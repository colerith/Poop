import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import discord

import main
from cogs.core import database
from cogs.core.constants import TZ, format_duration, HARDNESS_CHOICES, COLOR_CHOICES
from cogs.poop_tracker.cog import PoopTracker
from cogs.poop_tracker.reporting import build_weekly_details_embeds
from cogs.poop_tracker.session_state import PoopSessionState


class RuntimeTests(unittest.TestCase):
    def test_official_runtime_supported(self):
        main.check_discord_runtime()

    def test_fork_without_tree_rejected_before_initialization(self):
        with patch.object(main.commands, 'Bot', SimpleNamespace(load_extension=AsyncMock())):
            with self.assertRaisesRegex(RuntimeError, 'Discord 依赖不兼容'):
                main.PoopBot()

    def test_old_runtime_rejected(self):
        with patch.object(main.discord, 'version_info', (1, 7, 3)):
            with self.assertRaisesRegex(RuntimeError, 'Discord 依赖不兼容'):
                main.check_discord_runtime()


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.patch = patch.object(database, 'DB_PATH', Path(self.temp.name) / 'test.db')
        self.patch.start()
        database.init_db()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def add(self, end, start=None, user=1, guild=2):
        database.add_poop_log(user, guild, 'normal', False, 'brown', None, start, end)

    def test_local_month_boundary(self):
        self.add(datetime(2026, 10, 1, 0, 5, tzinfo=TZ))
        self.assertEqual(len(database.get_monthly_logs(1, 2, 2026, 10)), 1)
        self.assertEqual(len(database.get_monthly_logs(1, 2, 2026, 9)), 0)

    def test_local_week_boundaries(self):
        self.add(datetime(2026, 10, 5, 0, 5, tzinfo=TZ))
        self.add(datetime(2026, 10, 12, 0, 5, tzinfo=TZ))
        self.assertEqual(len(database.get_weekly_logs(1, 2, 2026, 10, 9)), 1)

    def test_checkins_count_and_guild_isolation(self):
        end = datetime(2026, 10, 9, 12, tzinfo=TZ)
        self.add(end)
        self.add(end, end - timedelta(seconds=90.4))
        self.add(end, guild=3)
        self.assertEqual(database.get_server_leaderboard(2), [(1, 2, 90)])

    def test_delete_latest_tied_timestamp(self):
        end = datetime(2026, 10, 9, 12, tzinfo=TZ)
        self.add(end)
        self.add(end)
        latest = database.get_last_poop_log(1, 2)
        self.assertEqual(latest['id'], 2)
        database.delete_poop_log(latest['id'])
        self.assertEqual(database.get_last_poop_log(1, 2)['id'], 1)


class ReportTests(unittest.TestCase):
    def test_long_report_preserves_all_notes_within_limits(self):
        logs = [dict(color='brown', hardness='normal', is_diarrhea=False,
                     end_time='2026-10-09 12:00:00+08:00', start_time=None,
                     duration_seconds=None, notes=f'NOTE-{i}-' + '💩' * 1200)
                for i in range(30)]
        pages = build_weekly_details_embeds('测试用户', logs, False)
        text = ''.join(field.value for page in pages for field in page.fields if '详细记录' in field.name)
        for i in range(30):
            self.assertIn(f'NOTE-{i}-' + '💩' * 1200, text)
        self.assertIn('周五', text)
        for page in pages:
            self.assertLessEqual(len(page.fields), 25)
            units = lambda value: len(value.encode('utf-16-le')) // 2
            total = units(page.title or '') + units(page.description or '') + units(page.footer.text or '')
            for field in page.fields:
                self.assertLessEqual(units(field.value), 1024)
                total += units(field.name) + units(field.value)
            self.assertLessEqual(total, 6000)

    def test_float_duration(self):
        self.assertEqual(format_duration(3661.9), '1小时 1分钟')


class SyncTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.patch = patch.object(database, 'DB_PATH', Path(self.temp.name) / 'test.db')
        self.patch.start()
        self.bot = main.PoopBot()
        await self.bot.__aenter__()
        self.bot.tree.sync = AsyncMock(return_value=[])

    async def asyncTearDown(self):
        await self.bot.close()
        self.patch.stop()
        self.temp.cleanup()

    async def test_exact_original_commands_loaded_and_global_cleared(self):
        payloads = []
        async def capture_sync(*, guild=None):
            payloads.append((guild, list(self.bot.tree.get_commands(guild=guild))))
            return []
        self.bot.tree.sync.side_effect = capture_sync
        await self.bot.setup_hook()
        self.assertEqual(payloads, [(None, [])])
        self.assertEqual({c.name for c in self.bot.tree.get_commands()},
                         {'拉屎打卡', '开始拉屎', '结束拉屎', '取消打卡', '本周详细日志', '本月热力图', '排行榜'})
        self.assertTrue(all(c.guild_only for c in self.bot.tree.get_commands()))
        self.bot.tree.sync.assert_awaited_once_with(guild=None)

    async def test_load_failure_does_not_sync_empty_tree(self):
        with patch.object(self.bot, 'load_extension', AsyncMock(side_effect=RuntimeError('load failed'))):
            with self.assertRaises(RuntimeError):
                await self.bot.setup_hook()
        self.bot.tree.sync.assert_not_awaited()

    async def test_all_guilds_and_new_guild_sync(self):
        await self.bot.setup_hook()
        self.bot.tree.sync.reset_mock()
        guilds = [SimpleNamespace(id=123), SimpleNamespace(id=456)]
        with patch.object(main.PoopBot, 'guilds', new=property(lambda _: guilds)):
            await self.bot.on_ready()
            await self.bot.on_ready()
        self.assertEqual(self.bot.tree.sync.await_count, 2)
        await self.bot.on_guild_join(SimpleNamespace(id=789))
        self.assertEqual(self.bot.tree.sync.await_count, 3)
        self.assertEqual(len(self.bot.tree.get_commands(guild=discord.Object(id=789))), 7)

    async def test_clear_global_restores_local_definitions_even_on_error(self):
        await self.bot.setup_hook()
        saved = self.bot.tree.get_commands()
        ctx = SimpleNamespace(guild=None, send=AsyncMock())
        with patch.object(main, 'bot', self.bot):
            await main.sync.callback(ctx, 'clear_global')
            self.assertEqual(self.bot.tree.get_commands(), saved)
            await main.sync.callback(ctx, 'sync', '123')
            self.assertEqual(len(self.bot.tree.get_commands(guild=discord.Object(id=123))), 7)
            self.bot.tree.sync.side_effect = discord.HTTPException(SimpleNamespace(status=500, reason='test'), 'test')
            with self.assertLogs('main', level='ERROR'):
                await main.sync.callback(ctx, 'clear_global')
            self.assertEqual(self.bot.tree.get_commands(), saved)

    async def test_global_registration_action_rejected(self):
        ctx = SimpleNamespace(guild=None, send=AsyncMock())
        with patch.object(main, 'bot', self.bot):
            await main.sync.callback(ctx, 'global')
        self.bot.tree.sync.assert_not_awaited()

    async def test_cleanup_failure_restores_template_and_retries(self):
        failure = discord.HTTPException(SimpleNamespace(status=500, reason='test'), 'test')
        self.bot.tree.sync.side_effect = [failure, [], []]
        with self.assertLogs('main', level='ERROR'):
            await self.bot.setup_hook()
        self.assertFalse(self.bot._global_cleared)
        self.assertEqual(len(self.bot.tree.get_commands()), 7)
        guilds = [SimpleNamespace(id=123)]
        with patch.object(main.PoopBot, 'guilds', new=property(lambda _: guilds)):
            await self.bot.on_ready()
        self.assertTrue(self.bot._global_cleared)
        self.assertEqual(len(self.bot.tree.get_commands(guild=discord.Object(id=123))), 7)

    async def test_failed_guild_does_not_prevent_other_guilds(self):
        self.bot._global_cleared = True
        failure = discord.Forbidden(SimpleNamespace(status=403, reason='test'), 'test')
        self.bot.tree.sync.side_effect = [failure, []]
        guilds = [SimpleNamespace(id=123), SimpleNamespace(id=456)]
        with patch.object(main.PoopBot, 'guilds', new=property(lambda _: guilds)):
            with self.assertLogs('main', level='ERROR'):
                await self.bot.on_ready()
        self.assertEqual(self.bot._synced_guilds, {456})


class SessionTests(unittest.IsolatedAsyncioTestCase):
    def make_tracker(self):
        tracker = object.__new__(PoopTracker)
        tracker.session_state = PoopSessionState()
        tracker.bot = SimpleNamespace(fetch_user=AsyncMock())
        tracker.session_state.start_session(1, datetime.now(TZ) - timedelta(minutes=2), 2)
        return tracker

    def interaction(self, guild_id):
        return SimpleNamespace(user=SimpleNamespace(id=1, mention='<@1>'), guild=SimpleNamespace(id=guild_id),
                               response=SimpleNamespace(send_message=AsyncMock()))

    async def test_cross_guild_end_keeps_session(self):
        tracker = self.make_tracker()
        with patch.object(database, 'add_poop_log') as add:
            await PoopTracker.end_poop.callback(tracker, self.interaction(3), HARDNESS_CHOICES[2], False, COLOR_CHOICES[0])
            add.assert_not_called()
        self.assertTrue(tracker.session_state.has_session(1))

    async def test_save_failure_keeps_session(self):
        tracker = self.make_tracker()
        with patch.object(database, 'add_poop_log', side_effect=sqlite3.OperationalError('busy')):
            with self.assertRaises(sqlite3.OperationalError):
                await PoopTracker.end_poop.callback(tracker, self.interaction(2), HARDNESS_CHOICES[2], False, COLOR_CHOICES[0])
        self.assertTrue(tracker.session_state.has_session(1))

    async def test_successful_end_clears_session(self):
        tracker = self.make_tracker()
        with patch.object(database, 'add_poop_log') as add:
            await PoopTracker.end_poop.callback(tracker, self.interaction(2), HARDNESS_CHOICES[2], False, COLOR_CHOICES[0])
            add.assert_called_once()
        self.assertFalse(tracker.session_state.has_session(1))

    async def test_timeout_save_failure_keeps_session(self):
        tracker = self.make_tracker()
        tracker.session_state.start_session(1, datetime.now(TZ) - timedelta(hours=2), 2)
        with patch.object(database, 'add_poop_log', side_effect=sqlite3.OperationalError('busy')):
            with self.assertRaises(sqlite3.OperationalError):
                await PoopTracker.check_poop_sessions.coro(tracker)
        self.assertTrue(tracker.session_state.has_session(1))

    async def test_private_message_rejected(self):
        interaction = self.interaction(2)
        interaction.guild = None
        self.assertFalse(await self.make_tracker().interaction_check(interaction))
        interaction.response.send_message.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()

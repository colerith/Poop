import random
import logging
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ..core import database, views
from ..core.constants import (
    COLOR_CHOICES,
    HARDNESS_CHOICES,
    HEALTH_TIPS,
    TZ,
    format_duration,
)
from .reporting import build_monthly_heatmap_embed, build_weekly_details_embeds
from .session_state import PoopSessionState


class PoopTracker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session_state = PoopSessionState()

        database.init_db()
        self.check_poop_sessions.add_exception_type(database.sqlite3.OperationalError)
        self.check_poop_sessions.start()
        logging.getLogger(__name__).info("拉屎追踪器已准备就绪。")

    def cog_unload(self):
        self.check_poop_sessions.cancel()

    @tasks.loop(minutes=1)
    async def check_poop_sessions(self):
        current_time = datetime.now(TZ)
        to_remove = []

        for user_id, (start_time, guild_id) in self.session_state.iter_sessions():
            duration = current_time - start_time
            duration_minutes = duration.total_seconds() / 60

            reminder_count = self.session_state.get_reminder_count(user_id)
            if duration_minutes >= (reminder_count + 1) * 10 and duration_minutes < 60:
                try:
                    user = await self.bot.fetch_user(user_id)
                    await user.send(
                        f"⏰ 你已经在马桶上 {int(duration_minutes)} 分钟了！拉完了吗？记得使用 `/结束拉屎` 结束打卡哦！"
                    )
                    self.session_state.set_reminder_count(user_id, reminder_count + 1)
                except Exception:
                    pass

            if duration_minutes >= 60:
                to_remove.append((user_id, start_time, guild_id))

        for user_id, start_time, guild_id in to_remove:
            if self.session_state.get_session(user_id) != (start_time, guild_id):
                continue

            end_time = start_time + timedelta(hours=1)
            database.add_poop_log(
                user_id=user_id,
                guild_id=guild_id,
                hardness="未记录",
                is_diarrhea=False,
                color="未记录",
                notes="自动结束（超过1小时）",
                start_time=start_time,
                end_time=end_time,
            )

            self.session_state.pop_session(user_id)
            try:
                user = await self.bot.fetch_user(user_id)
                await user.send("⏱️ 你的拉屎会话已超过1小时，已自动结束并记录为1小时。请记得下次及时使用 `/结束拉屎` 打卡哦！")
            except Exception:
                pass

    @check_poop_sessions.before_loop
    async def before_check_poop_sessions(self):
        await self.bot.wait_until_ready()

    async def interaction_check(self, interaction):
        if interaction.guild is None:
            await interaction.response.send_message("请在服务器内使用此命令。", ephemeral=True)
            return False
        return True

    async def cog_app_command_error(self, interaction, error):
        logging.getLogger(__name__).error("打卡命令执行失败", exc_info=(type(error), error, error.__traceback__))
        message = "❌ 操作失败，请稍后重试；如果问题持续，请联系管理员查看日志。"
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="拉屎打卡", description="“事后”快速记录一次伟大的解放！")
    @app_commands.choices(hardness=HARDNESS_CHOICES, color=COLOR_CHOICES)
    @app_commands.describe(hardness="软硬程度如何？", is_diarrhea="是正常发挥还是喷射战士？", color="它的颜色是？", notes="有什么想补充的吗？")
    async def poop_check_in(
        self,
        interaction: discord.Interaction,
        hardness: app_commands.Choice[str],
        is_diarrhea: bool,
        color: app_commands.Choice[str],
        notes: str = None,
    ):
        database.add_poop_log(
            user_id=interaction.user.id,
            guild_id=interaction.guild.id,
            hardness=hardness.value,
            is_diarrhea=is_diarrhea,
            color=color.value,
            notes=notes,
            start_time=None,
            end_time=datetime.now(TZ),
        )
        tip = random.choice(HEALTH_TIPS)
        await interaction.response.send_message(
            f"💩 {interaction.user.mention} 又完成了一件人生大事，记录完毕！\n\n**小助手温馨提示💡**\n> {tip}"
        )

    @app_commands.guild_only()
    @app_commands.command(name="开始拉屎", description="开启一次史诗级旅程的计时器！")
    async def start_poop(self, interaction: discord.Interaction):
        if self.session_state.has_session(interaction.user.id):
            await interaction.response.send_message("别急，你已经在马桶上了！结束后请使用 `/结束拉屎`。", ephemeral=True)
            return

        self.session_state.start_session(interaction.user.id, datetime.now(TZ), interaction.guild.id)
        tip = random.choice(HEALTH_TIPS)
        await interaction.response.send_message(
            f"🏃 {interaction.user.mention} 已坐上王座，祝你...一路顺畅，如黄河入海！🌊\n\n**小助手冷知识放送🔬**\n> {tip}"
        )

    @app_commands.guild_only()
    @app_commands.command(name="结束拉屎", description="解放完毕！停止计时并汇报战果。")
    @app_commands.choices(hardness=HARDNESS_CHOICES, color=COLOR_CHOICES)
    @app_commands.describe(hardness="软硬程度如何？", is_diarrhea="是正常发挥还是喷射战士？", color="它的颜色是？", notes="有什么想补充的吗？")
    async def end_poop(
        self,
        interaction: discord.Interaction,
        hardness: app_commands.Choice[str],
        is_diarrhea: bool,
        color: app_commands.Choice[str],
        notes: str = None,
    ):
        session = self.session_state.get_session(interaction.user.id)
        if session is None:
            await interaction.response.send_message("🤔 你还没开始呢，怎么就结束了？先用 `/开始拉屎` 吧！", ephemeral=True)
            return

        start_time, guild_id = session
        if guild_id != interaction.guild.id:
            await interaction.response.send_message("请回到开始计时的服务器使用 `/结束拉屎`。", ephemeral=True)
            return
        end_time = datetime.now(TZ)
        duration = end_time - start_time
        seconds = int(duration.total_seconds())
        h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
        duration_str = f"{h}小时 {m}分 {s}秒" if h > 0 else f"{m}分 {s}秒"

        database.add_poop_log(
            user_id=interaction.user.id,
            guild_id=interaction.guild.id,
            hardness=hardness.value,
            is_diarrhea=is_diarrhea,
            color=color.value,
            notes=notes,
            start_time=start_time,
            end_time=end_time,
        )
        self.session_state.pop_session(interaction.user.id)
        await interaction.response.send_message(
            f"🎉 {interaction.user.mention} 解放完毕！本次史诗级旅程用时: **{duration_str}**。\n战果已载入史册：**{hardness.name}**, **{'是喷射战士' if is_diarrhea else '状态正常'}**！"
        )

    @app_commands.guild_only()
    @app_commands.command(name="取消打卡", description="手滑了？删除你最近的一条拉屎记录。")
    async def cancel_check_in(self, interaction: discord.Interaction):
        last_log = database.get_last_poop_log(interaction.user.id, interaction.guild.id)
        if not last_log:
            await interaction.response.send_message("你的历史清清白白，没有记录可以取消。", ephemeral=True)
            return

        end_time_obj = datetime.fromisoformat(last_log["end_time"])
        time_str = discord.utils.format_dt(end_time_obj, style="R")
        embed = discord.Embed(
            title="🗑️ 等一下！",
            description=f"你确定要删除这条 **{time_str}** 的记录吗？此操作无法撤销！",
            color=discord.Color.orange(),
        )
        view = views.ConfirmCancelView(log_id=last_log["id"])
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="本周详细日志", description="查看本周的详细拉屎记录和统计")
    @app_commands.describe(only_notes="只查看有备注的日志吗？")
    async def weekly_details(self, interaction: discord.Interaction, only_notes: bool = False):
        await interaction.response.defer(ephemeral=True)
        now = datetime.now(TZ)
        logs = database.get_weekly_logs(interaction.user.id, interaction.guild.id, now.year, now.month, now.day)

        if not logs:
            await interaction.followup.send("你这周风平浪静，还没有任何记录哦。")
            return

        filtered_logs = [log for log in logs if not only_notes or (only_notes and log["notes"])]
        if not filtered_logs:
            msg = "本周没有找到任何带备注的记录哦。" if only_notes else "本周没有任何记录哦。"
            await interaction.followup.send(msg)
            return

        embeds = build_weekly_details_embeds(interaction.user.display_name, filtered_logs, only_notes)
        for embed in embeds:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="本月热力图", description="以日历形式查看本月的拉屎颜色和硬度分布")
    async def monthly_heatmap(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        now = datetime.now(TZ)
        year, month = now.year, now.month
        logs = database.get_monthly_logs(interaction.user.id, interaction.guild.id, year, month)

        if not logs:
            await interaction.followup.send("本月一片空白，快去创造历史吧！", ephemeral=True)
            return

        embed = build_monthly_heatmap_embed(interaction.user.display_name, year, month, logs)
        await interaction.followup.send(embed=embed)

    @app_commands.guild_only()
    @app_commands.command(name="排行榜", description="围观本服的“厕所之王”！")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        server_leaderboard = database.get_server_leaderboard(interaction.guild.id)

        embed = discord.Embed(title=f"🏆🚽 {interaction.guild.name} 拉屎风云榜 🚽🏆", color=0xD4AF37)

        description = ""
        rank_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}

        for i, row in enumerate(server_leaderboard[:10]):
            rank = i + 1
            user_id, times, total_duration_sec = row[0], row[1], row[2] or 0
            try:
                user = interaction.guild.get_member(user_id) or await self.bot.fetch_user(user_id)
                user_mention = user.mention
            except discord.NotFound:
                user_mention = f"已离开的勇士(ID:{user_id})"

            duration_str = format_duration(total_duration_sec)
            emoji = rank_emojis.get(rank, f"**{rank}.**")
            description += f"{emoji} {user_mention} - **{times}** 次 (共计: **{duration_str}**)\n"

        if not description:
            description = "王座虚位以待，本服还没有打卡记录！"

        embed.description = description
        embed.set_footer(text="排名依据：次数优先，其次是总时长")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(PoopTracker(bot))

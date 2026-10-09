"""机器人入口：全局注册，并向每个已加入的服务器同步命令。"""
import asyncio
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

log = logging.getLogger(__name__)
load_dotenv(Path(__file__).with_name(".env"))


class PoopBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        # 斜杠命令不依赖特权 Intent；仅在需要 !sync 时启用。
        intents.message_content = os.getenv("ENABLE_MESSAGE_CONTENT", "false").lower() == "true"
        super().__init__(command_prefix="!", intents=intents,
                         allowed_mentions=discord.AllowedMentions.none())
        self._synced_guilds = set()
        self._sync_lock = asyncio.Lock()
        self._global_synced = False

    async def setup_hook(self):
        # 加载失败必须终止启动，避免把空命令树同步到 Discord。
        await self.load_extension("cogs.poop_tracker")
        await self.sync_global()

    async def sync_global(self):
        try:
            synced = await self.tree.sync()
        except discord.HTTPException:
            log.exception("全局命令同步失败；连接就绪后将重试")
            return
        self._global_synced = True
        log.info("已同步 %s 条全局命令", len(synced))

    async def sync_guild(self, guild):
        async with self._sync_lock:
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            self._synced_guilds.add(guild.id)
            log.info("服务器 %s 已同步 %s 条命令：%s", guild.id, len(synced),
                     [command.name for command in synced])
            return synced

    async def try_sync_guild(self, guild):
        try:
            await self.sync_guild(guild)
        except discord.Forbidden:
            log.error("服务器 %s 同步被拒绝，请检查机器人安装及 applications.commands 授权", guild.id)
        except discord.HTTPException:
            log.exception("服务器 %s 同步失败；可重新连接或使用 !sync 重试", guild.id)

    async def on_ready(self):
        if not self._global_synced:
            await self.sync_global()
        for guild in self.guilds:
            if guild.id not in self._synced_guilds:
                await self.try_sync_guild(guild)
        log.info("机器人 %s 已就绪，已加入 %s 个服务器", self.user, len(self.guilds))

    async def on_guild_join(self, guild):
        await self.try_sync_guild(guild)

    async def on_guild_remove(self, guild):
        self._synced_guilds.discard(guild.id)


bot = PoopBot()


@bot.command(name="sync")
@commands.is_owner()
async def sync(ctx: commands.Context, action: str = "sync", guild_id_str: str = None):
    """所有者维护命令：!sync [sync|clear|global|clear_global] [服务器ID]。"""
    if action not in {"sync", "clear", "global", "clear_global"}:
        await ctx.send("用法：`!sync [sync|clear|global|clear_global] [服务器ID]`")
        return
    guild_id = ctx.guild.id if ctx.guild else None
    if guild_id_str:
        try:
            guild_id = int(guild_id_str)
            if guild_id <= 0:
                raise ValueError
        except ValueError:
            await ctx.send("❌ 服务器 ID 必须是正整数。")
            return
    if action in {"sync", "clear"} and guild_id is None:
        await ctx.send("❌ 请提供服务器 ID，或在服务器内使用此命令。")
        return
    try:
        if action == "sync":
            synced = await bot.sync_guild(discord.Object(id=guild_id))
        elif action == "global":
            synced = await bot.tree.sync()
            bot._global_synced = True
        else:
            guild = discord.Object(id=guild_id) if action == "clear" else None
            # 清除远端命令后恢复本地定义，确保后续 !sync 能正常重新注册。
            async with bot._sync_lock:
                saved = bot.tree.get_commands(guild=guild)
                try:
                    bot.tree.clear_commands(guild=guild)
                    synced = await bot.tree.sync(guild=guild)
                finally:
                    for command in saved:
                        bot.tree.add_command(command, guild=guild, override=True)
        await ctx.send(f"✅ 操作完成：{action}，远端现有 {len(synced)} 条命令。")
    except discord.HTTPException:
        log.exception("手动命令同步失败")
        await ctx.send("❌ 同步失败，请检查机器人授权和网络，详细原因见运行日志。")


@sync.error
async def sync_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.send("❌ 此命令仅限机器人所有者使用。")
    else:
        log.error("维护命令失败", exc_info=(type(error), error, error.__traceback__))
        await ctx.send("❌ 操作失败，请查看运行日志。")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("❌ 请在项目根目录的 .env 文件中配置 DISCORD_TOKEN。")
    logging.basicConfig(level=logging.INFO)
    bot.run(token)

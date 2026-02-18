# main.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# --- 配置 ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print("❌ 错误：在 .env 文件中找不到 DISCORD_TOKEN。")
    exit()

TEST_GUILDS = [1384945301780955246, 1397629012292931726]


# --- Bot 子类 ---
class PoopBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """这是 Bot 启动时异步执行的核心钩子"""

        print("="*30)
        print("🚀 正在初始化 Bot...")

        # 1. 加载 Cogs
        print("\n--- [阶段 1/2] 正在加载功能插件 (Cogs) ---")
        cogs_loaded = 0
        for filename in os.listdir('./cogs'):
            # 我们只加载 poop_tracker.py，core 目录是辅助模块，不作为 cog 加载
            if filename == 'poop_tracker.py':
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"  ✅ 成功加载 Cog: {filename}")
                    cogs_loaded += 1
                except Exception as e:
                    print(f"  ❌ 加载 Cog {filename} 失败: {e}")
        print(f"--- Cogs 加载完毕 ({cogs_loaded} 个) ---\n")

        # 2. 同步斜杠命令到测试服务器
        print("--- [阶段 2/2] 正在同步斜杠命令 ---")
        if not TEST_GUILDS:
            print("  ⚠️ 警告: 未设置测试服务器ID (TEST_GUILDS)，将进行全局同步。")
            print("  全局同步可能需要长达一小时才能生效。")
            synced = await self.tree.sync()
            print(f"  🌍 已同步 {len(synced)} 条全局命令。")
        else:
            for guild_id in TEST_GUILDS:
                guild = discord.Object(id=guild_id)
                try:
                    self.tree.copy_global_to(guild=guild)
                    synced = await self.tree.sync(guild=guild)
                    print(f"  ✅ 已将 {len(synced)} 条命令同步到服务器: {guild_id}")
                    # 打印出同步的命令列表，方便调试
                    if synced:
                         print(f"     - 命令列表: {[cmd.name for cmd in synced]}")
                except discord.errors.Forbidden:
                    print(f"  ❌ 权限错误: 无法将命令同步到服务器 {guild_id}。")
                    print("     请确保 Bot 已被正确邀请，拥有 'applications.commands' 权限。")
                except Exception as e:
                    print(f"  ❌ 同步到服务器 {guild_id} 时发生未知错误: {e}")

        print("--- 命令同步完毕 ---\n")


    async def on_ready(self):
        print("="*30)
        print(f'✅ Bot 已准备就绪！')
        print(f'   - 用户名: {self.user} ({self.user.id})')
        print(f'   - 邀请的服务器数量: {len(self.guilds)}')
        print(f'🚀 准备好记录大家的每一次“解放”！')
        print("="*30)

bot = PoopBot()

# --- 手动同步指令 !sync ---
@bot.command(name="sync")
@commands.is_owner() # 只有机器人所有者能使用
async def sync(ctx: commands.Context, guild_id: int = None):
    """
    手动将斜杠命令同步到指定服务器或当前服务器。
    用法:
    !sync -> 同步到当前服务器
    !sync [服务器ID] -> 同步到指定ID服务器
    """
    target_guild_id = guild_id or ctx.guild.id
    if not target_guild_id:
        await ctx.send("❌ 请在服务器内使用此命令，或提供一个服务器ID。")
        return

    msg = await ctx.send(f"🚑 正在向服务器 `{target_guild_id}` 紧急同步命令...")

    guild = discord.Object(id=target_guild_id)
    try:
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        await msg.edit(content=f"✅ **同步成功！**\n已向服务器 `{target_guild_id}` 注册了 **{len(synced)}** 个命令。\n\n**请注意：**\n> 成员可能需要 **重启 Discord 客户端 (Ctrl+R)** 才能看到最新的命令。")
        print(f"[手动同步] 成功将 {len(synced)} 个命令同步到服务器 {target_guild_id}。")
    except Exception as e:
        await msg.edit(content=f"❌ **同步失败！**\n错误信息: ```{e}```")
        import traceback
        traceback.print_exc()

# --- 运行 Bot ---
if __name__ == "__main__":
    bot.run(TOKEN)
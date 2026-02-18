# main.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Bot 子类
class PoopBot(commands.Bot):
    def __init__(self):
        # 设置 intents
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """这是 Bot 启动时异步执行的钩子"""
        print("--- 开始加载 Cogs ---")

        # 加载 cogs 文件夹下的所有 .py 文件
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"✅ 成功加载 Cog: {filename}")
                except Exception as e:
                    print(f"❌ 加载 Cog {filename} 失败: {e}")

        print("--- Cogs 加载完毕 ---")

        # 同步斜杠命令
        synced = await self.tree.sync()
        print(f"🌍 已同步 {len(synced)} 条全局命令。")


    async def on_ready(self):
        print('---')
        print(f'🤖 以 {self.user} ({self.user.id}) 登入')
        print(f'本小助手已就位，准备好记录大家的每一次“解放”！🚀')
        print('---')

# 实例化并运行 Bot
bot = PoopBot()
bot.run(TOKEN)
# cogs/poop_tracker.py
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import random

from .core import database, views
from .core.constants import (
    TZ, HARDNESS_CHOICES, COLOR_CHOICES,
    COLOR_MAP, HEALTH_TIPS,COLOR_EMOJI_MAP,HARDNESS_EMOJI_MAP, format_duration
)

class PoopTracker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.poop_starters = {}
        self.poop_reminder_count = {}

        # 初始化数据库并启动后台任务
        database.init_db()
        self.check_poop_sessions.start()
        print("🚽 拉屎追踪器已准备就绪。")

    def cog_unload(self):
        # 在 Cog 被卸载时停止后台任务
        self.check_poop_sessions.cancel()

    # 后台任务
    @tasks.loop(minutes=1)
    async def check_poop_sessions(self):
        current_time = datetime.now(TZ)
        to_remove = []

        for user_id, (start_time, guild_id) in list(self.poop_starters.items()):
            duration = current_time - start_time
            duration_minutes = duration.total_seconds() / 60

            reminder_count = self.poop_reminder_count.get(user_id, 0)
            if duration_minutes >= (reminder_count + 1) * 10 and duration_minutes < 60:
                try:
                    user = await self.bot.fetch_user(user_id)
                    await user.send(f"⏰ 你已经在马桶上 {int(duration_minutes)} 分钟了！拉完了吗？记得使用 `/结束拉屎` 结束打卡哦！")
                    self.poop_reminder_count[user_id] = reminder_count + 1
                except: pass

            if duration_minutes >= 60:
                to_remove.append((user_id, start_time, guild_id))

        for user_id, start_time, guild_id in to_remove:
            popped_session = self.poop_starters.pop(user_id, None)
            if popped_session is None or popped_session != (start_time, guild_id):
                if popped_session is not None: self.poop_starters[user_id] = popped_session
                continue

            self.poop_reminder_count.pop(user_id, None)
            end_time = start_time + timedelta(hours=1)

            database.add_poop_log(
                user_id=user_id, guild_id=guild_id, hardness='normal', is_diarrhea=False,
                color='未记录', notes='自动结束（超过1小时）', start_time=start_time, end_time=end_time
            )

            try:
                user = await self.bot.fetch_user(user_id)
                await user.send(f"⏱️ 你的拉屎会话已超过1小时，已自动结束并记录为1小时。请记得下次及时使用 `/结束拉屎` 打卡哦！")
            except: pass

    # --- 斜杠命令 ---

    @app_commands.command(name="拉屎打卡", description="“事后”快速记录一次伟大的解放！")
    @app_commands.choices(hardness=HARDNESS_CHOICES, color=COLOR_CHOICES)
    @app_commands.describe(hardness="手感如何？", is_diarrhea="是正常发挥还是喷射战士？", color="它的颜色是？", notes="有什么想补充的吗？")
    async def poop_check_in(self, interaction: discord.Interaction, hardness: app_commands.Choice[str], is_diarrhea: bool, color: app_commands.Choice[str], notes: str = None):
        database.add_poop_log(
            user_id=interaction.user.id, guild_id=interaction.guild.id, hardness=hardness.value,
            is_diarrhea=is_diarrhea, color=color.value, notes=notes, start_time=None,
            end_time=datetime.now(TZ)
        )
        tip = random.choice(HEALTH_TIPS)
        await interaction.response.send_message(f"💩 {interaction.user.mention} 又完成了一件人生大事，记录完毕！\n\n**小助手温馨提示💡**\n> {tip}")

    @app_commands.command(name="开始拉屎", description="开启一次史诗级旅程的计时器！")
    async def start_poop(self, interaction: discord.Interaction):
        if interaction.user.id in self.poop_starters:
            await interaction.response.send_message("别急，你已经在马桶上了！结束后请使用 `/结束拉屎`。", ephemeral=True)
            return
        self.poop_starters[interaction.user.id] = (datetime.now(TZ), interaction.guild.id)
        self.poop_reminder_count[interaction.user.id] = 0
        tip = random.choice(HEALTH_TIPS)
        await interaction.response.send_message(f"🏃 {interaction.user.mention} 已坐上王座，祝你...一路顺暢，如黄河入海！🌊\n\n**小助手冷知识放送🔬**\n> {tip}")

    @app_commands.command(name="结束拉屎", description="解放完毕！停止计时并汇报战果。")
    @app_commands.choices(hardness=HARDNESS_CHOICES, color=COLOR_CHOICES)
    @app_commands.describe(hardness="手感如何？", is_diarrhea="是正常发挥还是喷射战士？", color="它的颜色是？", notes="有什么想补充的吗？")
    async def end_poop(self, interaction: discord.Interaction, hardness: app_commands.Choice[str], is_diarrhea: bool, color: app_commands.Choice[str], notes: str = None):
        if interaction.user.id in self.poop_starters:
            start_time, _ = self.poop_starters.pop(interaction.user.id)
            self.poop_reminder_count.pop(interaction.user.id, None)
            end_time = datetime.now(TZ)
            duration = end_time - start_time
            seconds = int(duration.total_seconds())
            h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
            duration_str = f"{h}小时 {m}分 {s}秒" if h > 0 else f"{m}分 {s}秒"

            database.add_poop_log(
                user_id=interaction.user.id, guild_id=interaction.guild.id, hardness=hardness.value,
                is_diarrhea=is_diarrhea, color=color.value, notes=notes, start_time=start_time, end_time=end_time
            )
            await interaction.response.send_message(f"🎉 {interaction.user.mention} 解放完毕！本次史诗级旅程用时: **{duration_str}**。\n战果已载入史册：**{hardness.name}**, **{'是喷射战士' if is_diarrhea else '状态正常'}**！")
        else:
            await interaction.response.send_message("🤔 你还没开始呢，怎么就结束了？先用 `/开始拉屎` 吧！", ephemeral=True)

    @app_commands.command(name="取消打卡", description="手滑了？删除你最近的一条拉屎记录。")
    async def cancel_check_in(self, interaction: discord.Interaction):
        last_log = database.get_last_poop_log(interaction.user.id, interaction.guild.id)
        if not last_log:
            await interaction.response.send_message("你的历史清清白白，没有记录可以取消。", ephemeral=True)
            return

        end_time_obj = datetime.fromisoformat(last_log['end_time'])
        time_str = discord.utils.format_dt(end_time_obj, style='R')
        embed = discord.Embed(title="🗑️ 等一下！", description=f"你确定要删除这条 **{time_str}** 的记录吗？此操作无法撤销！", color=discord.Color.orange())
        view = views.ConfirmCancelView(log_id=last_log['id'])
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="本周详细日志", description="查看本周的详细拉屎记录和统计")
    @app_commands.describe(only_notes="只查看有备注的日志吗？")
    async def weekly_details(self, interaction: discord.Interaction, only_notes: bool = False):
        await interaction.response.defer(ephemeral=True)
        now = datetime.now(TZ)
        logs = database.get_weekly_logs(interaction.user.id, interaction.guild.id, now.year, now.month, now.day)

        if not logs:
            await interaction.followup.send("你这周风平浪静，还没有任何记录哦。")
            return

        filtered_logs = [log for log in logs if not only_notes or (only_notes and log['notes'])]

        if not filtered_logs:
            msg = "本周没有找到任何带备注的记录哦。" if only_notes else "本周没有任何记录哦。"
            await interaction.followup.send(msg)
            return

        # 统计数据
        color_stats = {}
        diarrhea_count = 0

        for log in filtered_logs:
            color = COLOR_MAP.get(log['color'], log['color'] or '未记录')
            color_stats[color] = color_stats.get(color, 0) + 1
            if log['is_diarrhea']:
                diarrhea_count += 1

        embed = discord.Embed(
            title=f"📊 {interaction.user.display_name} 的本周详细日志",
            description=f"共 {len(filtered_logs)} 条记录{'（仅显示有备注的记录）' if only_notes else ''}",
            color=0x7A5543
        )

        color_text = "\n".join([f"{color}: {count}次" for color, count in sorted(color_stats.items(), key=lambda x: x[1], reverse=True)])
        embed.add_field(name="🎨 颜色统计", value=color_text or "无数据", inline=False)
        embed.add_field(name="💧 拉肚子次数", value=f"{diarrhea_count}次", inline=True)
        embed.add_field(name="✅ 正常次数", value=f"{len(filtered_logs) - diarrhea_count}次", inline=True)

        details_text = ""
        for log in filtered_logs:
            end_time = datetime.fromisoformat(log['end_time'])
            start_time = datetime.fromisoformat(log['start_time']) if log['start_time'] else None
            duration_seconds = log['duration_seconds'] if log['duration_seconds'] is not None else (int((end_time - start_time).total_seconds()) if start_time else None)
            duration_str = format_duration(duration_seconds)
            color = COLOR_MAP.get(log['color'], log['color'] or '未记录')
            diarrhea = "💧拉肚子" if log['is_diarrhea'] else "✅正常"
            note = f" - **备注**：{log['notes']}" if log['notes'] else ""

            details_text += (
                f"**{end_time.strftime('%A %H:%M')}** "
                f"({duration_str}) - {color} {diarrhea}{note}\n"
            )

        embed.add_field(name="📋 详细记录", value=details_text or "无记录", inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="本月热力图", description="以日历形式查看本月的拉屎颜色和硬度分布")
    async def monthly_heatmap(self, interaction: discord.Interaction):
        await interaction.response.defer()

        now = datetime.now(TZ)
        year, month = now.year, now.month

        logs = database.get_monthly_logs(interaction.user.id, interaction.guild.id, year, month)

        if not logs:
            await interaction.followup.send("本月一片空白，快去创造历史吧！", ephemeral=True)
            return

        # 1. 数据预处理：将日志按天分组
        daily_data = {}
        for log in logs:
            day = datetime.fromisoformat(log['end_time']).day
            if day not in daily_data:
                daily_data[day] = {'colors': set(), 'hardnesses': set()}

            daily_data[day]['colors'].add(log['color'] or '未记录')
            daily_data[day]['hardnesses'].add(log['hardness'] or '未记录')

        # 2. 生成日历网格
        import calendar
        cal = calendar.monthcalendar(year, month)

        # --- 生成颜色热力图 ---
        color_heatmap = "`一  二  三  四  五  六  日`\n"
        for week in cal:
            for day in week:
                if day == 0:
                    color_heatmap += "    " # 使用4个空格作为占位符
                    continue

                emoji = "⬜" # 默认无记录
                if day in daily_data:
                    colors = daily_data[day]['colors']
                    if len(colors) > 1:
                        emoji = "🌈" # 当天有多种颜色记录
                    else:
                        color_key = list(colors)[0]
                        emoji = COLOR_EMOJI_MAP.get(color_key, "❔")

                color_heatmap += f"`{emoji}` "
            color_heatmap += "\n"

        # --- 生成硬度热力图 ---
        hardness_heatmap = "`一  二  三  四  五  六  日`\n"
        for week in cal:
            for day in week:
                if day == 0:
                    hardness_heatmap += "    " # 同样使用4个空格
                    continue

                emoji = "⬜" # 默认无记录
                if day in daily_data:
                    hardnesses = daily_data[day]['hardnesses']
                    if len(hardnesses) > 1:
                        emoji = "❓" # 当天有多种硬度记录
                    else:
                        hardness_key = list(hardnesses)[0]
                        emoji = HARDNESS_EMOJI_MAP.get(hardness_key, "❔")

                hardness_heatmap += f"`{emoji}` "
            hardness_heatmap += "\n"

        # 3. 创建并发送 Embed
        embed = discord.Embed(
            title=f"📅 {interaction.user.display_name} 的 {year}年{month}月拉屎热力图",
            color=0x7A5543
        )
        embed.add_field(name="🎨 颜色分布", value=color_heatmap, inline=False)
        embed.add_field(name="🧱 软硬度分布", value=hardness_heatmap, inline=False)
        embed.set_footer(text="图例: ⬜=无记录, 🌈=多种颜色, ❓=多种硬度")

        await interaction.followup.send(embed=embed)

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
            description = "王座虚位以待，本服还没有人开始记录时长！"

        embed.description = description
        embed.set_footer(text="排名依据：次数优先，其次是总时长")
        await interaction.followup.send(embed=embed)



async def setup(bot: commands.Bot):
    await bot.add_cog(PoopTracker(bot))
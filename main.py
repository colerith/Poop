# main.py

import discord
from discord import app_commands
from discord.ext import tasks
import os
import random
from dotenv import load_dotenv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import database

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

TZ = ZoneInfo("Asia/Shanghai")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

poop_starters = {}  # {user_id: (start_time, guild_id)}
poop_reminder_count = {}
HARDNESS_CHOICES = [
    app_commands.Choice(name="🪨 钻石级 (很硬)", value="very_hard"),
    app_commands.Choice(name="🧱 板砖级 (偏硬)", value="hard"),
    app_commands.Choice(name="🍌 香蕉级 (正常)", value="normal"),
    app_commands.Choice(name="🍦 雪糕级 (偏软)", value="soft"),
    app_commands.Choice(name="💧 瀑布级 (水状)", value="watery"),
]


# 颜色代码映射到显示名称
COLOR_MAP = {
    "brown": "🟤棕色",
    "yellow": "🟡黄色", 
    "black": "⚫黑色",
    "green": "🟢绿色",
    "other": "🔴其他"
}

COLOR_CHOICES = [
    app_commands.Choice(name="🟤 棕色", value="brown"),
    app_commands.Choice(name="🟡 黄色", value="yellow"),
    app_commands.Choice(name="⚫ 黑色", value="black"),
    app_commands.Choice(name="🟢 绿色", value="green"),
    app_commands.Choice(name="🔴 其他", value="other"),
]

# 健康小知识列表
HEALTH_TIPS = [
    "多喝水是保持肠道通畅的第一要义！今天你喝够8杯水了吗？",
    "富含纤维的食物，比如蔬菜、水果和全谷物，是肠道的好朋友哦！",
    "规律的体育锻炼不仅能强身健体，还能促进肠道蠕动，告别便秘！",
    "别憋着！有便意就去，这是身体在给你发信号呢！",
    "吃饭时细嚼慢咽，不仅对胃好，也有助于消化系统的健康。",
    "益生菌是肠道里的“超级英雄”，可以喝点酸奶来给它们加油！",
    "减少高脂肪、高糖分食物的摄入，你的肠道会感谢你的！",
    "保持好心情！压力和焦虑也可能影响你的肠道功能哦。",
    "养成每日定时排便的习惯，比如在早餐后，有助于训练你的生物钟。",
    "早上起床后喝一杯温开水，可以唤醒你的肠道，促进蠕动。",
    "坐马桶时，可以在脚下垫个小凳子，让身体微微前倾，这个姿势有助于更顺畅地排便。",
    "以肚脐为中心，顺时针方向轻轻按摩腹部，可以帮助刺激肠道蠕动。",
    "留意你便便的形状和颜色，它们是肠道健康状况的直接反映。",
    "戒烟限酒，吸烟和过量饮酒都会损害消化系统，影响正常的排便功能。",
    "保证每晚7-8小时的优质睡眠，睡眠不足会扰乱肠道菌群的平衡。",
    "上厕所时要专心，不要看手机或读书，避免时间过长导致痔疮等问题。",
    "避免长时间久坐不动，每小时起身活动几分钟，这会减缓肠道蠕动。",
    "适量摄入橄榄油、牛油果、坚果等食物中的健康脂肪，可以起到润滑肠道的作用。",
    "注意某些药物可能会导致便秘，如果你正在服药并有排便问题，记得咨询医生。",
    "如果长期存在排便困扰，建议定期进行肠道健康检查，做到早发现、早治疗。"
]

def format_duration(total_seconds):
    """将总秒数格式化为易读的“X小时Y分钟”或“Y分钟”"""
    if total_seconds is None:
        return "未记录"
    if total_seconds < 60:
        return "不到1分钟"

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}小时 {minutes}分钟"
    elif minutes > 0:
        return f"{minutes}分钟"
    else:
        return f"{seconds}秒"

@tasks.loop(minutes=1)
async def check_poop_sessions():
    current_time = datetime.now(TZ)
    to_remove = []
    
    for user_id, (start_time, guild_id) in list(poop_starters.items()):
        duration = current_time - start_time
        duration_minutes = duration.total_seconds() / 60
        
        reminder_count = poop_reminder_count.get(user_id, 0)
        if duration_minutes >= (reminder_count + 1) * 10 and duration_minutes < 60:
            try:
                user = await client.fetch_user(user_id)
                await user.send(f"⏰ 你已经在马桶上 {int(duration_minutes)} 分钟了！拉完了吗？记得使用 `/结束拉屎` 结束打卡哦！")
                poop_reminder_count[user_id] = reminder_count + 1
            except:
                pass
        
        if duration_minutes >= 60:
            to_remove.append((user_id, start_time, guild_id))
    
    for user_id, start_time, guild_id in to_remove:
        popped_session = poop_starters.pop(user_id, None)
        if popped_session is None or popped_session != (start_time, guild_id):
            if popped_session is not None:
                poop_starters[user_id] = popped_session
            continue
        
        poop_reminder_count.pop(user_id, None)
        end_time = start_time + timedelta(hours=1)
        
        database.add_poop_log(
            user_id=user_id, 
            guild_id=guild_id,
            hardness='normal', 
            is_diarrhea=False, 
            color='未记录', 
            notes='自动结束（超过1小时）', 
            start_time=start_time, 
            end_time=end_time
        )
        
        try:
            user = await client.fetch_user(user_id)
            await user.send(f"⏱️ 你的拉屎会话已超过1小时，已自动结束并记录为1小时。请记得下次及时使用 `/结束拉屎` 打卡哦！")
        except:
            pass

@client.event
async def on_ready():
    database.init_db()
    await tree.sync()
    check_poop_sessions.start()
    print(f'以 {client.user} 登入')
    print('本小助手已就位，准备好记录大家的每一次“解放”！🚀')


@tree.command(name="拉屎打卡", description="“事后”快速记录一次伟大的解放！")
@app_commands.describe(hardness="手感如何？", is_diarrhea="是正常发挥还是喷射战士？", color="它的颜色是？", notes="有什么想补充的吗？")
@app_commands.choices(hardness=HARDNESS_CHOICES, color=COLOR_CHOICES)
async def poop_check_in(interaction: discord.Interaction, hardness: app_commands.Choice[str], is_diarrhea: bool, color: app_commands.Choice[str], notes: str = None):
    database.add_poop_log(
        user_id=interaction.user.id, guild_id=interaction.guild.id, hardness=hardness.value,
        is_diarrhea=is_diarrhea, color=color.value, notes=notes, start_time=None, 
        end_time=datetime.now(TZ)
    )
    tip = random.choice(HEALTH_TIPS)
    await interaction.response.send_message(f"💩 {interaction.user.mention} 又完成了一件人生大事，记录完毕！\n\n**小助手温馨提示💡**\n> {tip}")

@tree.command(name="开始拉屎", description="开启一次史诗级旅程的计时器！")
async def start_poop(interaction: discord.Interaction):
    if interaction.user.id in poop_starters:
        await interaction.response.send_message("别急，你已经在马桶上了！结束后请使用 `/结束拉屎`。", ephemeral=True)
        return
    poop_starters[interaction.user.id] = (datetime.now(TZ), interaction.guild.id)
    poop_reminder_count[interaction.user.id] = 0
    tip = random.choice(HEALTH_TIPS)
    await interaction.response.send_message(f"🏃 {interaction.user.mention} 已坐上王座，祝你...一路顺畅，如黄河入海！🌊\n\n**小助手冷知识放送🔬**\n> {tip}")

@tree.command(name="结束拉屎", description="解放完毕！停止计时并汇报战果。")
@app_commands.describe(hardness="手感如何？", is_diarrhea="是正常发挥还是喷射战士？", color="它的颜色是？", notes="有什么想补充的吗？")
@app_commands.choices(hardness=HARDNESS_CHOICES, color=COLOR_CHOICES)
async def end_poop(interaction: discord.Interaction, hardness: app_commands.Choice[str], is_diarrhea: bool, color: app_commands.Choice[str], notes: str = None):
    if interaction.user.id in poop_starters:
        start_time, _ = poop_starters.pop(interaction.user.id)
        poop_reminder_count.pop(interaction.user.id, None)
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

class ConfirmCancelView(discord.ui.View):
    def __init__(self, log_id: int):
        super().__init__(timeout=30)
        self.log_id = log_id
    @discord.ui.button(label="确认删除", style=discord.ButtonStyle.danger, custom_id="confirm_delete")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        database.delete_poop_log(self.log_id)
        await interaction.response.edit_message(content="✅ **记录已删除，就当无事发生。**", view=None)
        self.stop()
    @discord.ui.button(label="手滑了", style=discord.ButtonStyle.secondary, custom_id="cancel_delete")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="操作已取消，记录被抢救了回来！", view=None)
        self.stop()

@tree.command(name="取消打卡", description="手滑了？删除你最近的一条拉屎记录。")
async def cancel_check_in(interaction: discord.Interaction):
    last_log = database.get_last_poop_log(interaction.user.id, interaction.guild.id)
    if not last_log:
        await interaction.response.send_message("你的历史清清白白，没有记录可以取消。", ephemeral=True)
        return
    
    end_time_obj = datetime.fromisoformat(last_log['end_time'])
    time_str = discord.utils.format_dt(end_time_obj, style='R')
    embed = discord.Embed(title="🗑️ 等一下！", description=f"你确定要删除这条 **{time_str}** 的记录吗？此操作无法撤销！", color=discord.Color.orange())
    view = ConfirmCancelView(log_id=last_log['id'])
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@tree.command(name="本月详细日志", description="查看本月详细拉屎日志和统计数据，可筛选备注")
@app_commands.describe(only_notes="只查看有备注的日志吗？")
async def monthly_details(interaction: discord.Interaction, only_notes: bool = False):
    await interaction.response.defer()
    now = datetime.now(TZ)
    logs = database.get_monthly_logs(interaction.user.id, interaction.guild.id, now.year, now.month)
    
    if not logs:
        await interaction.followup.send("你这个月风平浪静，还没有任何记录哦。", ephemeral=True)
        return

    filtered_logs = [log for log in logs if not only_notes or (only_notes and log['notes'])]
    
    if not filtered_logs and only_notes:
        await interaction.followup.send("本月没有找到任何带备注的记录哦。", ephemeral=True)
        return
    elif not filtered_logs: # 理论上不会发生，因为上面已经判断过 logs 是否为空
        await interaction.followup.send("本月没有任何记录哦。", ephemeral=True)
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
        title=f"📊 {interaction.user.display_name} 的 {now.year}年{now.month}月详细日志",
        description=f"共 {len(filtered_logs)} 条记录{'（仅显示有备注的记录）' if only_notes else ''}",
        color=0x7A5543
    )
    
    color_text = "\n".join([f"{color}: {count}次" for color, count in sorted(color_stats.items(), key=lambda x: x[1], reverse=True)])
    embed.add_field(name="🎨 颜色统计", value=color_text or "无数据", inline=False)
    
    embed.add_field(name="💧 拉肚子次数", value=f"{diarrhea_count}次", inline=True)
    embed.add_field(name="✅ 正常次数", value=f"{len(filtered_logs) - diarrhea_count}次", inline=True)
    
    # 添加详细记录列表
    details_text = ""
    for i, log in enumerate(filtered_logs):
        end_time = datetime.fromisoformat(log['end_time'])
        start_time = datetime.fromisoformat(log['start_time']) if log['start_time'] else None
        
        duration_seconds = log['duration_seconds'] if log['duration_seconds'] is not None else \
                           int((end_time - start_time).total_seconds()) if start_time else None
        
        duration_str = format_duration(duration_seconds)

        color = COLOR_MAP.get(log['color'], log['color'] or '未记录')
        diarrhea = "💧拉肚子" if log['is_diarrhea'] else "✅正常"
        note = f" - **备注**：{log['notes']}" if log['notes'] else ""
        
        details_text += (
            f"**{end_time.day}日 {end_time.hour:02d}:{end_time.minute:02d}** "
            f"({duration_str}) - {color} {diarrhea}{note}\n"
        )
        if len(details_text) > 3500: # 避免 embed 字段过长
            details_text += f"\n... 还有 {len(filtered_logs) - (i+1)} 条记录未显示。"
            break
    
    embed.add_field(name="📋 详细记录", value=details_text or "无记录", inline=False)
    
    await interaction.followup.send(embed=embed)

@tree.command(name="排行榜", description="围观本服的“厕所之王”！")
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.defer() 
    server_leaderboard = database.get_server_leaderboard(interaction.guild.id)

    embed = discord.Embed(title=f"🏆🚽 {interaction.guild.name} 拉屎风云榜 🚽🏆", color=0xD4AF37)

    description = ""
    rank_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}

    for i, row in enumerate(server_leaderboard[:10]):
        rank = i + 1
        user_id, times, total_duration_sec = row[0], row[1], row[2] or 0
        try:
            user = interaction.guild.get_member(user_id) or await client.fetch_user(user_id)
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


client.run(TOKEN)

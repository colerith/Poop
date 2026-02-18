# cogs/core/constants.py
from discord import app_commands
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta

TZ = ZoneInfo("Asia/Shanghai")

HARDNESS_CHOICES = [
    app_commands.Choice(name="🪨 钻石级 (很硬)", value="very_hard"),
    app_commands.Choice(name="🧱 板砖级 (偏硬)", value="hard"),
    app_commands.Choice(name="🍌 香蕉级 (正常)", value="normal"),
    app_commands.Choice(name="🍦 雪糕级 (偏软)", value="soft"),
    app_commands.Choice(name="💧 瀑布级 (水状)", value="watery"),
]

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

COLOR_EMOJI_MAP = {
    "brown": "🟤",
    "yellow": "🟡",
    "black": "⚫",
    "green": "🟢",
    "other": "🔴",
    "未记录": "❔"
}

HARDNESS_EMOJI_MAP = {
    "very_hard": "🪨",
    "hard": "🧱",
    "normal": "🍌",
    "soft": "🍦",
    "watery": "💧",
    "未记录": "❔"
}

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
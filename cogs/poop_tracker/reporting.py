import calendar
from datetime import datetime

import discord

from ..core.constants import (
    COLOR_EMOJI_MAP,
    COLOR_MAP,
    HARDNESS_EMOJI_MAP,
    format_duration,
)


def build_weekly_details_embeds(user_display_name: str, filtered_logs, only_notes: bool) -> list[discord.Embed]:
    color_stats = {}
    diarrhea_count = 0

    for log in filtered_logs:
        color = COLOR_MAP.get(log["color"], log["color"] or "未记录")
        color_stats[color] = color_stats.get(color, 0) + 1
        if log["is_diarrhea"]:
            diarrhea_count += 1

    embed = discord.Embed(
        title=f"📊 {user_display_name} 的本周详细日志",
        description=f"共 {len(filtered_logs)} 条记录{'（仅显示有备注的记录）' if only_notes else ''}",
        color=0x7A5543,
    )

    color_text = "\n".join([
        f"{color}: {count}次" for color, count in sorted(color_stats.items(), key=lambda x: x[1], reverse=True)
    ])
    embed.add_field(name="🎨 颜色统计", value=color_text or "无数据", inline=False)
    embed.add_field(name="💧 拉肚子次数", value=f"{diarrhea_count}次", inline=True)
    embed.add_field(name="✅ 正常次数", value=f"{len(filtered_logs) - diarrhea_count}次", inline=True)

    details_text = ""
    weekdays = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
    for log in filtered_logs:
        end_time = datetime.fromisoformat(log["end_time"])
        start_time = datetime.fromisoformat(log["start_time"]) if log["start_time"] else None
        duration_seconds = (
            log["duration_seconds"]
            if log["duration_seconds"] is not None
            else (int((end_time - start_time).total_seconds()) if start_time else None)
        )
        duration_str = format_duration(duration_seconds)
        color = COLOR_MAP.get(log["color"], log["color"] or "未记录")
        diarrhea = "💧拉肚子" if log["is_diarrhea"] else "✅正常"
        note = f" - **备注**：{log['notes']}" if log["notes"] else ""

        details_text += f"**{weekdays[end_time.weekday()] + end_time.strftime(' %m-%d %H:%M')}** ({duration_str}) - {color} {diarrhea}{note}\n"

    # Discord 单字段最多 1024 字符、单条消息的 Embed 总计最多 6000 字符。
    # 以 UTF-16 单元保守分片，兼容中文、Emoji 以及很长的历史备注。
    chunks = []
    chunk = ""
    units = 0
    for char in details_text or "无记录":
        size = len(char.encode("utf-16-le")) // 2
        if units + size > 900:
            chunks.append(chunk)
            chunk, units = "", 0
        chunk += char
        units += size
    if chunk:
        chunks.append(chunk)
    embeds = [embed]
    for index, chunk in enumerate(chunks):
        if index and index % 4 == 0:
            embed = discord.Embed(title="📊 本周详细日志（续）", color=0x7A5543)
            embeds.append(embed)
        embed.add_field(name="📋 详细记录" if index == 0 else "📋 详细记录（续）", value=chunk, inline=False)
    for index, page in enumerate(embeds, 1):
        page.set_footer(text=f"第 {index}/{len(embeds)} 页")
    return embeds


def build_monthly_heatmap_embed(user_display_name: str, year: int, month: int, logs) -> discord.Embed:
    daily_data = {}
    for log in logs:
        day = datetime.fromisoformat(log["end_time"]).day
        if day not in daily_data:
            daily_data[day] = {"colors": set(), "hardnesses": set()}

        daily_data[day]["colors"].add(log["color"] or "未记录")
        daily_data[day]["hardnesses"].add(log["hardness"] or "未记录")

    cal = calendar.monthcalendar(year, month)

    color_heatmap = "`一  二  三  四  五  六  日`\n"
    for week in cal:
        for day in week:
            if day == 0:
                color_heatmap += "    "
                continue

            emoji = "⬜"
            if day in daily_data:
                colors = daily_data[day]["colors"]
                if len(colors) > 1:
                    emoji = "🌈"
                else:
                    color_key = list(colors)[0]
                    emoji = COLOR_EMOJI_MAP.get(color_key, "❔")

            color_heatmap += f"`{emoji}` "
        color_heatmap += "\n"

    hardness_heatmap = "`一  二  三  四  五  六  日`\n"
    for week in cal:
        for day in week:
            if day == 0:
                hardness_heatmap += "    "
                continue

            emoji = "⬜"
            if day in daily_data:
                hardnesses = daily_data[day]["hardnesses"]
                if len(hardnesses) > 1:
                    emoji = "❓"
                else:
                    hardness_key = list(hardnesses)[0]
                    emoji = HARDNESS_EMOJI_MAP.get(hardness_key, "❔")

            hardness_heatmap += f"`{emoji}` "
        hardness_heatmap += "\n"

    embed = discord.Embed(
        title=f"📅 {user_display_name} 的 {year}年{month}月拉屎热力图",
        color=0x7A5543,
    )
    embed.add_field(name="🎨 颜色分布", value=color_heatmap, inline=False)
    embed.add_field(name="🧱 软硬度分布", value=hardness_heatmap, inline=False)
    embed.set_footer(text="图例: ⬜=无记录, 🌈=多种颜色, ❓=多种硬度")
    return embed

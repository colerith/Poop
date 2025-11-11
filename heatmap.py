# heatmap.py

import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import calendar
from datetime import datetime
# --- 新增：导入字体管理器 ---
from matplotlib.font_manager import FontProperties
import os # 导入 os 库来检查文件是否存在

def create_heatmap(data, year, month, username=None):
    # --- 新增：定义字体文件路径并加载 ---
    font_path = 'NotoSansSC-Regular.otf' # 字体文件名需要和上传的文件完全一致

    # 检查字体文件是否存在
    if os.path.exists(font_path):
        # 创建字体属性对象
        font_prop = FontProperties(fname=font_path, size=16)
        font_prop_small = FontProperties(fname=font_path, size=10) # 用于标注日期
    else:
        # 如果字体文件不存在，则不使用特殊字体，避免报错
        print(f"警告：找不到字体文件 {font_path}。将使用默认字体。")
        font_prop = None
        font_prop_small = None

    days_in_month = calendar.monthrange(year, month)[1]

    poop_counts = {day: 0 for day in range(1, days_in_month + 1)}
    for row in data:
        end_time = datetime.fromisoformat(row['end_time'])
        if end_time.year == year and end_time.month == month:
            poop_counts[end_time.day] += 1

    first_weekday, _ = calendar.monthrange(year, month)
    cal_data = pd.DataFrame(float('nan'), index=range(6), columns=range(7))
    cal_days = pd.DataFrame(' ', index=range(6), columns=range(7))

    day_num = 1
    for week in range(6):
        for weekday in range(7):
            if (week == 0 and weekday < first_weekday) or day_num > days_in_month:
                continue
            else:
                cal_data.iloc[week, weekday] = poop_counts[day_num]
                # 在日期数字前加上 emoji
                emoji = "💩" if poop_counts[day_num] > 0 else ""
                cal_days.iloc[week, weekday] = f"{day_num}{emoji}"
                day_num += 1

    plt.figure(figsize=(10, 7))

    ax = sns.heatmap(cal_data, cmap="YlGnBu", annot=False, # 我们将手动添加标注
                     linewidths=2, cbar=False, square=True, 
                     xticklabels=False, yticklabels=False,
                     linecolor='white', na_color='#f0f0f0')

    # --- 新增：手动添加标注，并应用中文字体 ---
    for week in range(6):
        for weekday in range(7):
            day_str = cal_days.iloc[week, weekday].strip()
            if day_str:
                count = cal_data.iloc[week, weekday]
                color = "white" if count > (cal_data.max().max() / 2) else "black"
                ax.text(weekday + 0.5, week + 0.5, day_str,
                        ha='center', va='center', color=color,
                        fontproperties=font_prop_small) # 使用字体

    # --- 更新：为标题应用字体属性 ---
    title = f"{username}的 {year}年 {month}月 拉屎热力图" if username else f"{year}年 {month}月 拉屎热力图"
    plt.title(title, fontproperties=font_prop, pad=20)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='both', which='both', length=0) # 隐藏刻度线

    filepath = f"heatmap_{year}_{month}.png"
    plt.savefig(filepath, dpi=300, bbox_inches='tight', pad_inches=0.2)
    plt.close()
    return filepath
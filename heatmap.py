# heatmap.py

import matplotlib
matplotlib.use('Agg') # --- 新增：使用Agg后端，增强服务器兼容性 ---
import matplotlib.pyplot as plt
import pandas as pd
import calendar
from datetime import datetime
import numpy as np
import os
import seaborn as sns

def set_chinese_font():
    """
    一个更稳妥的函数，用于自动查找并设置可用的中文字体。
    """
    # 定义一个常用中文字体的列表，按优先级排序
    font_list = [
        'SimHei',
        'Microsoft YaHei',
        'PingFang SC',
        'WenQuanYi Micro Hei',
        'Noto Sans CJK SC',
        'Source Han Sans SC',
    ]
    
    for font in font_list:
        try:
            # 尝试设置字体，如果系统没有该字体会报错
            plt.rcParams['font.sans-serif'] = [font]
            plt.rcParams['axes.unicode_minus'] = False # 解决负号显示为方块的问题
            print(f"成功加载中文字体: {font}")
            return
        except Exception:
            continue
    
    # 如果列表中的字体都找不到
    print("警告: 未找到任何可用的中文字体，热力图标题可能显示不正确。")


def create_heatmap(data, year, month, username=None):
    """
    生成一个更美观、更稳定的月度活动日历热力图。
    """
    # --- 核心改动：在绘图前自动设置字体 ---
    set_chinese_font()
    
    # 1. 获取月份信息
    first_weekday, days_in_month = calendar.monthrange(year, month)
    
    # 2. 统计每天的次数
    poop_counts = {day: 0 for day in range(1, days_in_month + 1)}
    for row in data:
        # fromisoformat可以智能处理带时区或不带时区的时间字符串
        end_time = datetime.fromisoformat(row['end_time'])
        if end_time.year == year and end_time.month == month:
            poop_counts[end_time.day] += 1
            
    # 3. 构建日历网格数据 (使用Numpy，更高效)
    # 动态计算需要多少周（行）
    num_weeks = (days_in_month + first_weekday + 6) // 7
    cal_data = np.full((num_weeks, 7), np.nan) # 用NaN填充非本月日期
    annot_labels = np.full((num_weeks, 7), "", dtype=object) # 标注用的文字
    
    day_num = 1
    for week in range(num_weeks):
        for weekday in range(7):
            if (week == 0 and weekday < first_weekday) or day_num > days_in_month:
                continue
            
            count = poop_counts.get(day_num, 0)
            cal_data[week, weekday] = count
            emoji = " 💩" if count > 0 else ""
            annot_labels[week, weekday] = f"{day_num}{emoji}"
            day_num += 1

    # 4. 开始绘图
    # 动态调整图形高度以适应不同周数的月份
    fig_height = 2 + num_weeks * 1.2 
    fig, ax = plt.subplots(figsize=(10, fig_height))

    # 使用Seaborn绘制热力图
    # "Greens" 色系很符合主题 ;)
    sns.heatmap(
        cal_data,
        annot=annot_labels,
        fmt="", # 因为我们提供了完整的字符串作为标注，所以格式化字符串为空
        cmap="Greens",
        linewidths=4,
        linecolor='white',
        cbar=False, # 不需要颜色条
        square=True,
        ax=ax,
        na_color="#f9f9f9" # 为非本月日期设置一个浅灰色
    )

    # 5. 美化与定制
    # 设置标题
    title = f"{username} 的 {year}年{month}月「解放」热力图"
    ax.set_title(title, fontsize=20, pad=25)

    # 设置星期的标签，并移到顶部
    ax.set_xticklabels(['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'], fontsize=12)
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position('top')
    
    # 移除y轴的刻度
    ax.set_yticks([])
    
    # 移除边框和刻度线
    ax.tick_params(axis='both', which='both', length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # 6. 保存图像
    # 使用用户名和时间戳确保文件名唯一，防止并发请求时文件被覆盖
    timestamp = int(datetime.now().timestamp())
    filepath = f"heatmap_{username}_{year}_{month}_{timestamp}.png"
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close(fig) # 关闭图形，释放内存
    
    return filepath

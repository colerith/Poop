# database.py

import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('poop.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS poop_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            hardness TEXT,
            is_diarrhea BOOLEAN,
            color TEXT,
            notes TEXT,
            start_time DATETIME,
            end_time DATETIME,
            duration_seconds INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def add_poop_log(user_id, guild_id, hardness, is_diarrhea, color, notes, start_time, end_time):
    conn = sqlite3.connect('poop.db')
    c = conn.cursor()
    duration_seconds = None
    if start_time and end_time:
        duration_seconds = (end_time - start_time).total_seconds()

    c.execute('''
        INSERT INTO poop_log (user_id, guild_id, hardness, is_diarrhea, color, notes, start_time, end_time, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, guild_id, hardness, is_diarrhea, color, notes, start_time, end_time, duration_seconds))
    conn.commit()
    conn.close()

def get_monthly_logs(user_id, guild_id, year, month):
    conn = sqlite3.connect('poop.db')
    # 使用 sqlite3.Row 可以让我们通过列名访问数据，更方便
    conn.row_factory = sqlite3.Row 
    c = conn.cursor()
    c.execute('''
        SELECT * FROM poop_log
        WHERE user_id = ? AND guild_id = ? AND
              strftime('%Y', end_time) = ? AND
              strftime('%m', end_time) = ?
        ORDER BY end_time DESC
    ''', (user_id, guild_id, str(year), str(month).zfill(2)))
    logs = c.fetchall()
    conn.close()
    return logs

def get_server_leaderboard(guild_id):
    conn = sqlite3.connect('poop.db')
    c = conn.cursor()
    c.execute('''
        SELECT user_id, COUNT(*), SUM(duration_seconds)
        FROM poop_log
        WHERE guild_id = ? AND duration_seconds IS NOT NULL
        GROUP BY user_id
        ORDER BY COUNT(*) DESC, SUM(duration_seconds) DESC
    ''', (guild_id,))
    leaderboard = c.fetchall()
    conn.close()
    return leaderboard

# --- 新增函数 ---
def get_last_poop_log(user_id, guild_id):
    """获取指定用户在服务器的最后一条记录"""
    conn = sqlite3.connect('poop.db')
    conn.row_factory = sqlite3.Row 
    c = conn.cursor()
    c.execute('''
        SELECT * FROM poop_log
        WHERE user_id = ? AND guild_id = ?
        ORDER BY end_time DESC
        LIMIT 1
    ''', (user_id, guild_id))
    log = c.fetchone()
    conn.close()
    return log

# --- 新增函数 ---
def delete_poop_log(log_id):
    """根据记录的ID删除它"""
    conn = sqlite3.connect('poop.db')
    c = conn.cursor()
    c.execute('DELETE FROM poop_log WHERE id = ?', (log_id,))
    conn.commit()
    conn.close()
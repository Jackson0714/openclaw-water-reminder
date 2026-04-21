#!/usr/bin/env python3
"""
喝水提醒系统（PostgreSQL版）
- cron: 每天8:30-17:00每小时触发提醒
- 用户回复"喝了xxxml"自动累计
- 支持问累计、统计报表、周报
"""

import json
import sys
import os
from datetime import datetime, date, timedelta
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

# PostgreSQL 配置
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "database": "water_tracker",
    "user": "water",
    "password": "water123"
}

USER_ID = "default"
TODAY = date.today()
NOW = datetime.now()

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def add_water(ml, user_id=USER_ID):
    """用户报告喝水量"""
    conn = get_conn()
    cur = conn.cursor()
    
    today = date.today()
    now = datetime.now()
    
    # 插入记录
    cur.execute(
        "INSERT INTO water_log (user_id, drank_at, amount_ml) VALUES (%s, %s, %s) RETURNING id",
        (user_id, now, ml)
    )
    
    # 更新每日汇总（upsert）
    cur.execute("""
        INSERT INTO water_daily (user_id, log_date, total_ml, updated_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, log_date)
        DO UPDATE SET total_ml = water_daily.total_ml + EXCLUDED.total_ml,
                       updated_at = EXCLUDED.updated_at
        RETURNING total_ml
    """, (user_id, today, ml, now))
    
    total = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    
    # 获取目标
    goal = get_goal(user_id)
    remaining = goal - total
    
    if remaining <= 0:
        return f"✅ 已记录！今日累计：{total}ml，已达标🎉", True
    else:
        return f"✅ 已记录！今日累计：{total}ml，还差 {remaining}ml，加油💪", True

def get_status(user_id=USER_ID):
    """获取当前状态"""
    today = date.today()
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute(
        "SELECT total_ml, goal_ml FROM water_daily WHERE user_id=%s AND log_date=%s",
        (user_id, today)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if row:
        total = row['total_ml']
        goal = row['goal_ml']
    else:
        total = 0
        goal = get_goal(user_id)
    
    remaining = goal - total
    if remaining <= 0:
        return f"📊 今日喝水：{total}ml / {goal}ml，已达标🎉"
    return f"📊 今日喝水：{total}ml / {goal}ml，还差 {remaining}ml"

def get_goal(user_id=USER_ID):
    """获取每日目标"""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT goal_ml FROM water_settings WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row['goal_ml'] if row else 2000

def get_report(user_id=USER_ID):
    """生成日报表"""
    today = date.today()
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 今日汇总
    cur.execute(
        "SELECT total_ml, goal_ml FROM water_daily WHERE user_id=%s AND log_date=%s",
        (user_id, today)
    )
    row = cur.fetchone()
    total = row['total_ml'] if row else 0
    goal = row['goal_ml'] if row else get_goal(user_id)
    remaining = goal - total
    pct = min(100, int(total / goal * 100)) if goal > 0 else 0
    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
    
    # 今日明细
    cur.execute(
        "SELECT drank_at, amount_ml FROM water_log WHERE user_id=%s AND DATE(drank_at)=%s ORDER BY drank_at",
        (user_id, today)
    )
    logs = cur.fetchall()
    cur.close()
    conn.close()
    
    lines = [
        f"💧 喝水日报 {today}",
        f"━━━━━━━━━━━━━━━━",
        f"目标：{goal}ml",
        f"已喝：{total}ml",
        f"进度：[{bar}] {pct}%",
    ]
    
    if remaining <= 0:
        lines.append("状态：✅ 今日已达标！")
    else:
        lines.append(f"状态：⏳ 还差 {remaining}ml")
    
    if logs:
        lines.append("明细：")
        for entry in logs:
            t = entry['drank_at'].strftime("%H:%M")
            lines.append(f"  • {t}  +{entry['amount_ml']}ml")
    
    return "\n".join(lines)

def get_weekly_report(user_id=USER_ID, weeks_ago=1):
    """生成周报表（上周）"""
    today = date.today()
    # 上周一
    week_start = today - timedelta(days=today.weekday() + 7 * weeks_ago)
    week_end = week_start + timedelta(days=6)
    
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT log_date, total_ml, goal_ml
        FROM water_daily
        WHERE user_id=%s AND log_date >= %s AND log_date <= %s
        ORDER BY log_date
    """, (user_id, week_start, week_end))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    # 补充缺失日期
    day_data = {r['log_date']: r for r in rows}
    goal = get_goal(user_id)
    
    total_week = 0
    days_met = 0
    lines = [
        f"💧 喝水周报 {week_start} ~ {week_end}",
        f"━━━━━━━━━━━━━━━━",
        f"每日目标：{goal}ml",
        ""
    ]
    
    cur_date = week_start
    while cur_date <= week_end:
        if cur_date in day_data:
            d = day_data[cur_date]
            pct = min(100, int(d['total_ml'] / d['goal_ml'] * 100))
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            emoji = "✅" if d['total_ml'] >= d['goal_ml'] else "📍"
            lines.append(f"{emoji} {cur_date.strftime('%m/%d %a')}  {d['total_ml']}ml / {d['goal_ml']}ml  [{bar}] {pct}%")
            total_week += d['total_ml']
            if d['total_ml'] >= d['goal_ml']:
                days_met += 1
        else:
            lines.append(f"❌ {cur_date.strftime('%m/%d %a')}  无记录")
        cur_date += timedelta(days=1)
    
    lines.append("")
    lines.append(f"周累计：{total_week}ml")
    avg = total_week / 7 if total_week > 0 else 0
    lines.append(f"日均：{int(avg)}ml")
    lines.append(f"达标天数：{days_met}/7")
    
    if total_week > 0:
        pct = min(100, int(total_week / (goal * 7) * 100))
        lines.append(f"整体完成率：{pct}%")
    
    return "\n".join(lines)

def should_remind(user_id=USER_ID):
    """判断是否需要提醒"""
    today = date.today()
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute(
        "SELECT total_ml, goal_ml, reminded FROM water_daily WHERE user_id=%s AND log_date=%s",
        (user_id, today)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if row:
        if row['total_ml'] >= row['goal_ml']:
            return "already_met", None
        if row['reminded']:
            return "already_reminded", None
        return "need_remind", None
    return "need_remind", None

def mark_reminded(user_id=USER_ID):
    today = date.today()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO water_daily (user_id, log_date, total_ml, reminded)
        VALUES (%s, %s, 0, TRUE)
        ON CONFLICT (user_id, log_date)
        DO UPDATE SET reminded = TRUE
    """, (user_id, today))
    conn.commit()
    cur.close()
    conn.close()

def get_reminder_message(user_id=USER_ID):
    goal = get_goal(user_id)
    return (
        f"💧 喝水提醒！\n"
        f"今日目标：{goal}ml\n\n"
        "每隔一小时提醒你一次。\n"
        "回复「喝了XXXml」来记录，比如「喝了300ml」"
    )

def get_already_met_message(user_id=USER_ID):
    today = date.today()
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT total_ml, goal_ml FROM water_daily WHERE user_id=%s AND log_date=%s",
        (user_id, today)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    total = row['total_ml'] if row else 0
    goal = row['goal_ml'] if row else get_goal(user_id)
    
    return (
        f"🎉 今日已达标！\n"
        f"当前累计：{total}ml / {goal}ml\n"
        f"继续保持～"
    )

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if cmd == "status":
        print(get_status())
    
    elif cmd == "add":
        ml = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        msg, _ = add_water(ml)
        print(msg)
    
    elif cmd == "report":
        print(get_report())
    
    elif cmd == "weekly":
        weeks = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        print(get_weekly_report(weeks_ago=weeks))
    
    elif cmd == "check":
        reason, _ = should_remind()
        if reason == "already_met":
            print("ALREADY_MET")
        elif reason == "already_reminded":
            print("SKIP")
        else:
            print("REMIND")
    
    elif cmd == "reset":
        today = date.today()
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM water_log WHERE user_id=%s AND DATE(drank_at)=%s",
            (USER_ID, today)
        )
        cur.execute(
            "DELETE FROM water_daily WHERE user_id=%s AND log_date=%s",
            (USER_ID, today)
        )
        conn.commit()
        cur.close()
        conn.close()
        print("已重置")

if __name__ == "__main__":
    main()

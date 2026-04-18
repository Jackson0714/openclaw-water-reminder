#!/usr/bin/env python3
"""
喝水提醒系统
- cron: 每天8:30-17:00每小时触发提醒
- 用户回复"喝了xxxml"自动累计
- 支持问累计、统计报表
"""

import json
import sys
import os
from datetime import datetime, date
from pathlib import Path

DATA_FILE = Path("/root/.openclaw/workspace/water_tracker.json")
WORKSPACE = Path("/root/.openclaw/workspace")

TODAY = date.today().isoformat()
NOW = datetime.now()

def load_data():
    if not DATA_FILE.exists():
        return {"date": "", "total_ml": 0, "goal_ml": 2000, "reminded_today": False, "log": []}
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def reset_if_new_day(data):
    """跨天后重置"""
    if data["date"] != TODAY:
        return {
            "date": TODAY,
            "total_ml": 0,
            "goal_ml": 2000,
            "reminded_today": False,
            "log": []
        }
    return data

def add_water(ml):
    """用户报告喝水量"""
    data = load_data()
    data = reset_if_new_day(data)
    data["total_ml"] += ml
    data["log"].append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "ml": ml
    })
    save_data(data)
    
    remaining = data["goal_ml"] - data["total_ml"]
    if remaining <= 0:
        return f"✅ 已记录！今日累计：{data['total_ml']}ml，已达标🎉", True
    else:
        return f"✅ 已记录！今日累计：{data['total_ml']}ml，还差 {remaining}ml，加油💪", True

def get_status():
    """获取当前状态"""
    data = load_data()
    data = reset_if_new_day(data)
    remaining = data["goal_ml"] - data["total_ml"]
    if remaining <= 0:
        return f"📊 今日喝水：{data['total_ml']}ml / {data['goal_ml']}ml，已达标🎉"
    return f"📊 今日喝水：{data['total_ml']}ml / {data['goal_ml']}ml，还差 {remaining}ml"

def get_report():
    """生成日报表"""
    data = load_data()
    data = reset_if_new_day(data)
    total = data["total_ml"]
    goal = data["goal_ml"]
    remaining = goal - total
    pct = min(100, int(total / goal * 100))
    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
    
    lines = [
        f"💧 喝水日报 {data['date']}",
        f"━━━━━━━━━━━━━━━━",
        f"目标：{goal}ml",
        f"已喝：{total}ml",
        f"进度：[{bar}] {pct}%",
    ]
    
    if remaining <= 0:
        lines.append("状态：✅ 今日已达标！")
    else:
        lines.append(f"状态：⏳ 还差 {remaining}ml")
    
    if data["log"]:
        lines.append("明细：")
        for entry in data["log"]:
            lines.append(f"  • {entry['time']}  +{entry['ml']}ml")
    
    return "\n".join(lines)

def should_remind():
    """判断是否需要提醒"""
    data = load_data()
    data = reset_if_new_day(data)
    if data["total_ml"] >= data["goal_ml"]:
        return "already_met", data
    if data["reminded_today"]:
        return "already_reminded", data
    return "need_remind", data

def mark_reminded(data):
    data["reminded_today"] = True
    save_data(data)

def get_reminder_message():
    """获取提醒消息内容"""
    return (
        "💧 喝水提醒！\n"
        "今日目标：2000ml\n\n"
        "每隔一小时提醒你一次。\n"
        "回复「喝了XXXml」来记录，比如「喝了300ml」"
    )

def get_already_met_message(data):
    """达标后不再提醒的消息"""
    return (
        f"🎉 今日已达标！\n"
        f"当前累计：{data['total_ml']}ml / {data['goal_ml']}ml\n"
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
    
    elif cmd == "reset":
        data = {
            "date": TODAY,
            "total_ml": 0,
            "goal_ml": 2000,
            "reminded_today": False,
            "log": []
        }
        save_data(data)
        print("已重置")
    
    elif cmd == "check":
        # 检查是否需要提醒，返回相应消息（供 cron 使用）
        data = load_data()
        data = reset_if_new_day(data)
        reason, data = should_remind()
        
        if reason == "already_met":
            print("ALREADY_MET")
        elif reason == "already_reminded":
            print("SKIP")
        else:
            print("REMIND")

if __name__ == "__main__":
    main()

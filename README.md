# 💧 OpenClaw 喝水提醒助手

基于 OpenClaw 的智能喝水追踪助手，每小时自动提醒你喝水，帮你养成每天喝够 2000ml 的好习惯。

## 功能

- ⏰ **定时提醒**：每天 8:30～16:30 每小时提醒一次（可自定义时间）
- 📊 **智能累计**：你回复"喝了 300ml"自动累加，达标后不再打扰
- 📋 **进度查询**：随时问"今天喝了多少"查看当前进度
- 📈 **日报表**：输入"喝水报表"生成带进度条的详细报告
- 🔄 **自动重置**：每天早上自动清零，从头来过

## 快速开始

### 前提条件

- 已在服务器上安装 [OpenClaw](https://docs.openclaw.ai)
- OpenClaw 已配置好微信（openclaw-weixin）通道
- 服务器有 4GB+ 可用空间

### 第一步：上传脚本

将 `water_reminder.py` 上传到你的 OpenClaw workspace 目录：

```bash
# 连接到你的服务器，在 workspace 下创建 scripts 目录
mkdir -p ~/.openclaw/workspace/scripts
# 上传 water_reminder.py 到该目录
```

### 第二步：初始化数据文件

在服务器上执行一次初始化：

```bash
python3 ~/.openclaw/workspace/scripts/water_reminder.py reset
```

正常输出：`已重置`

### 第三步：创建定时任务

在 OpenClaw 服务器上执行以下命令，创建每小时提醒的 cron 任务：

```bash
# 查看你的微信账号 ID（记住 AccountId）
openclaw channels list

# 创建提醒 cron 任务（把 YOUR_ACCOUNT_ID 替换成上一步查到的）
openclaw cron add \
  --name "water-reminder" \
  --description "每天8:30-16:30每小时喝水提醒" \
  --cron "30 8-16 * * *" \
  --tz "Asia/Shanghai" \
  --session isolated \
  --tools exec,read \
  --message '你是一个喝水提醒助手。读取 /root/.openclaw/workspace/water_tracker.json 查看今日喝水进度。

根据数据决定：
- 如果已达标（>=2000ml）：回复「SKIP」（不发提醒）
- 如果今天已提醒过（reminded_today=true）：回复「SKIP」
- 否则：读取数据后，发送一条微信消息给对方（微信ID: 对方的微信ID，channel: openclaw-weixin，accountId: 你的accountId），内容格式：
  「💧 喝水提醒！
今日已喝：Xxml / 2000ml
还差：Xml
回复「喝了xxxml」记录 ✨」
发完消息后，用 exec 工具执行：python3 -c \"import json; d=json.load(open('\''/root/.openclaw/workspace/water_tracker.json'\'')); d['\''reminded_today'\'']=True; json.dump(d,open('\''/root/.openclaw/workspace/water_tracker.json'\'','\''w'\''),ensure_ascii=False,indent=2)\" 把 reminded_today 设为 true。' \
  2>&1
```

### 第四步：验证是否正常

```bash
# 测试手动触发一次提醒
openclaw cron run $(openclaw cron list --json | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

# 查看当前喝水状态
python3 ~/.openclaw/workspace/scripts/water_reminder.py status

# 查看完整日报
python3 ~/.openclaw/workspace/scripts/water_reminder.py report
```

---

## 使用方法

在微信（或其他配置的频道）里直接发消息给机器人：

| 你发送 | 机器人回复 |
|---|---|
| `喝了300ml` | ✅ 已记录！今日累计：300ml，还差 1700ml |
| `喝了500ml` | ✅ 已记录！今日累计：800ml，还差 1200ml |
| `今天喝了多少` | 📊 今日喝水：800ml / 2000ml，还差 1200ml |
| `喝水报表` | 完整的日报，包含进度条和明细记录 |

---

## 自定义修改

### 修改每日目标

编辑 `water_tracker.json`，修改 `goal_ml` 的值（单位：ml）：

```json
{
  "goal_ml": 2500
}
```

### 修改提醒时间段

编辑 cron 任务：

```bash
# 比如改成早上 9 点到晚上 8 点，每半小时提醒一次
openclaw cron edit YOUR_JOB_ID --cron "0,30 9-20 * * *"
```

### 修改提醒间隔

```bash
# 每小时一次（默认）
--cron "30 8-16 * * *"

# 每半小时一次
--cron "0,30 8-16 * * *"

# 每2小时一次
--cron "30 8-16/2 * * *"
```

### 完全删除提醒任务

```bash
# 先查看任务 ID
openclaw cron list

# 删除
openclaw cron rm YOUR_JOB_ID
```

---

## 文件说明

| 文件 | 用途 |
|---|---|
| `water_reminder.py` | 核心追踪脚本 |
| `~/.openclaw/workspace/water_tracker.json` | 数据存储（自动创建） |

### 数据文件格式

```json
{
  "date": "2026-04-18",
  "total_ml": 142,
  "goal_ml": 2000,
  "reminded_today": false,
  "log": [
    {"time": "07:46:42", "ml": 82},
    {"time": "07:55:20", "ml": 60}
  ]
}
```

---

## 命令行参考

```bash
# 查看状态
python3 water_reminder.py status

# 手动添加喝水量（用于调试）
python3 water_reminder.py add 300

# 生成报表
python3 water_reminder.py report

# 重置今天的数据
python3 water_reminder.py reset

# 查看 cron 任务列表
openclaw cron list

# 手动触发一次提醒
openclaw cron run YOUR_JOB_ID

# 查看 cron 运行历史
openclaw cron runs --id YOUR_JOB_ID
```

---

## 常见问题

**Q: 提醒没有收到怎么办？**
A: 检查 cron 是否启用：`openclaw cron list`，确认 `enabled: true`

**Q: 周末也需要提醒吗？**
A: 当前配置是每天 8:30-16:30，包括周末。如需改成工作日，把 `--cron "30 8-16 * * *"` 改成 `--cron "30 8-16 * * 1-5"`

**Q: 能改喝水目标吗？**
A: 能，编辑 `water_tracker.json` 中的 `goal_ml` 字段即可

---

## 项目结构

```
water-reminder/
├── README.md              # 本文件
└── water_reminder.py      # 核心脚本
```

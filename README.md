# 🎧 English Bot

> **每天自动推送 2 个精选英语视频，由 Gemini AI 分析内容，生成词汇卡片 + 摘要 + 句型 + 语法，发送到你的邮箱。**

&nbsp;

```
GitHub Actions 定时触发
       ↓
Gemini AI 自由选题（或你手动指定）
       ↓
YouTube Data API 搜索最热门英语视频
       ↓
Gemini 直接分析视频内容（无需下载字幕）
       ↓
生成词汇卡片 + 摘要 + 句型 + 语法亮点
       ↓
每天 08:00 发送到你的邮箱 📬
```

&nbsp;

## ✨ 功能特点

- **零维护** — 部署一次，每天自动运行，无需服务器
- **AI 自由选题** — Gemini 根据历史记录自动选择不重复的话题，或你随时手动指定
- **智能筛选视频** — 按播放量、点赞量综合评分排序，过滤非英美口音，精选 20 分钟内的视频
- **非英语自动跳过** — Gemini 判断语言，非英语视频自动补位，保证每天 2 个
- **原生视频理解** — Gemini 直接读取 YouTube URL，理解语气和语境，无需字幕
- **墨墨记忆卡兼容** — 词汇卡片以附件形式发送，可直接导入墨墨 App

&nbsp;

## 📬 每日邮件内容

每封邮件包含 **2 个视频** 的分析，以及 **2 个 `.txt` 附件**：

| 邮件正文 | 附件 |
|---|---|
| 视频缩略图 + 跳转链接 | `markji_YYYY-MM-DD_video1.txt` |
| 📝 视频摘要（3-4句） | `markji_YYYY-MM-DD_video2.txt` |
| 💬 实用句型（3-5条） | 墨墨格式，可直接导入 |
| 🔤 语法亮点（1-2条） | |
| 📖 词汇卡片在附件中 | |

**词汇卡片格式（墨墨兼容）：**

```
pitch in
---
共同出力；凑钱帮忙
Everyone pitched in to get the boss a birthday gift.
大家一起凑钱给老板买了生日礼物。

nail it
---
完美完成；做得很棒
She totally nailed the presentation today.
她今天的演讲做得非常出色。
```

&nbsp;

## 🗂️ 项目结构

```
english_bot/
├── .github/
│   └── workflows/
│       └── daily.yml          # GitHub Actions 定时任务
├── main.py                    # 入口，串联所有模块
├── topic_picker.py            # 话题选择（AI 自动 / 手动指定）
├── youtube_fetcher.py         # YouTube 搜索 + 评分排序
├── gemini_analyzer.py         # Gemini 视频分析 + 内容解析
├── email_sender.py            # 邮件构建 + QQ SMTP 发送
├── config.json                # 手动指定话题写这里
├── history.json               # 已推送视频和话题记录（自动维护）
└── requirements.txt           # Python 依赖
```

&nbsp;

## 🚀 部署教程

### 第一步：准备 API Keys

| Key | 获取地址 |
|---|---|
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) → Get API Key |
| `YOUTUBE_API_KEY` | [console.cloud.google.com](https://console.cloud.google.com) → 启用 YouTube Data API v3 → 凭据 → 创建 API 密钥 |
| `QQ_MAIL_PASSWORD` | QQ 邮箱网页版 → 设置 → 账户 → 开启 SMTP → 生成授权码（16位，非登录密码） |

### 第二步：Fork 或克隆本仓库

```bash
git clone https://github.com/你的用户名/english_bot.git
cd english_bot
```

### 第三步：添加 GitHub Secrets

进入仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

添加以下 5 个 Secret：

```
GEMINI_API_KEY       你的 Gemini API Key
YOUTUBE_API_KEY      你的 YouTube Data API Key
QQ_MAIL_USER         你的QQ邮箱，如 123456@qq.com
QQ_MAIL_PASSWORD     QQ 邮箱 16 位授权码
TO_EMAIL             接收邮件的地址（可以是同一个 QQ 邮箱）
```

### 第四步：开启 Actions 写权限

仓库 → **Settings** → **Actions** → **General** → **Workflow permissions** → 选 **Read and write permissions** → Save

### 第五步：手动触发测试

仓库 → **Actions** → **Daily English Bot** → **Run workflow**

可以在 topic 输入框填入话题（如 `咖啡店点单`）测试，留空则 AI 自动选题。

等待约 1 分钟，检查邮箱是否收到邮件 ✅

&nbsp;

## ⚙️ 话题控制

### 方式一：让 AI 自动选题（默认）

什么都不做，Gemini 每天根据历史记录自由生成一个新话题，保证不重复。

### 方式二：手动修改 `config.json`

编辑仓库里的 `config.json`：

```json
{
  "topic": "在美国租房谈合同"
}
```

下次运行会使用这个话题，用完自动清空，之后恢复 AI 自动选题。

### 方式三：触发 Actions 时传参数

仓库 → Actions → Daily English Bot → Run workflow → 在 topic 输入框填入话题

优先级：`Actions 参数` > `config.json` > `AI 自动`

&nbsp;

## 💰 费用估算

| 服务 | 费用 |
|---|---|
| Gemini 2.5 Flash | 约 ¥0.02 / 天（每月 < ¥1） |
| YouTube Data API | 免费（每日配额足够） |
| GitHub Actions | 免费（每月 2000 分钟，每天用不到 2 分钟） |
| QQ 邮件 SMTP | 免费 |
| **合计** | **每月 < ¥1** |

> Gemini API 有免费层，初期完全免费，稳定后再考虑是否付费。

&nbsp;

## 🛠️ 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export GEMINI_API_KEY=你的key
export YOUTUBE_API_KEY=你的key
export QQ_MAIL_USER=你的邮箱
export QQ_MAIL_PASSWORD=你的授权码
export TO_EMAIL=接收邮箱

# 手动指定话题（可选）
export MANUAL_TOPIC=咖啡店点单

# 运行
python main.py
```

&nbsp;

## 📦 依赖

```
google-genai
google-api-python-client
requests
```

Python 3.11+

&nbsp;

## 📄 License

MIT © 2026 Alan-stro

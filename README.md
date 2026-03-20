# LingoPost 📬
### 语言邮差 · 每天准时投递一份英语学习包

> 每天早上八点，一封英语学习邮件准时投进你的收件箱。

LingoPost 是一个运行在 GitHub Actions 上的个人英语学习机器人。它每天自动从 YouTube 挑选英语视频，用 Gemini AI 分析内容，提取单词卡、语法亮点和地道句型，以精美的 HTML 邮件发送给你——同时把所有历史记录沉淀到一个静态看板，构成你专属的英语学习档案。

---

## 功能概览

### 📺 智能选片
- 用 Gemini AI 自动生成今日话题（也可手动指定），确保话题多样、贴近真实英语语境
- 支持**频道白名单**：收藏喜欢的 YouTube 频道，每天优先从中推送一个视频
- 全网搜索兜底：白名单找不到合适内容时自动切换，保证每天稳定推送两个视频
- 视频去重、时长过滤（4–20 分钟）、英美口音过滤、热度排序

### 🤖 AI 深度分析
每个视频由 Gemini 2.5 Flash 生成：

| 内容 | 说明 |
|------|------|
| 单词卡片 | 5–8 个符合当日难度的词汇，含释义、例句、中文翻译 |
| 发音指南 | 音标 + 中国人易读错的发音说明 |
| 视频摘要 | 3–4 句中文概括 |
| 地道句型 | 3–5 个口语句型，含中文解释 |
| 语法亮点 | 1–2 个语法点，含视频原句示例 |

### 📊 难度自适应
- 支持 A2 / B1 / B2 / C1 / C2 五级
- 根据你的反馈（太简单 / 太难）自动调整下次难度
- 白名单视频额外经过难度匹配检测，避免推送远超当前水平的内容

### 🗂️ 学习看板
所有历史推送记录自动生成静态看板，托管在 GitHub Pages：
- 搜索标题、话题、单词、语法点全文
- 按话题、难度等级、来源（白名单 / 全网）筛选
- 展开每条记录查看完整单词卡和分析内容

---

## 项目结构

```
LingoPost/
├── main.py              # 主流程
├── topic_picker.py      # 话题 & 难度选择（含中文自动翻译）
├── youtube_fetcher.py   # YouTube 搜索 & 白名单频道搜索
├── gemini_analyzer.py   # Gemini AI 视频分析
├── email_sender.py      # HTML 邮件发送
├── utils.py             # 工具函数
├── channels.json        # 频道白名单配置
├── config.json          # 手动话题 / 难度配置
├── history.json         # 推送历史（自动维护）
├── records.json         # 完整分析记录，供看板使用（自动维护）
├── index.html           # Web 看板页面
└── .github/
    └── workflows/
        └── daily.yml    # GitHub Actions 定时任务
```

---

## 快速开始

### 1. Fork 本仓库

点击右上角 **Fork**，将项目复制到你自己的 GitHub 账号下。

### 2. 配置 Secrets

进入仓库 **Settings → Secrets and variables → Actions**，添加以下五个 Secret：

| Secret 名称 | 说明 |
|-------------|------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) 申请，免费额度足够日常使用 |
| `YOUTUBE_API_KEY` | [Google Cloud Console](https://console.cloud.google.com/) 启用 YouTube Data API v3 |
| `QQ_MAIL_USER` | 你的 QQ 邮箱地址 |
| `QQ_MAIL_PASSWORD` | QQ 邮箱**授权码**（非登录密码，在邮箱设置中生成） |
| `TO_EMAIL` | 接收邮件的邮箱地址 |

### 3. 配置频道白名单（可选）

编辑 `channels.json`，填入你喜欢的 YouTube 频道 ID：

```json
{
  "enabled": true,
  "fallback_to_search": true,
  "channels": [
    { "name": "The Economist", "channel_id": "UC0p5jTq6Xx_DosDFxVXnWaQ" },
    { "name": "English Podd",  "channel_id": "UCWhX9SjClPqpgnfOqnzLyGQ" }
  ]
}
```

> 获取频道 ID：在 YouTube 频道页面右键「查看页面源码」，搜索 `channelId` 即可找到 `UCxxxxxx` 格式的 ID。

### 4. 开启 GitHub Pages（看板）

进入仓库 **Settings → Pages**，Source 选择 `Deploy from a branch`，Branch 选 `main`，目录选 `/ (root)`，保存后稍等一分钟，即可通过 `https://你的用户名.github.io/LingoPost/` 访问学习看板。

### 5. 触发第一次运行

进入仓库 **Actions → Daily English Bot → Run workflow**，点击 **Run workflow** 手动触发一次，验证配置是否正确。

---

## 手动控制

在 Actions 页面手动触发时，可以填写以下参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| `topic` | 指定今日话题，支持中文（自动翻译为英文） | `旅行` 或 `travel tips` |
| `difficulty` | 指定难度等级 | `B1` / `B2` / `C1` |
| `feedback` | 对昨天内容的反馈，影响下次难度 | `too_easy` / `too_hard` |

留空则全部由 AI 自动决定。

---

## 运行时间

默认每天 **UTC 00:00**（北京时间 08:00）自动运行。

如需修改，编辑 `.github/workflows/daily.yml` 中的 cron 表达式：

```yaml
- cron: '0 0 * * *'  # UTC 时间，0 0 = 00:00
```

---

## 技术栈

- **运行环境**：GitHub Actions（完全免费）
- **AI 分析**：Google Gemini 2.5 Flash
- **视频来源**：YouTube Data API v3
- **邮件发送**：Python `smtplib` + QQ 邮箱 SMTP
- **看板托管**：GitHub Pages（纯静态，无需服务器）

---

## 常见问题

**Q：Gemini / YouTube API 免费额度够用吗？**
每天运行一次，分析两个视频，Gemini 免费额度完全足够。YouTube Data API 每日免费配额为 10,000 单位，每次运行消耗约 100 单位，也绰绰有余。

**Q：为什么有时候只推送了一个视频？**
YouTube 搜索结果经过时长、口音、去重多重过滤后，有时候合格的候选视频不足两个。这是正常现象，不影响整体使用。

**Q：看板数据什么时候更新？**
每次 Actions 运行完成后，`records.json` 会自动 commit 回仓库，GitHub Pages 随即刷新，通常延迟不超过 2 分钟。

**Q：手动输入中文话题可以吗？**
可以。`topic_picker.py` 会自动检测中文并调用 Gemini 翻译成适合 YouTube 搜索的英文关键词。

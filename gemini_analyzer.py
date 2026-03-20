import os
import re
import google.generativeai as genai


# ── 时长解析 ────────────────────────────────────────────────
def parse_duration_seconds(iso: str) -> int:
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not match:
        return 0
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    return h * 3600 + m * 60 + s

def is_within_duration(iso: str, max_minutes: int = 20) -> bool:
    return parse_duration_seconds(iso) <= max_minutes * 60


# ── Gemini 分析 ─────────────────────────────────────────────
PROMPT = """请分析这个视频，完成以下两步：

第一步：判断视频主要语言。
如果主要语言不是英语，只输出一行：NOT_ENGLISH
然后停止，不要输出任何其他内容。

第二步：如果是英语视频，从中挑选 5-8 个最有学习价值的单词或短语，优先选择：
- 地道口语短语、动词短语（phrasal verbs）
- 高频但中国学习者容易用错的词
- 视频语境中出现的习语或固定搭配
- 避免过于基础的词，如 good, make, go 等

然后在下方输出词汇卡片内容，再输出摘要和句型语法，严格按照以下格式：

---CARDS---
英文单词或短语
---
中文核心释义
英文例句（贴合视频语境）
中文例句

英文单词或短语
---
中文核心释义
英文例句（贴合视频语境）
中文例句

（每张卡之间空一行，正面只写英文，不写词性、序号或任何说明）

---SUMMARY---
用 3-4 句中文概括视频主要内容。

---SENTENCES---
3-5 个地道口语句型，每条一行，格式：
原句 | 中文解释

---GRAMMAR---
1-2 个语法亮点，每条一行，格式：
语法点 | 解释 | 视频例子
"""

def analyze_video(video_id: str, title: str) -> dict | None:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.5-flash")

    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        response = model.generate_content([
            {"role": "user", "parts": [
                {"file_data": {"mime_type": "video/youtube", "file_uri": url}},
                PROMPT
            ]}
        ])
        raw = response.text.strip()

    except Exception as e:
        print(f"[Gemini] 分析失败 [{video_id}]：{e}")
        return None

    # 语言检测
    if raw.startswith("NOT_ENGLISH"):
        print(f"[Gemini] 非英语视频，跳过：{title[:40]}")
        return None

    print(f"[Gemini] 分析完成：{title[:40]}")
    return _parse(raw, video_id, title)


def _parse(raw: str, video_id: str, title: str) -> dict:
    result = {
        "video_id":  video_id,
        "title":     title,
        "url":       f"https://www.youtube.com/watch?v={video_id}",
        "cards":     "",   # 墨墨格式原文，直接用于邮件和导出
        "summary":   "",
        "sentences": [],
        "grammar":   [],
    }

    # ── 提取各 section ──
    markers = ["---CARDS---", "---SUMMARY---", "---SENTENCES---", "---GRAMMAR---"]
    blocks  = {}
    for i, marker in enumerate(markers):
        start = raw.find(marker)
        if start == -1:
            continue
        start += len(marker)
        end = raw.find(markers[i + 1]) if i + 1 < len(markers) else len(raw)
        blocks[marker] = raw[start:end].strip()

    # CARDS：保留原始墨墨格式，同时做基本清洗
    raw_cards = blocks.get("---CARDS---", "")
    result["cards"] = _clean_cards(raw_cards)

    # SUMMARY
    result["summary"] = blocks.get("---SUMMARY---", "")

    # SENTENCES
    for line in blocks.get("---SENTENCES---", "").splitlines():
        line = line.strip()
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            result["sentences"].append(parts)

    # GRAMMAR
    for line in blocks.get("---GRAMMAR---", "").splitlines():
        line = line.strip()
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            result["grammar"].append(parts)

    return result


def _clean_cards(text: str) -> str:
    """参考 main.py 的 postprocess_cards + validate_cards 逻辑"""
    # 去掉 markdown 符号
    text = re.sub(r"^```[\w-]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    text = text.replace("**", "").replace("###", "")

    cleaned_lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            cleaned_lines.append("")
            continue
        # 去掉序号
        s = re.sub(r"^\d+[\.\)]\s*", "", s)
        s = re.sub(r"^[•\-\*]\s*", "", s)
        # 去掉多余标签
        s = re.sub(r"^(释义：|例句：|翻译：|词性：)\s*", "", s)
        cleaned_lines.append(s)

    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    # 确保每张卡有 ---
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    fixed = []
    for block in blocks:
        lines = [l.rstrip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        if "---" not in lines:
            if len(lines) >= 2:
                lines.insert(1, "---")
        fixed.append("\n".join(lines))

    return "\n\n".join(fixed)

import os
import re
from google import genai


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


PROMPT = """请分析这个视频，完成以下两步：

第一步：判断视频主要语言。
如果主要语言不是英语，只输出一行：NOT_ENGLISH
然后停止，不要输出任何其他内容。

第二步：如果是英语视频，从中挑选 5-8 个最有学习价值的单词或短语，优先选择：
- 地道口语短语、动词短语（phrasal verbs）
- 高频但中国学习者容易用错的词
- 视频语境中出现的习语或固定搭配
- 避免过于基础的词，如 good, make, go 等

严格按照以下格式输出：

---CARDS---
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
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {"role": "user", "parts": [
                    {"file_data": {"mime_type": "video/youtube", "file_uri": url}},
                    PROMPT,
                ]}
            ],
        )
        raw = response.text.strip()
    except Exception as e:
        print(f"[Gemini] 分析失败 [{video_id}]：{e}")
        return None

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
        "cards":     "",
        "summary":   "",
        "sentences": [],
        "grammar":   [],
    }

    markers = ["---CARDS---", "---SUMMARY---", "---SENTENCES---", "---GRAMMAR---"]
    blocks = {}
    for i, marker in enumerate(markers):
        start = raw.find(marker)
        if start == -1:
            continue
        start += len(marker)
        end = raw.find(markers[i + 1]) if i + 1 < len(markers) else len(raw)
        blocks[marker] = raw[start:end].strip()

    result["cards"]   = _clean_cards(blocks.get("---CARDS---", ""))
    result["summary"] = blocks.get("---SUMMARY---", "")

    for line in blocks.get("---SENTENCES---", "").splitlines():
        if "|" in line:
            result["sentences"].append([p.strip() for p in line.split("|")])

    for line in blocks.get("---GRAMMAR---", "").splitlines():
        if "|" in line:
            result["grammar"].append([p.strip() for p in line.split("|")])

    return result


def _clean_cards(text: str) -> str:
    text = re.sub(r"^```[\w-]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    text = text.replace("**", "").replace("###", "")

    cleaned = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            cleaned.append("")
            continue
        s = re.sub(r"^\d+[\.\)]\s*", "", s)
        s = re.sub(r"^[•\-\*]\s*", "", s)
        s = re.sub(r"^(释义：|例句：|翻译：|词性：)\s*", "", s)
        cleaned.append(s)

    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    fixed = []
    for block in blocks:
        lines = [l.rstrip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        if "---" not in lines and len(lines) >= 2:
            lines.insert(1, "---")
        fixed.append("\n".join(lines))

    return "\n\n".join(fixed)

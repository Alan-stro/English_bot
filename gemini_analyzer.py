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


def build_prompt(difficulty: str) -> str:
    return f"""请分析这个视频，完成以下步骤：

第一步：判断视频主要语言。
如果主要语言不是英语，只输出一行：NOT_ENGLISH
然后停止，不要输出任何其他内容。

第二步：评估视频整体英语难度等级（A2 / B1 / B2 / C1 / C2）。

第三步：今天的目标难度是 {difficulty}。
请从视频中挑选 5-8 个最符合 {difficulty} 水平的单词或短语，优先选择：
- 地道口语短语、动词短语（phrasal verbs）
- 高频但中国学习者容易用错的词
- 视频语境中出现的习语或固定搭配
- 避免过于基础的词，如 good, make, go 等

严格按照以下格式输出，不要添加任何额外内容：

---LEVEL---
视频难度等级，只输出一个值，如 B2

---CARDS---
英文单词或短语
---
中文核心释义
英文例句（贴合视频语境）
中文例句

（每张卡之间空一行，正面只写英文，不写词性、序号或任何说明）

---PRONUNCIATION---
每个词一行，格式：
单词或短语 | 音标 | 中文发音描述（重点说中国人容易读错的地方）

---SUMMARY---
用 3-4 句中文概括视频主要内容。

---SENTENCES---
3-5 个地道口语句型，每条一行，格式：
原句 | 中文解释

---GRAMMAR---
1-2 个语法亮点，每条一行，格式：
语法点 | 解释 | 视频例子
"""


def analyze_video(video_id: str, title: str, difficulty: str = "B2") -> dict | None:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                genai.types.Part(
                    file_data=genai.types.FileData(
                        mime_type="video/youtube",
                        file_uri=url,
                    )
                ),
                build_prompt(difficulty),
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
    return _parse(raw, video_id, title, difficulty)


def _parse(raw: str, video_id: str, title: str, difficulty: str) -> dict:
    result = {
        "video_id":      video_id,
        "title":         title,
        "url":           f"https://www.youtube.com/watch?v={video_id}",
        "target_level":  difficulty,   # 今天要求的难度
        "actual_level":  "",           # Gemini 评估视频实际难度
        "cards":         "",
        "pronunciation": [],
        "summary":       "",
        "sentences":     [],
        "grammar":       [],
    }

    markers = [
        "---LEVEL---",
        "---CARDS---",
        "---PRONUNCIATION---",
        "---SUMMARY---",
        "---SENTENCES---",
        "---GRAMMAR---",
    ]
    keys = ["level", "cards", "pronunciation", "summary", "sentences", "grammar"]

    blocks = {}
    for i, marker in enumerate(markers):
        start = raw.find(marker)
        if start == -1:
            continue
        start += len(marker)
        end = raw.find(markers[i + 1]) if i + 1 < len(markers) else len(raw)
        blocks[keys[i]] = raw[start:end].strip()

    # 实际难度
    result["actual_level"] = blocks.get("level", "").strip().upper()

    # 词汇卡片（墨墨格式）
    result["cards"] = _clean_cards(blocks.get("cards", ""))

    # 发音提示，每行按 | 切成三列
    for line in blocks.get("pronunciation", "").splitlines():
        line = line.strip()
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                result["pronunciation"].append({
                    "word":        parts[0],
                    "phonetic":    parts[1],
                    "description": parts[2],
                })

    # 摘要
    result["summary"] = blocks.get("summary", "")

    # 句型
    for line in blocks.get("sentences", "").splitlines():
        if "|" in line:
            result["sentences"].append([p.strip() for p in line.split("|")])

    # 语法
    for line in blocks.get("grammar", "").splitlines():
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
        lines = [ln.rstrip() for ln in b

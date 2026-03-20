import json
import os
from google import genai

DIFFICULTY_LEVELS = ["A2", "B1", "B2", "C1", "C2"]


def _has_chinese(text: str) -> bool:
    return any('\u4e00' <= ch <= '\u9fff' for ch in text)


def _ensure_english(topic: str) -> str:
    """如果话题包含中文，调用 Gemini 翻译成适合 YouTube 搜索的英文关键词。"""
    if not _has_chinese(topic):
        return topic

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = f"""请把下面的话题翻译成适合在 YouTube 搜索的英文关键词（2-5 个词），
不要加任何解释或标点，只输出英文关键词本身。

话题：{topic}"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        translated = response.text.strip()
        print(f"[话题] 中文话题已翻译：{topic} → {translated}")
        return translated
    except Exception as e:
        print(f"[话题] 翻译失败，保留原始话题：{e}")
        return topic


def get_topic() -> str:

    manual = os.environ.get("MANUAL_TOPIC", "").strip()
    if manual:
        print(f"[话题] 来自 Actions 参数：{manual}")
        return _ensure_english(manual)

    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        if config.get("topic", "").strip():
            topic = config["topic"].strip()
            print(f"[话题] 来自 config.json：{topic}")
            config["topic"] = ""
            with open("config.json", "w") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return _ensure_english(topic)
    except Exception as e:
        print(f"[话题] 读取 config.json 失败：{e}")

    return _gemini_pick_topic()


def get_difficulty() -> str:

    # 优先级 1：Actions 参数
    manual = os.environ.get("MANUAL_DIFFICULTY", "").strip().upper()
    if manual in DIFFICULTY_LEVELS:
        print(f"[难度] 来自 Actions 参数：{manual}")
        return manual

    # Actions 反馈
    actions_feedback = os.environ.get("MANUAL_FEEDBACK", "").strip().lower()

    try:
        with open("config.json", "r") as f:
            config = json.load(f)

        feedback = actions_feedback or config.get("feedback", "").strip().lower()
        if feedback:
            config["feedback"] = ""
            with open("config.json", "w") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f"[难度] 收到反馈：{feedback}")

        manual_diff = config.get("difficulty", "").strip().upper()
        if manual_diff in DIFFICULTY_LEVELS:
            adjusted = _adjust_by_feedback(manual_diff, feedback)
            if adjusted != manual_diff:
                config["difficulty"] = adjusted
                with open("config.json", "w") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                print(f"[难度] 根据反馈从 {manual_diff} 调整为：{adjusted}")
                return adjusted
            print(f"[难度] 来自 config.json：{manual_diff}")
            return manual_diff

    except Exception as e:
        print(f"[难度] 读取 config.json 失败：{e}")

    return _gemini_pick_difficulty()


def _adjust_by_feedback(current: str, feedback: str) -> str:
    idx = DIFFICULTY_LEVELS.index(current)
    if feedback == "too_easy" and idx < len(DIFFICULTY_LEVELS) - 1:
        return DIFFICULTY_LEVELS[idx + 1]
    if feedback == "too_hard" and idx > 0:
        return DIFFICULTY_LEVELS[idx - 1]
    return current


def _gemini_pick_difficulty() -> str:
    history = _load_history()
    recent_difficulties = history.get("difficulties", [])[-10:]
    recent_feedbacks    = history.get("feedbacks",    [])[-10:]

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    prompt = f"""你是一个英语学习难度规划师。

难度等级从低到高：A2 → B1 → B2 → C1 → C2

最近推送的难度记录：{recent_difficulties if recent_difficulties else "暂无，初始设定为 B2"}
最近的反馈记录：{recent_feedbacks if recent_feedbacks else "暂无反馈"}

请根据以下原则决定今天的难度：
- 如果连续 3 天以上 too_easy 反馈，上调一级
- 如果连续 2 天以上 too_hard 反馈，下调一级
- 没有反馈则保持近期主流难度
- 偶尔（约 10% 概率）在当前级别上下浮动一级，保持新鲜感

只输出难度等级本身，如 B2，不要任何解释。"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        difficulty = response.text.strip().upper()
        if difficulty in DIFFICULTY_LEVELS:
            print(f"[难度] Gemini 动态判断：{difficulty}")
            return difficulty
    except Exception as e:
        print(f"[难度] Gemini 判断失败：{e}")

    return "B2"


def _gemini_pick_topic() -> str:
    recent = _load_recent_topics()
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    prompt = f"""你是一个英语学习内容策划人。

请为今天生成一个 YouTube 视频搜索话题，规则如下：
- 贴近英语母语者的真实日常，适合学英语口语
- 话题可以是任何领域、任何粒度，越具体越好
- 不要和下面最近已推送过的话题重复或太相似
- 必须用英文输出，2-5 个词，适合直接用于 YouTube 搜索

最近推过的话题：
{json.dumps(recent, ensure_ascii=False, indent=2) if recent else "（暂无记录）"}

只输出英文话题本身，不要任何解释或标点。"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        topic = response.text.strip()
        print(f"[话题] Gemini 生成：{topic}")
        return topic
    except Exception as e:
        print(f"[话题] Gemini 生成失败，使用默认：{e}")
        return "daily life vlog"


def _load_recent_topics(n: int = 10) -> list:
    return _load_history().get("topics", [])[-n:]


def _load_history() -> dict:
    try:
        with open("history.json", "r") as f:
            return json.load(f)
    except Exception:
        return {"videos": [], "topics": [], "difficulties": [], "feedbacks": []}

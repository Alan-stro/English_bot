import json
import os
from google import genai


def get_topic() -> str:
    manual = os.environ.get("MANUAL_TOPIC", "").strip()
    if manual:
        print(f"[话题] 来自 Actions 参数：{manual}")
        return manual

    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        if config.get("topic", "").strip():
            topic = config["topic"].strip()
            print(f"[话题] 来自 config.json：{topic}")
            config["topic"] = ""
            with open("config.json", "w") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return topic
    except Exception as e:
        print(f"[话题] 读取 config.json 失败：{e}")

    return _gemini_pick_topic()


def _gemini_pick_topic() -> str:
    recent = _load_recent_topics()

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    prompt = f"""你是一个英语学习内容策划人。

请为今天生成一个 YouTube 视频搜索话题，规则如下：
- 贴近英语母语者的真实日常，适合学英语口语
- 话题可以是任何领域、任何粒度，越具体越好
- 不要和下面最近已推送过的话题重复或太相似

最近推过的话题：
{json.dumps(recent, ensure_ascii=False, indent=2) if recent else "（暂无记录）"}

只输出话题本身，中英文均可，不要任何解释或标点。"""

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
    try:
        with open("history.json", "r") as f:
            data = json.load(f)
        return data.get("topics", [])[-n:]
    except Exception:
        return []

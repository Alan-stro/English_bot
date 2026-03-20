import os
import re
from google import genai
from utils import is_within_duration, parse_duration_seconds

HISTORY_FILE = "history.json"
MAX_VIDEOS = 2


def load_history() -> dict:
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"videos": [], "topics": [], "difficulties": [], "feedbacks": []}


def save_history(new_video_ids: list, topic: str, difficulty: str, feedback: str):
    history = load_history()

    history["videos"].extend(new_video_ids)
    history["videos"] = history["videos"][-200:]

    history["topics"].append(topic)
    history["topics"] = history["topics"][-10:]

    history["difficulties"].append(difficulty)
    history["difficulties"] = history["difficulties"][-30:]

    if feedback:
        history.setdefault("feedbacks", []).append(feedback)
        history["feedbacks"] = history["feedbacks"][-30:]

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def main():
    print("=== 每日英语 Bot 启动 ===")

    topic      = get_topic()
    difficulty = get_difficulty()
    feedback   = os.environ.get("MANUAL_FEEDBACK", "").strip().lower()

    print(f"[主流程] 话题：{topic} | 难度：{difficulty}")

    candidates = search_videos(topic)
    if not candidates:
        print("[主流程] 没有找到候选视频，退出")
        return

    analyses = []
    for video in candidates:
        if len(analyses) >= MAX_VIDEOS:
            break
        vid   = video["id"]["videoId"]
        title = video["snippet"]["title"]
        print(f"[主流程] 正在分析 ({len(analyses)+1}/{MAX_VIDEOS})：{title[:50]}")
        result = analyze_video(vid, title, difficulty)
        if result is None:
            print("[主流程] 跳过，继续取下一个候选")
            continue
        analyses.append(result)

    if not analyses:
        print("[主流程] 所有候选视频均不可用，退出")
        return

    if len(analyses) < MAX_VIDEOS:
        print(f"[主流程] 警告：只找到 {len(analyses)} 个可用视频（目标 {MAX_VIDEOS}）")

    try:
        send_daily_email(topic, difficulty, analyses)
    except Exception as e:
        print(f"[主流程] 邮件发送失败：{e}")
        raise

    save_history(
        [a["video_id"] for a in analyses],
        topic,
        difficulty,
        feedback,
    )
    print(f"=== 完成，共推送 {len(analyses)} 个视频 ===")


if __name__ == "__main__":
    main()

import json
import os
from topic_picker import get_topic
from youtube_fetcher import search_videos
from gemini_analyzer import analyze_video
from email_sender import send_daily_email

HISTORY_FILE = "history.json"
MAX_VIDEOS = 2  # 每天推送数量


def load_history() -> dict:
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"videos": [], "topics": []}


def save_history(new_video_ids: list, topic: str):
    history = load_history()
    history["videos"].extend(new_video_ids)
    history["videos"] = history["videos"][-200:]
    history["topics"].append(topic)
    history["topics"] = history["topics"][-10:]  # 对应 topic_picker 的 n=10
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def main():
    print("=== 每日英语 Bot 启动 ===")

    # Step 1: 决定话题
    topic = get_topic()

    # Step 2: 搜索候选视频（最多返回 5 个候选）
    candidates = search_videos(topic)
    if not candidates:
        print("[主流程] 没有找到候选视频，退出")
        return

    # Step 3: 逐个分析，遇到非英语自动补位，凑满 MAX_VIDEOS 个
    analyses = []
    for video in candidates:
        if len(analyses) >= MAX_VIDEOS:
            break
        vid   = video["id"]["videoId"]
        title = video["snippet"]["title"]
        print(f"[主流程] 正在分析 ({len(analyses)+1}/{MAX_VIDEOS})：{title[:50]}")
        result = analyze_video(vid, title)
        if result is None:
            print(f"[主流程] 跳过，继续取下一个候选")
            continue
        analyses.append(result)

    if not analyses:
        print("[主流程] 所有候选视频均不可用，退出")
        return

    if len(analyses) < MAX_VIDEOS:
        print(f"[主流程] 警告：只找到 {len(analyses)} 个可用视频（目标 {MAX_VIDEOS}）")

    # Step 4: 发送邮件
    send_daily_email(topic, analyses)

    # Step 5: 更新历史
    save_history([a["video_id"] for a in analyses], topic)
    print(f"=== 完成，共推送 {len(analyses)} 个视频 ===")


if __name__ == "__main__":
    main()

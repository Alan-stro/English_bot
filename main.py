import json
import os
import time
from topic_picker import get_topic, get_difficulty
from youtube_fetcher import search_videos, search_videos_from_channel
from gemini_analyzer import analyze_video
from email_sender import send_daily_email

HISTORY_FILE = "history.json"
MAX_VIDEOS = 2


def load_history() -> dict:
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"videos": [], "topics": [], "difficulties": [], "feedbacks": []}


def save_history(new_video_ids: list, topic: str, difficulty: str, feedback: str, last_channel_id: str | None = None):
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

    if last_channel_id:
        history["last_channel_id"] = last_channel_id

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def main():
    print("=== 每日英语 Bot 启动 ===")

    topic      = get_topic()
    difficulty = get_difficulty()
    feedback   = os.environ.get("MANUAL_FEEDBACK", "").strip().lower()

    print(f"[主流程] 话题：{topic} | 难度：{difficulty}")

    # ── 白名单频道：最多贡献 1 个视频 ──────────────────────────────
    channel_video   = None
    used_channel_id = None

    channel_candidates, used_channel_id = search_videos_from_channel(topic)
    for video in channel_candidates:
        vid   = video["id"]["videoId"]
        title = video["snippet"]["title"]
        print(f"[主流程] 分析白名单视频：{title[:50]}")
        result = analyze_video(vid, title, difficulty, check_difficulty_mismatch=True)
        if result is None:
            continue
        if result.get("difficulty_mismatch"):
            print(f"[主流程] 白名单视频难度不匹配，跳过：{title[:40]}")
            continue
        channel_video = result
        break  # 找到一个合格的就停止

    if channel_video:
        print(f"[主流程] 白名单视频已选定：{channel_video['title'][:40]}")
    else:
        print("[主流程] 白名单未找到合适视频，将全部由全网补充")
        used_channel_id = None  # 未成功使用，不记录

    # ── 全网搜索：补足至 MAX_VIDEOS ──────────────────────────────────
    global_needed = MAX_VIDEOS - (1 if channel_video else 0)
    print(f"[主流程] 全网需要补充 {global_needed} 个视频")

    global_candidates = search_videos(topic)
    global_analyses = []
    for video in global_candidates:
        if len(global_analyses) >= global_needed:
            break

        if global_analyses or channel_video:
            print("[主流程] 等待 60 秒，避免触发 API 速率限制...")
            time.sleep(60)

        vid   = video["id"]["videoId"]
        title = video["snippet"]["title"]
        print(f"[主流程] 正在分析全网视频 ({len(global_analyses)+1}/{global_needed})：{title[:50]}")
        result = analyze_video(vid, title, difficulty)
        if result is None:
            print("[主流程] 跳过，继续取下一个候选")
            continue
        global_analyses.append(result)

    # ── 合并结果 ─────────────────────────────────────────────────────
    analyses = ([channel_video] if channel_video else []) + global_analyses

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
        last_channel_id=used_channel_id,
    )
    print(f"=== 完成，共推送 {len(analyses)} 个视频 ===")


if __name__ == "__main__":
    main()

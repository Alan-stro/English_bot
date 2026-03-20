import os
import json
import math
import random
import requests
from utils import is_within_duration

PREFERRED_REGIONS = {"en", "en-US", "en-GB", "en-AU", "en-CA"}
CHANNELS_FILE = "channels.json"


def _load_channels() -> dict:
    try:
        with open(CHANNELS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"enabled": False, "fallback_to_search": True, "channels": []}


def search_videos_from_channel(topic: str) -> tuple[list, str | None]:
    """
    从频道白名单中随机挑一个频道搜索视频。
    返回 (候选列表, 使用的 channel_id)。
    如果白名单未启用或搜索失败，返回 ([], None)。
    """
    config = _load_channels()
    if not config.get("enabled", False):
        return [], None

    channels = config.get("channels", [])
    if not channels:
        return [], None

    history = _load_history()
    seen_ids = set(history.get("videos", []))
    last_channel_id = history.get("last_channel_id")

    # 避免连续两天使用同一频道
    available = [c for c in channels if c["channel_id"] != last_channel_id]
    if not available:
        available = channels  # 只有一个频道时退回全部

    chosen = random.choice(available)
    print(f"[频道白名单] 使用频道：{chosen['name']}")

    candidates = _search_in_channel(topic, chosen["channel_id"], seen_ids)
    if not candidates:
        print(f"[频道白名单] 频道内无结果，返回空")
        return [], chosen["channel_id"]

    enriched = _enrich(candidates)
    filtered = _filter_and_rank(enriched)
    print(f"[频道白名单] 最终候选 {len(filtered)} 个")
    return filtered[:5], chosen["channel_id"]


def _search_in_channel(topic: str, channel_id: str, seen_ids: set) -> list:
    params = {
        "part": "snippet",
        "q": topic,
        "channelId": channel_id,
        "type": "video",
        "videoDuration": "medium",
        "videoCaption": "closedCaption",
        "relevanceLanguage": "en",
        "maxResults": 10,
        "key": os.environ["YOUTUBE_API_KEY"],
    }
    try:
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except Exception as e:
        print(f"[频道白名单] 搜索失败：{e}")
        return []

    fresh = [v for v in items if v["id"]["videoId"] not in seen_ids]
    print(f"[频道白名单] 搜到 {len(items)} 个，去重后 {len(fresh)} 个")
    return fresh


def _load_history() -> dict:
    try:
        with open("history.json", "r") as f:
            return json.load(f)
    except Exception:
        return {"videos": [], "topics": [], "difficulties": [], "feedbacks": []}


def search_videos(topic: str) -> list:
    history = _load_history()
    seen_ids = set(history.get("videos", []))

    candidates = _search(topic, seen_ids)
    if not candidates:
        return []

    enriched = _enrich(candidates)
    filtered = _filter_and_rank(enriched)
    print(f"[YouTube] 最终候选 {len(filtered)} 个")
    return filtered[:5]


def _search(topic: str, seen_ids: set) -> list:
    params = {
        "part": "snippet",
        "q": topic,
        "type": "video",
        "videoDuration": "medium",
        "videoCaption": "closedCaption",
        "relevanceLanguage": "en",
        "maxResults": 10,
        "key": os.environ["YOUTUBE_API_KEY"],
    }
    try:
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except Exception as e:
        print(f"[YouTube] 搜索失败：{e}")
        return []

    fresh = [v for v in items if v["id"]["videoId"] not in seen_ids]
    print(f"[YouTube] 搜到 {len(items)} 个，去重后 {len(fresh)} 个")
    return fresh


def _enrich(candidates: list) -> list:
    ids = ",".join(v["id"]["videoId"] for v in candidates)
    try:
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "statistics,contentDetails,snippet",
                "id": ids,
                "key": os.environ["YOUTUBE_API_KEY"],
            },
            timeout=15,
        )
        resp.raise_for_status()
        stats_map = {item["id"]: item for item in resp.json().get("items", [])}
    except Exception as e:
        print(f"[YouTube] 拉取统计数据失败：{e}")
        return candidates

    enriched = []
    for v in candidates:
        vid = v["id"]["videoId"]
        detail = stats_map.get(vid, {})
        stats = detail.get("statistics", {})
        v["_stats"] = {
            "views":     int(stats.get("viewCount",     0)),
            "likes":     int(stats.get("likeCount",     0)),
            "favorites": int(stats.get("favoriteCount", 0)),
            "comments":  int(stats.get("commentCount",  0)),
        }
        v["_duration"] = detail.get("contentDetails", {}).get("duration", "")
        v["_region"]   = detail.get("snippet", {}).get("defaultAudioLanguage", "")
        enriched.append(v)
    return enriched


def _filter_and_rank(videos: list) -> list:
    scored = []
    for v in videos:
        duration = v.get("_duration", "")
        if duration and not is_within_duration(duration, max_minutes=20):
            print(f"[过滤] 超时：{v['snippet']['title'][:40]}")
            continue

        region = v.get("_region", "")
        if region and region not in PREFERRED_REGIONS:
            print(f"[过滤] 非英美口音：{v['snippet']['title'][:40]}")
            continue

        stats = v.get("_stats", {})
        score = (
            math.log1p(stats.get("views",     0)) * 1.0 +
            math.log1p(stats.get("likes",     0)) * 1.5 +
            math.log1p(stats.get("favorites", 0)) * 1.2 +
            math.log1p(stats.get("comments",  0)) * 1.0
        )
        v["_score"] = score
        scored.append(v)

    scored.sort(key=lambda x: x["_score"], reverse=True)
    return scored

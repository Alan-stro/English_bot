import os
import json
import math
import requests

PREFERRED_REGIONS = {"en", "en-US", "en-GB", "en-AU", "en-CA"}


def _load_history() -> dict:
    try:
        with open("history.json", "r") as f:
            return json.load(f)
    except Exception:
        return {"videos": [], "topics": []}


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
            "views":    int(stats.get("viewCount",    0)),
            "likes":    int(stats.get("likeCount",    0)),
            "favorites":int(stats.get("favoriteCount",0)),
            "comments": int(stats.get("commentCount", 0)),
        }
        v["_duration"] = detail.get("contentDetails", {}).get("duration", "")
        v["_region"]   = detail.get("snippet", {}).get("defaultAudioLanguage", "")
        enriched.append(v)
    return enriched


def _filter_and_rank(videos: list) -> list:
    from gemini_analyzer import is_within_duration
    scored = []
    for v in videos:
        # 时长过滤：20 分钟以内
        duration = v.get("_duration", "")
        if duration and not is_within_duration(duration, max_minutes=20):
            print(f"[过滤] 超时：{v['snippet']['title'][:40]}")
            continue

        # 口音过滤
        region = v.get("_region", "")
        if region and region not in PREFERRED_REGIONS:
            print(f"[过滤] 非英美口音：{v['snippet']['title'][:40]}")
            continue

        stats = v.get("_stats", {})
        score = (
            math.log1p(stats.get("views",    0)) * 1.0 +
            math.log1p(stats.get("likes",    0)) * 1.5 +
            math.log1p(stats.get("favorites",0)) * 1.2 +
            math.log1p(stats.get("comments", 0)) * 1.0
        )
        v["_score"] = score
        scored.append(v)

    scored.sort(key=lambda x: x["_score"], reverse=True)
    return scored

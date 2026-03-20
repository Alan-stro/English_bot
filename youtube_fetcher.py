import os
import json
import requests
from datetime import datetime, timedelta

def search_videos(topic: str) -> list:

    history = _load_history()
    seen_ids = set(history.get("videos", []))

    # 第一步：搜索候选视频（只返回元数据）
    candidates = _search(topic, seen_ids)
    if not candidates:
        return []

    # 第二步：批量拉取播放量 / 点赞量 / 收藏量等数据
    enriched = _enrich(candidates)

    # 第三步：口音过滤 + 综合评分排序，取前 2
    filtered = _filter_and_rank(enriched)
    print(f"[YouTube] 最终选出 {len(filtered)} 个视频")
    return filtered[:5]  # 多返回候选，供 main.py 补位用


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
    """批量查询播放量、点赞量、收藏量，10个视频只消耗1次配额"""
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
        stats_map = {
            item["id"]: item
            for item in resp.json().get("items", [])
        }
    except Exception as e:
        print(f"[YouTube] 拉取统计数据失败：{e}")
        return candidates  # 失败就用原始候选，不中断流程

    enriched = []
    for v in candidates:
        vid = v["id"]["videoId"]
        detail = stats_map.get(vid, {})
        stats = detail.get("statistics", {})
        v["_stats"] = {
            "views":     int(stats.get("viewCount",    0)),
            "likes":     int(stats.get("likeCount",    0)),
            "favorites": int(stats.get("favoriteCount",0)),
            "comments":  int(stats.get("commentCount", 0)),
        }
        # 视频时长，格式如 PT8M43S
        v["_duration"] = detail.get("contentDetails", {}).get("duration", "")
        # 频道所在地区
        v["_region"] = detail.get("snippet", {}).get("defaultAudioLanguage", "")
        enriched.append(v)

    return enriched


# 偏好的口音地区 / 语言标签白名单
PREFERRED_REGIONS = {"en", "en-US", "en-GB", "en-AU", "en-CA"}

def _filter_and_rank(videos: list) -> list:
    scored = []
    for v in videos:
        stats = v.get("_stats", {})
        region = v.get("_region", "")

        # 口音过滤：有地区标签且不在白名单的直接跳过
        # 没有标签的保留（大部分英语视频不设标签）
        if region and region not in PREFERRED_REGIONS:
            print(f"[过滤] 跳过非英美口音视频：{v['snippet']['title'][:40]}")
            continue

        views     = stats.get("views",    0)
        likes     = stats.get("likes",    0)
        favorites = stats.get("favorites",0)
        comments  = stats.get("comments", 0)

        # 综合评分：播放量权重最高，点赞和评论次之
        # 用对数压缩防止百万播放量的视频把其他都淹没
        import math
        score = (
            math.log1p(views)     * 1.0 +
            math.log1p(likes)     * 1.5 +
            math.log1p(favorites) * 1.2 +
            math.log1p(comments)  * 1.0
        )
        v["_score"] = score
        scored.append(v)

    scored.sort(key=lambda x: x["_score"], reverse=True)
    return scored

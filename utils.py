import re


def parse_duration_seconds(iso: str) -> int:
    """把 PT8M43S 解析成秒数"""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not match:
        return 0
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    return h * 3600 + m * 60 + s


def is_within_duration(iso: str, max_minutes: int = 20) -> bool:
    return parse_duration_seconds(iso) <= max_minutes * 60

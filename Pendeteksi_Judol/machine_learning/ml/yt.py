import os, re
from urllib.parse import urlparse, parse_qs
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def extract_video_id(link: str) -> str:
    u = urlparse(link)
    if u.netloc in ("youtu.be", "www.youtu.be"):
        return u.path.lstrip("/")
    qs = parse_qs(u.query)
    return qs.get("v", [""])[0]

def fetch_all_comment_threads(video_id: str, max_total: int = 200):
    items, page_token = [], None
    try:
        while True:
            resp = youtube.commentThreads().list(
                part="id,snippet,replies",
                videoId=video_id,
                maxResults=100,
                pageToken=page_token,
                order="time",
                textFormat="plainText",
            ).execute()
            batch = resp.get("items", [])
            items.extend(batch)
            if len(items) >= max_total:  
                break
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
    except HttpError as e:
        if e.resp.status in (403, 404):
            return []
        raise
    return items

def fetch_all_replies(parent_id: str):
    replies, page_token = [], None
    while True:
        resp = youtube.comments().list(
            part="id,snippet",
            parentId=parent_id,
            maxResults=100,
            pageToken=page_token,
            textFormat="plainText",
        ).execute()
        replies.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return replies

def collect_comments(link: str, limit: int = 100):
    """Return: list[dict]"""
    vid = extract_video_id(link)
    threads = fetch_all_comment_threads(vid, max_total=limit)

    rows = []
    for th in threads:
        top = th["snippet"]["topLevelComment"]["snippet"]
        rows.append({
            "level": "top",
            "comment_id": th["snippet"]["topLevelComment"]["id"],
            "parent_id": None,
            "author": top.get("authorDisplayName"),
            "published_at": top.get("publishedAt"),
            "updated_at": top.get("updatedAt"),
            "text": top.get("textDisplay") or "",   
        })

        total_replies = th["snippet"].get("totalReplyCount", 0)
        if total_replies:
            parent_id = th["snippet"]["topLevelComment"]["id"]
            partial = (th.get("replies", {}) or {}).get("comments", [])
            have = {r["id"] for r in partial}
            for r in partial:
                rs = r["snippet"]
                rows.append({
                    "level": "reply",
                    "comment_id": r["id"],
                    "parent_id": parent_id,
                    "author": rs.get("authorDisplayName"),
                    "published_at": rs.get("publishedAt"),
                    "updated_at": rs.get("updatedAt"),
                    "text": rs.get("textDisplay") or "",
                })
            if len(have) < total_replies:
                for r in fetch_all_replies(parent_id):
                    if r["id"] in have: 
                        continue
                    rs = r["snippet"]
                    rows.append({
                        "level": "reply",
                        "comment_id": r["id"],
                        "parent_id": parent_id,
                        "author": rs.get("authorDisplayName"),
                        "published_at": rs.get("publishedAt"),
                        "updated_at": rs.get("updatedAt"),
                        "text": rs.get("textDisplay") or "",
                    })

    # jika melebihi limit
    if len(rows) > limit:
        rows = rows[:limit]
    return rows

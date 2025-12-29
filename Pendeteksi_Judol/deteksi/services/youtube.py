import os
from urllib.parse import urlparse, parse_qs
import requests
from django.conf import settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# Fungsi youtube API key dari variabel lingkungan
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def extract_video_id(link: str) -> str:
    u = urlparse(link)
    if u.netloc in ("youtu.be", "www.youtu.be"):
        return u.path.lstrip("/")
    qs = parse_qs(u.query)
    return qs.get("v", [""])[0]


def extract_youtube_video_id(url: str) -> str | None:
    """
    Mengekstrak video ID dari berbagai format URL YouTube.
    Mengembalikan None jika URL tidak valid atau ID tidak ditemukan.
    """
    try:
        # Pastikan URL adalah string
        if not isinstance(url, str) or not url:
            return None

        u = urlparse(url)
        
        # Cek domain youtu.be
        if u.netloc in ("youtu.be", "www.youtu.be"):
            # ID ada di path, contoh: /cBVGlBWQzuc
            return u.path.lstrip("/")

        # Cek domain youtube.com
        if u.netloc in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            # Cek format URL /shorts/
            if "/shorts/" in u.path:
                return u.path.split("/shorts/")[1].split("?")[0]
            
            # Cek format URL /watch
            if u.path == "/watch":
                qs = parse_qs(u.query)
                # qs.get("v") mengembalikan list, jadi ambil elemen pertama
                video_id = qs.get("v", [None])[0]
                return video_id

            # Cek format URL /embed/
            if "/embed/" in u.path:
                return u.path.split("/embed/")[1].split("?")[0]

        # Jika tidak ada yang cocok, kembalikan None
        return None

    except Exception:
        # Tangani error parsing yang tidak terduga
        return None
    
    
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
    vid = extract_youtube_video_id(link)
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

    if len(rows) > limit:
        rows = rows[:limit]
    return rows


# --- OAuth & Moderation Helpers ---

def get_youtube_client_from_session(yt_creds):
    """
    Membuat instance YouTube client (OAuth) dari dictionary credentials session.
    """
    if not yt_creds:
        return None
        
    creds = Credentials(
        token=yt_creds["token"],
        refresh_token=yt_creds.get("refresh_token"),
        token_uri=yt_creds["token_uri"],
        client_id=yt_creds["client_id"],
        client_secret=yt_creds["client_secret"],
        scopes=yt_creds["scopes"],
    )
    return build("youtube", "v3", credentials=creds)


def create_oauth_flow(redirect_uri, state=None):
    """
    Membuat OAuth flow logic.
    """
    return Flow.from_client_secrets_file(
        os.path.join(settings.BASE_DIR, "client_secret.json"),
        scopes=SCOPES,
        redirect_uri=redirect_uri,
        state=state,
    )


def fetch_youtube_user_info_oauth(creds):
    """
    Mengambil informasi channel user (nama, avatar) menggunakan OAuth credentials.
    """
    user_info = {
        "name": "YouTube User",
        "avatar": "",
    }
    try:
        # Gunakan creds langsung
        # Note: build() bisa dipanggil berulang, tidak masalah.
        yt_service = build("youtube", "v3", credentials=creds)
        channel_response = yt_service.channels().list(
            part="snippet",
            mine=True
        ).execute()
        
        if channel_response.get("items"):
            channel = channel_response["items"][0]["snippet"]
            user_info = {
                "name": channel.get("title", "YouTube User"),
                "avatar": channel.get("thumbnails", {}).get("default", {}).get("url", ""),
            }
    except Exception as e:
        print(f"Error fetching YouTube user info: {e}")
        
    return user_info


def revoke_youtube_token(token):
    """
    Mengirim request revoke token ke Google.
    """
    if not token:
        return
    revoke_url = 'https://oauth2.googleapis.com/revoke'
    try:
        response = requests.post(revoke_url, params={'token': token})
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        print(f"Error revoking token: {e}")


def perform_moderation_action(service, comment_ids, action):
    """
    Melakukan aksi moderasi (delete atau reject/banAuthor=False).
    Mengembalikan tuple (ok: bool, msg: str, error_type: str|None).
    """
    if action == "delete":
        for cid in comment_ids:
            service.comments().delete(id=cid).execute()
        return True, f"Berhasil menghapus {len(comment_ids)} komentar", None
    
    elif action == "reject":
        service.comments().setModerationStatus(
            id=",".join(comment_ids),
            moderationStatus="rejected",
            banAuthor=False
        ).execute()
        return True, f"Berhasil menghapus {len(comment_ids)} komentar", None
        
    else:
        return False, "Aksi tidak dikenal", "invalid_action"


import os
from urllib.parse import urlparse, parse_qs
import requests
from django.conf import settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ===== KONFIGURASI UTAMA =====
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
# ===== END KONFIGURASI UTAMA =====

# ===== FUNGSI EKSTRAKSI VIDEO ID =====
def extract_youtube_video_id(url: str) -> str | None:
    """
    Mengekstrak video ID dari berbagai format URL YouTube.
    Mengembalikan None jika URL tidak valid atau ID tidak ditemukan.
    """
    try:
        if not isinstance(url, str) or not url:
            return None

        u = urlparse(url)
        
        # Cek domain youtu.be
        if u.netloc in ("youtu.be", "www.youtu.be"):
            return u.path.lstrip("/")

        # Cek domain youtube.com
        if u.netloc in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            # Cek format URL /shorts/
            if "/shorts/" in u.path:
                return u.path.split("/shorts/")[1].split("?")[0]

            # Cek format URL /live/
            if "/live/" in u.path:
                return u.path.split("/live/")[1].split("?")[0]
            
            # Cek format URL /watch
            if u.path == "/watch":
                qs = parse_qs(u.query)
                video_id = qs.get("v", [None])[0]
                return video_id

            # Cek format URL /embed/
            if "/embed/" in u.path:
                return u.path.split("/embed/")[1].split("?")[0]

        return None

    except Exception:
        return None
# ===== END FUNGSI EKSTRAKSI VIDEO ID =====

# ===== FUNGSI PENGAMBILAN KOMENTAR =====
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
# ===== END FUNGSI PENGAMBILAN KOMENTAR =====

# ===== FUNGSI EKSTRAKSI CHANNEL =====
def extract_channel_info(input_str: str):
    """
    Mengembalikan tuple (tipe, value).
    tipe: 'video', 'channel_id', 'handle', atau None
    """
    input_str = input_str.strip()
    
    # Cek jika input adalah Handle (contoh: @WindahBasudara)
    if input_str.startswith("@"):
        return "handle", input_str
        
    u = urlparse(input_str)
    
    # Cek URL Video biasa
    if "watch" in u.path or "/shorts/" in u.path or "/live/" in u.path:
        return "video", extract_youtube_video_id(input_str)
    if "youtu.be" in u.netloc:
        return "video", extract_youtube_video_id(input_str)
        
    # Cek URL Channel / Handle
    path_parts = u.path.strip("/").split("/")
    
    if len(path_parts) >= 1:
        if path_parts[0].startswith("@"):
            return "handle", path_parts[0] # @username
        if path_parts[0] == "channel" and len(path_parts) > 1:
            return "channel_id", path_parts[1] 
        if path_parts[0] == "c" and len(path_parts) > 1:
            return "handle", path_parts[1] 

    return None, None
# ===== END FUNGSI EKSTRAKSI CHANNEL =====

# ===== FUNGSI PLAYLIST & CHANNEL INFO =====
def get_channel_uploads_playlist(identifier, id_type):
    """
    Mendapatkan ID Playlist 'Uploads' dari channel.
    Cost: 1 Unit.
    """
    try:
        if id_type == "handle":
            resp = youtube.channels().list(
                part="contentDetails",
                forHandle=identifier
            ).execute()
        elif id_type == "channel_id":
            resp = youtube.channels().list(
                part="contentDetails",
                id=identifier
            ).execute()
        else:
            return None

        if not resp.get("items"):
            return None
            
        # Ambil ID playlist uploads
        return resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    except HttpError as e:
        print(f"Error fetching channel: {e}")
        return None

def get_videos_from_playlist(playlist_id, limit=5):
    """
    Mengambil daftar video ID dari playlist.
    Cost: 1 Unit.
    """
    video_ids = []
    try:
        resp = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=limit
        ).execute()
        
        for item in resp.get("items", []):
            vid = item["contentDetails"]["videoId"]
            video_ids.append(vid)
            
    except HttpError as e:
        print(f"Error fetching playlist items: {e}")
        
    return video_ids

def get_my_latest_videos(yt_creds, limit=6):
    """
    Mengambil video terakhir dari channel user yang sedang login.
    """
    service = get_youtube_client_from_session(yt_creds)
    if not service:
        return []

    try:
        # 1. Get Channel ID (Mine)
        channels_response = service.channels().list(
            mine=True,
            part="contentDetails"
        ).execute()

        if not channels_response.get("items"):
            return []

        uploads_playlist_id = channels_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # 2. Get Playlist Items (Videos)
        playlist_items_response = service.playlistItems().list(
            playlistId=uploads_playlist_id,
            part="snippet",
            maxResults=limit
        ).execute()

        videos = []
        for item in playlist_items_response.get("items", []):
            snippet = item["snippet"]
            videos.append({
                "id": snippet["resourceId"]["videoId"],
                "title": snippet["title"],
                "thumbnail": snippet["thumbnails"].get("medium", snippet["thumbnails"].get("default"))["url"],
                "published_at": snippet["publishedAt"]
            })
        
        return videos

    except Exception as e:
        print(f"Error fetching my videos: {e}")
        return []
# ===== END FUNGSI PLAYLIST & CHANNEL INFO =====

# ===== FUNGSI OAUTH & MODERASI =====
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
    Membuat OAuth flow logic menggunakan Environment Variables.
    """
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    project_id = os.getenv("GOOGLE_PROJECT_ID")
    auth_uri = os.getenv("GOOGLE_OAUTH_URI")
    token_uri = os.getenv("GOOGLE_TOKEN_URI")
    auth_provider_x509_cert_url = os.getenv("GOOGLE_AUTH_PROVIDER_X509_CERT_URL")
    redirect_uris = os.getenv("GOOGLE_OAUTH_REDIRECT_URIS", "").split(",")
    
    if not client_id or not client_secret:
        raise ValueError("GOOGLE_OAUTH_CLIENT_ID dan GOOGLE_OAUTH_CLIENT_SECRET harus diset di environment variables.")

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "project_id": project_id,
            "auth_uri": auth_uri,
            "token_uri": token_uri,
            "auth_provider_x509_cert_url": auth_provider_x509_cert_url,
            "redirect_uris": redirect_uris,
        }
    }
    
    return Flow.from_client_config(
        client_config,
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


def perform_moderation_action(service, comment_ids, action, block_user):
    """
    Melakukan aksi moderasi (delete atau reject/banAuthor.
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
            banAuthor=block_user
        ).execute()
        return True, f"Berhasil menghapus {len(comment_ids)} komentar", None
        
    else:
        return False, "Aksi tidak dikenal", "invalid_action"
# ===== END FUNGSI OAUTH & MODERASI =====

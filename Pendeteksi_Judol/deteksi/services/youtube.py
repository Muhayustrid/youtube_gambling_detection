import os
from urllib.parse import urlparse, parse_qs
import requests
from django.conf import settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def extract_youtube_video_id(url: str) -> str | None:
    """
    Mengekstrak ID video dari berbagai format URL YouTube.
    
    Args:
        url (str): String URL YouTube (lengkap atau pendek).
        
    Returns:
        str | None: ID Video jika ditemukan, None jika tidak valid.
    """
    try:
        if not isinstance(url, str) or not url:
            return None

        u = urlparse(url)
        
        if u.netloc in ("youtu.be", "www.youtu.be"):
            return u.path.lstrip("/")

        if u.netloc in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            if "/shorts/" in u.path:
                return u.path.split("/shorts/")[1].split("?")[0]

            if "/live/" in u.path:
                return u.path.split("/live/")[1].split("?")[0]
            
            if u.path == "/watch":
                qs = parse_qs(u.query)
                video_id = qs.get("v", [None])[0]
                return video_id

            if "/embed/" in u.path:
                return u.path.split("/embed/")[1].split("?")[0]

        return None

    except Exception:
        return None

def fetch_all_comment_threads(video_id: str, max_total: int = 200):
    """
    Mengambil thread komentar teratas dari sebuah video.
    
    Args:
        video_id (str): ID video YouTube.
        max_total (int): Batas maksimum jumlah komentar yang diambil.
        
    Returns:
        list: Daftar item thread komentar dari API YouTube.
    """
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
            if max_total != 0 and len(items) >= max_total:  
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
    """
    Mengambil semua balasan untuk komentar tertentu.
    
    Args:
        parent_id (str): ID komentar induk.
        
    Returns:
        list: Daftar item balasan komentar.
    """
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
    """
    Mengumpulkan komentar (termasuk balasan) dari sebuah video hingga batas tertentu.
    
    Args:
        link (str): URL video YouTube.
        limit (int): Batas maksimum total komentar.
        
    Returns:
        list[dict]: Daftar dictionary berisi data komentar yang telah dinormalisasi.
    """
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

def extract_channel_info(input_str: str):
    """
    Mendeteksi apakah input string adalah URL video, ID Channel, atau Handle.
    
    Args:
        input_str (str): String input dari pengguna.
        
    Returns:
        tuple: (tipe, value). Tipe bisa 'video', 'channel_id', 'handle', atau None.
    """
    input_str = input_str.strip()
    
    if input_str.startswith("@"):
        return "handle", input_str
        
    u = urlparse(input_str)
    
    if "watch" in u.path or "/shorts/" in u.path or "/live/" in u.path:
        return "video", extract_youtube_video_id(input_str)
    if "youtu.be" in u.netloc:
        return "video", extract_youtube_video_id(input_str)
        
    path_parts = u.path.strip("/").split("/")
    
    if len(path_parts) >= 1:
        if path_parts[0].startswith("@"):
            return "handle", path_parts[0] 
        if path_parts[0] == "channel" and len(path_parts) > 1:
            return "channel_id", path_parts[1] 
        if path_parts[0] == "c" and len(path_parts) > 1:
            return "handle", path_parts[1] 

    return None, None

def get_channel_uploads_playlist(identifier, id_type):
    """
    Mendapatkan ID playlist 'Uploads' dari sebuah channel untuk mengambil video-videonya.
    Membutuhkan 1 Unit Biaya Kuota API.
    
    Args:
        identifier (str): ID Channel atau Handle.
        id_type (str): Tipe identifier ('handle' atau 'channel_id').
        
    Returns:
        str | None: ID Playlist Uploads jika ditemukan.
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
            
        return resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    except HttpError as e:
        print(f"Error fetching channel: {e}")
        return None

def get_videos_from_playlist(playlist_id, limit=5):
    """
    Mengambil daftar ID video dari playlist tertentu.
    Membutuhkan 1 Unit Biaya Kuota API.
    
    Args:
        playlist_id (str): ID Playlist.
        limit (int): Jumlah maksimum video yang diambil.
        
    Returns:
        list: Daftar Video ID.
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
    Mengambil daftar video terbaru dari channel pengguna yang sedang login.
    
    Args:
        yt_creds (dict): Kredensial sesi pengguna.
        limit (int): Jumlah video yang diambil.
        
    Returns:
        list[dict]: Daftar video dengan detail id, judul, thumbnail, dan tanggal.
    """
    service = get_youtube_client_from_session(yt_creds)
    if not service:
        return []

    try:
        channels_response = service.channels().list(
            mine=True,
            part="contentDetails"
        ).execute()

        if not channels_response.get("items"):
            return []

        uploads_playlist_id = channels_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

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


def get_channel_info(identifier, id_type):
    """
    Mengambil informasi dasar channel seperti nama, avatar, dan statistik.
    Membutuhkan 1 Unit Biaya Kuota API.
    
    Args:
        identifier (str): ID Channel atau Handle.
        id_type (str): Tipe identifier.
        
    Returns:
        dict | None: Informasi channel atau None jika gagal.
    """
    try:
        if id_type == "handle":
            resp = youtube.channels().list(
                part="snippet",
                forHandle=identifier
            ).execute()
        elif id_type == "channel_id":
            resp = youtube.channels().list(
                part="snippet",
                id=identifier
            ).execute()
        else:
            return None

        if not resp.get("items"):
            return None
        
        item = resp["items"][0]
        snippet = item["snippet"]
        
        return {
            "channel_id": item["id"],
            "name": snippet.get("title", "Unknown Channel"),
            "avatar": snippet.get("thumbnails", {}).get("medium", snippet.get("thumbnails", {}).get("default", {})).get("url", ""),
            "custom_url": snippet.get("customUrl", ""),
            "description": snippet.get("description", "")[:200],  
        }
    except HttpError as e:
        print(f"Error fetching channel info: {e}")
        return None


def get_video_info(video_id):
    """
    Mengambil informasi detail tentang sebuah video.
    Membutuhkan 1 Unit Biaya Kuota API.
    
    Args:
        video_id (str): ID Video.
        
    Returns:
        dict | None: Informasi video atau None jika gagal.
    """
    try:
        resp = youtube.videos().list(
            part="snippet",
            id=video_id
        ).execute()

        if not resp.get("items"):
            return None
        
        snippet = resp["items"][0]["snippet"]
        
        return {
            "video_id": video_id,
            "title": snippet.get("title", "Unknown Video"),
            "thumbnail": snippet.get("thumbnails", {}).get("medium", snippet.get("thumbnails", {}).get("default", {})).get("url", ""),
            "channel_name": snippet.get("channelTitle", "Unknown Channel"),
            "channel_id": snippet.get("channelId", ""),
            "published_at": snippet.get("publishedAt", ""),
        }
    except HttpError as e:
        print(f"Error fetching video info: {e}")
        return None

def get_youtube_client_from_session(yt_creds):
    """
    Membuat klien API YouTube yang terautentikasi dari kredensial sesi.
    
    Args:
        yt_creds (dict): Dictionary berisi token dan info kredensial.
        
    Returns:
        Resource: Objek layanan Google API Client untuk YouTube.
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
    Membuat objek OAuth Flow untuk proses autentikasi.
    Menggunakan konfigurasi dari variabel lingkungan.
    
    Args:
        redirect_uri (str): URL redirect setelah login sukses.
        state (str): State token untuk keamanan CSRF.
        
    Returns:
        Flow: Objek OAuth flow.
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
    Mengambil profil pengguna YouTube (channel sendiri) menggunakan token OAuth.
    
    Args:
        creds (Credentials): Objek kredensial Google Auth.
        
    Returns:
        dict: Informasi profil pengguna (nama, avatar, subs, views, video).
    """
    user_info = {
        "name": "YouTube User",
        "avatar": "",
        "handle": "",
        "subscribers": "0",
        "videos": "0",
        "views": "0"
    }
    try:
        yt_service = build("youtube", "v3", credentials=creds)
        channel_response = yt_service.channels().list(
            part="snippet,statistics",
            mine=True
        ).execute()
        
        if channel_response.get("items"):
            item = channel_response["items"][0]
            snippet = item["snippet"]
            stats = item["statistics"]
            
            user_info = {
                "name": snippet.get("title", "YouTube User"),
                "avatar": snippet.get("thumbnails", {}).get("medium", snippet.get("thumbnails", {}).get("default", {})).get("url", ""),
                "handle": snippet.get("customUrl", ""),
                "subscribers": "{:,}".format(int(stats.get("subscriberCount", 0))),
                "videos": "{:,}".format(int(stats.get("videoCount", 0))),
                "views": "{:,}".format(int(stats.get("viewCount", 0)))
            }
    except Exception as e:
        print(f"Error fetching YouTube user info: {e}")
        
    return user_info


def revoke_youtube_token(token):
    """
    Mencabut akses token (Logout) dari sisi server Google.
    
    Args:
        token (str): Token akses atau refresh token yang akan dicabut.
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
    Mengeksekusi aksi moderasi massal pada komentar.
    
    Args:
        service (Resource): Layanan YouTube API terautentikasi.
        comment_ids (list): Daftar ID komentar.
        action (str): Aksi yang dilakukan ('delete' atau 'reject').
        block_user (bool): Apakah penulis komentar juga akan di-ban.
        
    Returns:
        tuple: (sukses: bool, pesan: str, tipe_error: str|None)
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

def get_my_videos_paginated(yt_creds, limit=6, page_token=None):
    """
    Mengambil video milik pengguna dengan dukungan halaman (pagination).
    
    Args:
        yt_creds (dict): Kredensial sesi.
        limit (int): Jumlah item per halaman.
        page_token (str): Token halaman berikutnya (jika ada).
        
    Returns:
        dict: {'items': list, 'next_page_token': str|None}
    """
    service = get_youtube_client_from_session(yt_creds)
    if not service:
        return {"items": [], "next_page_token": None}

    try:
        channels_response = service.channels().list(
            mine=True,
            part="contentDetails"
        ).execute()

        if not channels_response.get("items"):
            return {"items": [], "next_page_token": None}

        uploads_playlist_id = channels_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        playlist_items_response = service.playlistItems().list(
            playlistId=uploads_playlist_id,
            part="snippet",
            maxResults=limit,
            pageToken=page_token
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
        
        return {
            "items": videos,
            "next_page_token": playlist_items_response.get("nextPageToken")
        }

    except Exception as e:
        print(f"Error fetching paginated videos: {e}")
        return {"items": [], "next_page_token": None}

def get_my_videos_with_filter(yt_creds, limit=50, date_filter='today'):
    """
    Mengambil video pengguna dan menyaringnya berdasarkan rentang waktu.
    Melakukan pengambilan halaman (pagination) secara otomatis hingga batas limit atau filter terpenuhi.
    
    Args:
        yt_creds (dict): Kredensial sesi.
        limit (int): Batas maksimum video yang dikembalikan.
        date_filter (str): Filter waktu ('today', '1week', '1month', '6months', '12months').
        
    Returns:
        dict: {'items': list} Daftar video yang sesuai kriteria.
    """
    from datetime import datetime, timedelta
    
    service = get_youtube_client_from_session(yt_creds)
    if not service:
        return {"items": []}

    try:
        now = datetime.utcnow()
        if date_filter == 'today':
            published_after = (now - timedelta(days=1)).isoformat("T") + "Z"
        elif date_filter == '1week':
            published_after = (now - timedelta(weeks=1)).isoformat("T") + "Z"
        elif date_filter == '1month':
            published_after = (now - timedelta(days=30)).isoformat("T") + "Z"
        elif date_filter == '6months':
            published_after = (now - timedelta(days=180)).isoformat("T") + "Z"
        elif date_filter == '12months':
            published_after = (now - timedelta(days=365)).isoformat("T") + "Z"
        else:
            published_after = (now - timedelta(days=365)).isoformat("T") + "Z"

        channels_response = service.channels().list(
            mine=True,
            part="contentDetails"
        ).execute()

        if not channels_response.get("items"):
            return {"items": []}

        uploads_playlist_id = channels_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        videos = []
        page_token = None
        
        while len(videos) < limit:
            request_limit = min(50, limit - len(videos))
            
            playlist_params = {
                "playlistId": uploads_playlist_id,
                "part": "snippet",
                "maxResults": request_limit,
            }
            
            if page_token:
                playlist_params["pageToken"] = page_token
            
            playlist_items_response = service.playlistItems().list(**playlist_params).execute()
            
            for item in playlist_items_response.get("items", []):
                snippet = item["snippet"]
                published_at = snippet["publishedAt"]
                
                video_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                filter_date = datetime.fromisoformat(published_after.replace('Z', '+00:00'))
                
                if video_date < filter_date:
                    continue
                
                videos.append({
                    "id": snippet["resourceId"]["videoId"],
                    "title": snippet["title"],
                    "thumbnail": snippet["thumbnails"].get("medium", snippet["thumbnails"].get("default"))["url"],
                    "published_at": published_at
                })
                
                if len(videos) >= limit:
                    break
            
            page_token = playlist_items_response.get("nextPageToken")
            if not page_token:
                break
        
        return {"items": videos}

    except Exception as e:
        print(f"Error fetching filtered videos: {e}")
        return {"items": []}

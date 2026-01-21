from .comment_processing import process_youtube_comments, process_raw_comments
from .youtube import (
    extract_channel_info,
    get_video_info,
    get_channel_info,
    get_channel_uploads_playlist,
    get_videos_from_playlist,
    collect_comments
)

def analyze_content(url, limit=100, video_count=5, comments_per_video=None):
    """
    Mengorkestrasi pengambilan dan analisis konten YouTube (Video tunggal atau Channel).
    
    Args:
        url (str): URL YouTube atau handle channel.
        limit (int): Batas maksimum total komentar (digunakan untuk video tunggal atau default).
        video_count (int): Jumlah maksimum video yang diambil jika input adalah channel.
        comments_per_video (int): Batas komentar per video jika input adalah channel.
        
    Returns:
        dict: Dictionary berisi:
            - 'results': Daftar komentar hasil analisis.
            - 'stats': Statistik dari analisis.
            - 'source_info': Informasi tentang sumber video/channel.
            - 'error_msg': Pesan kesalahan jika terjadi kegagalan.
    """
    if comments_per_video is None:
        comments_per_video = limit
        
    id_type, identifier = extract_channel_info(url)
    
    results = []
    stats = {}
    error_msg = None
    source_info = None
    
    if id_type == "video":
        if not identifier:
             error_msg = "URL Video tidak valid."
        else:
            video_url = f"https://www.youtube.com/watch?v={identifier}"
            results, stats = process_youtube_comments(video_url, limit=limit)
            
            source_info = get_video_info(identifier)
            if source_info:
                source_info["type"] = "video"
        
    elif id_type in ("handle", "channel_id"):
        source_info = get_channel_info(identifier, id_type)
        if source_info:
            source_info["type"] = "channel"
        
        playlist_id = get_channel_uploads_playlist(identifier, id_type)
        if not playlist_id:
            error_msg = "Channel tidak ditemukan atau tidak memiliki playlist Uploads publik."
        else:
            video_ids = get_videos_from_playlist(playlist_id, limit=video_count)
            
            if not video_ids:
                error_msg = "Tidak ditemukan video pada channel ini."
            else:
                all_raw_comments = []
                for vid in video_ids:
                    v_url = f"https://www.youtube.com/watch?v={vid}"
                    batch = collect_comments(v_url, limit=comments_per_video)
                    all_raw_comments.extend(batch)
                
                if not all_raw_comments:
                    error_msg = f"Tidak ada komentar ditemukan dari {len(video_ids)} video terakhir."
                else:
                    results, stats = process_raw_comments(all_raw_comments)

    else:
        error_msg = "Link tidak valid. Masukkan URL video, Channel ID, atau Handle (@username)."
        
    return {
        "results": results,
        "stats": stats,
        "source_info": source_info,
        "error_msg": error_msg
    }

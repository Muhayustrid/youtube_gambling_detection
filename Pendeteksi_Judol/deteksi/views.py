from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.conf import settings
from django.urls import reverse
import os
from django.http import HttpResponse
from deteksi.ml.predict import predict_comment
from .services.comment_processing import process_youtube_comments, process_raw_comments
from .services.ai_insight import generate_insight
from .services.youtube import (
    get_youtube_client_from_session,
    create_oauth_flow,
    fetch_youtube_user_info_oauth,
    revoke_youtube_token,
    perform_moderation_action,
    extract_youtube_video_id,
    extract_channel_info,
    get_channel_uploads_playlist,
    get_videos_from_playlist,
    collect_comments,
    get_my_latest_videos
)

from googleapiclient.errors import HttpError

# ===== FUNGSI MODERASI =====
def moderate_comments(request):
    if request.method != "POST":
        return HttpResponseForbidden("POST only")

    comment_ids = request.POST.getlist("comment_id")
    action = request.POST.get("action")
    block_user = request.POST.get("block_user")
    block_user_map = {'0': False, '1': True}
    
    svc = get_youtube_client_from_session(request.session.get("yt_creds"))
    
    if not svc:
        return JsonResponse({
            "ok": False, 
            "msg": "Belum login OAuth",
            "error_type": "auth"
        }, status=401)

    try:
        ok, msg, err_type = perform_moderation_action(svc, comment_ids, action, block_user_map.get(block_user, False))
        if not ok:
             return JsonResponse({
                "ok": False, 
                "msg": msg,
                "error_type": err_type
            }, status=400)
            
        return JsonResponse({
            "ok": True, 
            "count": len(comment_ids),
            "msg": msg
        })
        
    except HttpError as e:
        error_details = e.error_details[0] if e.error_details else {}
        reason = error_details.get('reason', 'unknown')
        
        if reason == 'processingFailure':
            msg = "Anda tidak memiliki izin untuk moderasi komentar di video ini. Pastikan Anda adalah pemilik channel/video."
            error_type = "no_permission"
        elif reason == 'forbidden':
            msg = "Akses ditolak. Anda tidak memiliki izin untuk melakukan moderasi."
            error_type = "forbidden"
        elif reason == 'commentNotFound':
            msg = "Komentar tidak ditemukan atau sudah dihapus."
            error_type = "not_found"
        else:
            msg = f"Gagal moderasi komentar: {error_details.get('message', str(e))}"
            error_type = "api_error"
        
        return JsonResponse({
            "ok": False, 
            "msg": msg,
            "error_type": error_type,
            "details": str(e) if settings.DEBUG else None 
        }, status=e.resp.status)
        
    except Exception as e:
        return JsonResponse({
            "ok": False, 
            "msg": f"Terjadi kesalahan: {str(e)}",
            "error_type": "server_error"
        }, status=500)
# ===== END FUNGSI MODERASI =====

# ===== FUNGSI OAUTH =====
if settings.DEBUG:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

def oauth_start(request):
    flow = create_oauth_flow(
        redirect_uri=request.build_absolute_uri(reverse("oauth_callback"))
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session["oauth_state"] = state
    return redirect(auth_url)


def oauth_callback(request):
    state = request.session.get("oauth_state")
    flow = create_oauth_flow(
        redirect_uri=request.build_absolute_uri(reverse("oauth_callback")),
        state=state,
    )
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    creds = flow.credentials

    user_info = fetch_youtube_user_info_oauth(creds)

    request.session["yt_creds"] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
        "user": user_info,  
    }
    return redirect("index")

def revoke_and_logout_view(request):
    creds = request.session.get('yt_creds')

    if creds:
        token_to_revoke = creds.get('refresh_token', creds.get('token'))
        revoke_youtube_token(token_to_revoke)

    request.session.pop('yt_creds', None)
    
    return redirect('index')
# ===== END FUNGSI OAUTH =====

# ===== FUNGSI ANALISIS =====
def index(request):
    yt_creds = request.session.get("yt_creds")
    oauth_ok = yt_creds is not None
    ctx = {
        "oauth_ok": oauth_ok,
        "yt_user": yt_creds.get("user") if yt_creds else None,
    }

    if oauth_ok:
        ctx["my_videos"] = get_my_latest_videos(yt_creds, limit=6)

    selected_limit = ""
    
    if request.method == "POST":
        url = (request.POST.get("url") or "").strip()
        selected_limit = (request.POST.get("limit") or "")
        
        try:
            limit = int(selected_limit)
        except (ValueError, TypeError):
            limit = 100

        try:
            video_count_param = int(request.POST.get("video_count") or 5)
        except:
            video_count_param = 5
            
        try:
            comments_per_video_param = int(request.POST.get("comments_per_video") or limit)
        except:
            comments_per_video_param = limit
        
        # Detect Input Type
        id_type, identifier = extract_channel_info(url)
        
        results = []
        stats = {}
        error_msg = None
        
        if id_type == "video":
            if not identifier:
                 error_msg = "URL Video tidak valid."
            else:
                video_url = f"https://www.youtube.com/watch?v={identifier}"
                results, stats = process_youtube_comments(video_url, limit=limit)
            
        elif id_type in ("handle", "channel_id"):
            # Fetch Channel Uploads
            playlist_id = get_channel_uploads_playlist(identifier, id_type)
            if not playlist_id:
                error_msg = "Channel tidak ditemukan atau tidak memiliki playlist Uploads publik."
            else:
                # Fetch Videos from Playlist
                video_ids = get_videos_from_playlist(playlist_id, limit=video_count_param)
                
                if not video_ids:
                    error_msg = "Tidak ditemukan video pada channel ini."
                else:
                    all_raw_comments = []
                    # Collecting comments
                    for vid in video_ids:
                        v_url = f"https://www.youtube.com/watch?v={vid}"
                        batch = collect_comments(v_url, limit=comments_per_video_param)
                        all_raw_comments.extend(batch)
                    
                    if not all_raw_comments:
                        error_msg = f"Tidak ada komentar ditemukan dari {len(video_ids)} video terakhir."
                    else:
                        # Process Aggregated Comments
                        results, stats = process_raw_comments(all_raw_comments)

        else:
            error_msg = "Link tidak valid. Masukkan URL video, Channel ID, atau Handle (@username)."

        # Error Handling
        if error_msg:
            ctx.update({
                "error_message": error_msg,
                "url": url, 
                "selected_limit": selected_limit,
            })
            if request.headers.get('HX-Request'):
                # Ensure oauth_ok is in context for HTMX error response
                ctx["oauth_ok"] = oauth_ok
                htmx_response = f"""
                <div id="urlInlineError" hx-swap-oob="true" class="error-message-inline">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    {error_msg}
                </div>

                <script>
                    var input = document.getElementById('urlInput');
                    input.classList.add('input-error');
                    input.focus();
                </script>
                """
                return HttpResponse(htmx_response)
            return render(request, "html/index.html", ctx)
        
        # Ensure oauth_ok is always in context for results_partial
        ctx["oauth_ok"] = oauth_ok
        
        # Generate Insight (Service Call)
        try: 
            llm_insight, llm_insight_cleaned, meta = generate_insight(url, limit, stats, results)
            ctx.update({
                "url": url,
                "llm_insight": llm_insight_cleaned,
                })
        except Exception as e:
            llm_insight = None
            llm_insight_cleaned = None
            meta = None

        
        ctx.update({
            "url": url,
            "rows": results,
            "selected_limit": selected_limit,
            "total_comments": stats["total"],
            "judi_count": stats["judi_count"],
            "clean_count": stats["clean_count"],
        })
        if request.headers.get('HX-Request'):
            return render(request, "html/partials/results_partial.html", ctx)

    return render(request, "html/index.html", ctx)
# ===== END FUNGSI ANALISIS =====

# ===== FUNGSI TESTING =====
def home(request):
    context = {}
    if request.method == "POST":
        text = request.POST.get("comment")
        result = predict_comment(text)
        context["text"] = text
        context["clean"] = result["clean"]
        context["label"] = "PROMOSI JUDOL" if result["label"] == 1 else "BUKAN"
        context["proba"] = result["proba"]
    return render(request, "html/tes.html", context)
    return render(request, "html/tes.html", context)
# ===== END FUNGSI TESTING =====

def my_videos_partial(request):
    if not request.session.get("yt_creds"):
         return HttpResponseForbidden("Not Authenticated")
         
    try:
        limit = int(request.GET.get('limit', 6))
    except (ValueError, TypeError):
        limit = 6

    videos = get_my_latest_videos(request.session.get("yt_creds"), limit=limit)
    return render(request, "html/partials/video_grid.html", {"my_videos": videos})

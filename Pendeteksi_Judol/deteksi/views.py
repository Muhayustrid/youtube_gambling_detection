from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.conf import settings
from django.urls import reverse
import os
from django.http import HttpResponse

from deteksi.ml.predict import predict_comment
from .ml.yt import extract_youtube_video_id

from .services.comment_processing import process_youtube_comments
from .services.ai_insight import generate_insight
from .services.youtube import (
    get_youtube_client_from_session,
    create_oauth_flow,
    fetch_youtube_user_info_oauth,
    revoke_youtube_token,
    perform_moderation_action
)
from googleapiclient.errors import HttpError

# Create your views here.



# Fungsi Aksi Moderasi Komentar YouTube
def moderate_comments(request):
    if request.method != "POST":
        return HttpResponseForbidden("POST only")

    comment_ids = request.POST.getlist("comment_id")
    
    action = request.POST.get("action")
    
    block_user = request.POST.get("block_user")
    
    block_user_map = {'0': False, '1': True}

    # if block_user == '1':
    #     block_user = True
        
    print(block_user_map.get(block_user, "GAGAL"))
    
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
        # ✅ Handle YouTube API Error
        error_details = e.error_details[0] if e.error_details else {}
        reason = error_details.get('reason', 'unknown')
        
        # Pesan error 
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
        
# end fungsi moderasi

# Fungsi OAuth YouTube
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
    # request.session.pop('yt_user', None)
    
    return redirect('index')

# end fungsi OAuth




# Fungsi Analisis Komentar YouTube

def index(request):
    yt_creds = request.session.get("yt_creds")
    oauth_ok = yt_creds is not None
    ctx = {
        "oauth_ok": oauth_ok,
        "yt_user": yt_creds.get("user") if yt_creds else None,
    }

    selected_limit = ""
    
    if request.method == "POST":
        url = (request.POST.get("url") or "").strip()
        selected_limit = (request.POST.get("limit") or "")
        try:
            limit = int(selected_limit)
        except (ValueError, TypeError):
            limit = 100
        
        # Validasi url
        video_id = extract_youtube_video_id(url)
        if not video_id:
            error_msg = "Link tidak valid. Mohon masukkan URL video YouTube yang benar."
            ctx.update({
                "error_message": error_msg,
                "url": url, 
                "selected_limit": selected_limit,
            })
            if request.headers.get('HX-Request'):
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
        
        # --- Proses Komentar (Service Call) ---
        results, stats = process_youtube_comments(url, limit=limit)

        # --- Generate Insight (Service Call) ---
        try:
            llm_insight, llm_insight_html, meta = generate_insight(url, limit, stats, results)
            ctx.update({
                "llm_insight": llm_insight,
                "llm_insight_html": llm_insight_html,
                })
        except Exception as e:
            print(f"Error generating insight: {e}")
            llm_insight = None
            llm_insight_html = None
            meta = None
        
        # Update Context untuk Render
        ctx.update({
            "url": url,
            "rows": results,
            "selected_limit": selected_limit,
            # "llm_insight": llm_insight,
            # "llm_insight_html": llm_insight_html,
            "total_comments": stats["total"],
            "judi_count": stats["judi_count"],
            "clean_count": stats["clean_count"],
        })
        if request.headers.get('HX-Request'):
            return render(request, "html/partials/results_partial.html", ctx)

    return render(request, "html/index.html", ctx)

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


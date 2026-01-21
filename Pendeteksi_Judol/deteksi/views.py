from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.conf import settings
from django.urls import reverse
from django.core.cache import cache
import os
import uuid
from googleapiclient.errors import HttpError

from deteksi.ml.predict import predict_comment, predict_and_explain
from .services.ai_insight import generate_insight
from .services.youtube import (
    get_youtube_client_from_session,
    create_oauth_flow,
    fetch_youtube_user_info_oauth,
    revoke_youtube_token,
    perform_moderation_action,
    get_my_latest_videos,
    get_my_videos_paginated,
    get_my_videos_with_filter,
)
from .services.orchestrator import analyze_content

if settings.DEBUG:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

def moderate_comments(request):
    """
    Menangani permintaan moderasi komentar (hapus atau tolak & blokir pengguna).
    Hanya menerima metode POST.
    
    Args:
        request: Objek HTTP request Django.
        
    Returns:
        JsonResponse: Status keberhasilan atau kegagalan operasi.
    """
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

def oauth_start(request):
    """
    Memulai proses autentikasi OAuth Google.
    Mengarahkan pengguna ke halaman persetujuan Google.
    
    Args:
        request: Objek HTTP request Django.
        
    Returns:
        HttpResponseRedirect: Mengarahkan pengguna ke URL otorisasi Google.
    """
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
    """
    Menangani callback dari proses autentikasi OAuth Google.
    Menukar kode otorisasi dengan token akses dan menyimpan kredensial di sesi.
    
    Args:
        request: Objek HTTP request Django.
        
    Returns:
        HttpResponseRedirect: Mengarahkan pengguna kembali ke halaman utama (index).
    """
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
    """
    Mencabut token akses Google dan mengeluarkan pengguna dari sesi (logout).
    
    Args:
        request: Objek HTTP request Django.
        
    Returns:
        HttpResponseRedirect: Mengarahkan pengguna ke halaman utama.
    """
    creds = request.session.get('yt_creds')

    if creds:
        token_to_revoke = creds.get('refresh_token', creds.get('token'))
        revoke_youtube_token(token_to_revoke)

    request.session.pop('yt_creds', None)
    
    return redirect('index')

def get_ai_insight(request):
    """
    Mengambil insight AI berdasarkan ID analisis yang tersimpan di cache.
    Menggunakan mekanisme lazy loading untuk performa yang lebih baik.
    
    Args:
        request: Objek HTTP request Django.
        
    Returns:
        HttpResponse: Render HTML potongan insight atau respons kosong.
    """
    analysis_id = request.GET.get('analysis_id')
    if not analysis_id:
        return HttpResponse("")
    
    data = cache.get(f"analysis_data_{analysis_id}")
    if not data:
        return HttpResponse('<div class="ai-insight-box fade-in" style="text-align:center; padding: 2rem;">Data sesi berakhir. Silakan analisis ulang.</div>')
        
    url = data['url']
    limit = data['limit']
    stats = data['stats']
    
    try:
        llm_insight, llm_insight_cleaned, meta = generate_insight(url, limit, stats)
    except Exception as e:
        llm_insight_cleaned = None

    if not llm_insight_cleaned:
        return HttpResponse("")

    ctx = {
        "llm_insight": llm_insight_cleaned
    }
    return render(request, "html/partials/insight_content.html", ctx)

def index(request):
    """
    Halaman utama aplikasi.
    Menangani input URL YouTube (video/channel), melakukan analisis komentar menggunakan orchestrator,
    dan menampilkan hasilnya. Juga menampilkan video terbaru pengguna jika login.
    
    Args:
        request: Objek HTTP request Django.
        
    Returns:
        HttpResponse: Halaman HTML utama atau respons parsial untuk HTMX.
    """
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
        
        analysis_result = analyze_content(url, limit, video_count_param, comments_per_video_param)
        
        results = analysis_result["results"]
        stats = analysis_result["stats"]
        error_msg = analysis_result["error_msg"]
        source_info = analysis_result["source_info"]

        if error_msg:
            ctx.update({
                "error_message": error_msg,
                "url": url, 
                "selected_limit": selected_limit,
            })
            if request.headers.get('HX-Request'):
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
        
        ctx["oauth_ok"] = oauth_ok
        
        analysis_id = str(uuid.uuid4())
        cache_data = {
            "url": url,
            "limit": limit,
            "stats": stats
        }
        
        cache.set(f"analysis_data_{analysis_id}", cache_data, 600)
        
        ctx.update({
            "analysis_id": analysis_id,
        })

        ctx.update({
            "url": url,
            "rows": results,
            "selected_limit": selected_limit,
            "total_comments": stats["total"],
            "judi_count": stats["judi_count"],
            "clean_count": stats["clean_count"],
            "source_info": source_info,
        })
        if request.headers.get('HX-Request'):
            return render(request, "html/partials/results_partial.html", ctx)

    return render(request, "html/index.html", ctx)

def get_dataset(request):
    """
    Halaman khusus untuk mendapatkan dataset dari komentar YouTube.
    Mirip dengan fungsi index, namun dengan tampilan yang disesuaikan untuk ekspor data.
    
    Args:
        request: Objek HTTP request Django.
        
    Returns:
        HttpResponse: Halaman HTML dataset atau respons parsial.
    """
    yt_creds = request.session.get("yt_creds")
    oauth_ok = yt_creds is not None
    ctx = {
        "oauth_ok": oauth_ok,
        "is_dataset_view": True,
    }

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
        
        analysis_result = analyze_content(url, limit, video_count_param, comments_per_video_param)
        
        results = analysis_result["results"]
        stats = analysis_result["stats"]
        error_msg = analysis_result["error_msg"]
        source_info = analysis_result["source_info"]

        if error_msg:
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
            return render(request, "html/getdataset.html", ctx)
        
        ctx.update({
            "url": url,
            "rows": results,
            "selected_limit": selected_limit,
            "total_comments": stats.get("total", 0),
            "judi_count": stats.get("judi_count", 0),
            "clean_count": stats.get("clean_count", 0),
            "source_info": source_info,
        })
        if request.headers.get('HX-Request'):
            return render(request, "html/partials/results_partial.html", ctx)

    return render(request, "html/getdataset.html", ctx)

def home(request):
    """
    Halaman untuk pengujian prediksi komentar tunggal secara manual.
    Menampilkan form input teks dan hasil prediksi.
    
    Args:
        request: Objek HTTP request Django.
        
    Returns:
        HttpResponse: Halaman HTML tes.
    """
    context = {}
    if request.method == "POST":
        text = request.POST.get("comment")
        result = predict_comment(text)
        context["text"] = text
        context["clean"] = result["clean"]
        context["label"] = "PROMOSI JUDOL" if result["label"] == 1 else "BUKAN"
        context["proba"] = result["proba"]
    return render(request, "html/tes.html", context)

def my_videos_partial(request):
    """
    Mengambil dan merender grid video terbaru milik pengguna untuk dimuat secara parsial.
    Biasanya digunakan untuk pagination atau reload konten.
    
    Args:
        request: Objek HTTP request Django.
        
    Returns:
        HttpResponse: HTML parsial grid video.
    """
    if not request.session.get("yt_creds"):
         return HttpResponseForbidden("Not Authenticated")
         
    try:
        limit = int(request.GET.get('limit', 6))
    except (ValueError, TypeError):
        limit = 6

    videos = get_my_latest_videos(request.session.get("yt_creds"), limit=limit)
    return render(request, "html/partials/video_grid.html", {"my_videos": videos})

def video_saya(request):
    """
    Halaman "Video Saya" yang menampilkan daftar video milik pengguna yang sedang login.
    Mendukung filter tanggal dan caching hasil untuk performa.
    Memerlukan login (OAuth).
    
    Args:
        request: Objek HTTP request Django.
        
    Returns:
        HttpResponse: Halaman HTML daftar video pengguna.
    """
    yt_creds = request.session.get("yt_creds")
    if not yt_creds:
        return redirect('oauth_start')

    oauth_ok = True

    date_filter = request.GET.get('date_filter', 'today')

    user_handle = yt_creds.get("user", {}).get("handle", "")
    if not user_handle:
        user_handle = yt_creds.get("user", {}).get("name", "unknown")

    cache_key = f"videos_{user_handle}_{date_filter}"

    videos = cache.get(cache_key)

    if videos is None:
        result = get_my_videos_with_filter(yt_creds, limit=50, date_filter=date_filter)
        videos = result["items"]
        cache.set(cache_key, videos, 900)

    try:
        from google.oauth2.credentials import Credentials
        creds_obj = Credentials(
            token=yt_creds["token"],
            refresh_token=yt_creds.get("refresh_token"),
            token_uri=yt_creds["token_uri"],
            client_id=yt_creds["client_id"],
            client_secret=yt_creds["client_secret"],
            scopes=yt_creds["scopes"],
        )
        fresh_user_info = fetch_youtube_user_info_oauth(creds_obj)
        yt_creds["user"] = fresh_user_info
        request.session["yt_creds"] = yt_creds
    except Exception as e:
        print(f"Failed to refresh user info: {e}")
        fresh_user_info = yt_creds.get("user")

    ctx = {
        "oauth_ok": oauth_ok,
        "yt_user": fresh_user_info,
        "my_videos": videos,
        "date_filter": date_filter
    }
    return render(request, "html/video_saya.html", ctx)

def comment_detail(request):
    """
    Menampilkan detail prediksi dan penjelasan untuk komentar tertentu dalam modal.
    Menghitung ulang prediksi dan memberikan konteks penjelasan (LIME atau bobot kata).
    
    Args:
        request: Objek HTTP request Django.
        
    Returns:
        HttpResponse: HTML parsial modal detail komentar.
    """
    if request.method != "POST":
        return HttpResponseForbidden("Method not allowed")
    
    text = request.POST.get("text")
    if not text:
        return HttpResponse("No text provided", status=400)
    
    explanation = predict_and_explain(text)
    
    ctx = explanation
    if "proba_judol_pct" not in ctx:
        ctx["proba_judol_pct"] = ctx["proba_judol"] * 100
        
    return render(request, "html/partials/comment_detail_modal.html", ctx)

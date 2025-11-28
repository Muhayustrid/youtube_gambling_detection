from django.http import JsonResponse, HttpResponseForbidden
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.shortcuts import redirect

def _svc_from_session(request):
    data = request.session.get("yt_creds")
    if not data:
        return None
    creds = Credentials(
        token=data["token"],
        refresh_token=data.get("refresh_token"),
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=data["scopes"],
    )
    return build("youtube", "v3", credentials=creds)

from googleapiclient.errors import HttpError
from django.conf import settings

def moderate_comments(request):
    if request.method != "POST":
        return HttpResponseForbidden("POST only")

    comment_ids = request.POST.getlist("comment_id")
    action = request.POST.get("action")  
    svc = _svc_from_session(request)
    
    if not svc:
        return JsonResponse({
            "ok": False, 
            "msg": "Belum login OAuth",
            "error_type": "auth"
        }, status=401)

    try:
        if action == "delete":
            for cid in comment_ids:
                svc.comments().delete(id=cid).execute()
        elif action == "reject":
            svc.comments().setModerationStatus(
                id=",".join(comment_ids),
                moderationStatus="rejected",
                banAuthor=False
            ).execute()
        else:
            return JsonResponse({
                "ok": False, 
                "msg": "Aksi tidak dikenal",
                "error_type": "invalid_action"
            }, status=400)
            
        return JsonResponse({
            "ok": True, 
            "count": len(comment_ids),
            "msg": f"Berhasil menghapus {len(comment_ids)} komentar"
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
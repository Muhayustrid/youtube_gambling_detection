# Create your views here.
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

def moderate_comments(request):
    if request.method != "POST":
        return HttpResponseForbidden("POST only")

    comment_ids = request.POST.getlist("comment_id")
    action = request.POST.get("action")  
    svc = _svc_from_session(request)
    if not svc:
        return JsonResponse({"ok": False, "msg": "Belum login OAuth"}, status=401)

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
            return JsonResponse({"ok": False, "msg": "Aksi tidak dikenal"}, status=400)
        return JsonResponse({"ok": True, "count": len(comment_ids)})
    except Exception as e:
        return JsonResponse({"ok": False, "msg": str(e)}, status=500)

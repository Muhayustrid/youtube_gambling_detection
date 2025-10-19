from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from .ml.predict import predict_comment
from .ml.yt import collect_comments

def home(request):
    context = {}
    if request.method == "POST":
        text = request.POST.get("comment")
        result = predict_comment(text)
        context["text"] = text
        context["clean"] = result["clean"]
        context["label"] = "PROMOSI JUDOL" if result["label"] == 1 else "BUKAN"
        context["proba"] = result["proba"]
    return render(request, "html/index.html", context)

def analyze(request):
    ctx = {}
    if request.method == "POST":
        url   = (request.POST.get("url") or "").strip()
        limit = int(request.POST.get("limit") or 100)

        rows = collect_comments(url, limit=limit)
        results = []
        for r in rows:
            pred = predict_comment(r["text"])
            results.append({
                **r,
                "text_clean": pred["clean"],
                "label": pred["label"],     
                "proba": pred["proba"],     
            })
        ctx.update({"url": url, "rows": results})
        ctx["oauth_ok"] = bool(request.session.get("yt_creds")) 
    return render(request, "html/crawling_analyze.html", ctx)
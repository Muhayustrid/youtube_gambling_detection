from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from .ml.predict import predict_comment

def home(request):
    context = {}
    if request.method == "POST":
        text = request.POST.get("comment")
        result = predict_comment(text)
        context["text"] = text
        context["clean"] = result["clean"]
        context["label"] = "PROMOSI JUDOL" if result["label"] == 1 else "BUKAN"
        context["proba"] = result["proba"]
    return render(request, "html/home.html", context)

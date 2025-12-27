from django.shortcuts import render
from .ml.predict import predict_comment
from .ml.yt import collect_comments, extract_youtube_video_id
from .ml.utils_text import top_keywords_from_texts
from .openrouter_client import call_openrouter, call_openrouter_with_fallback
import markdown
import json
import os
from django.utils import timezone
from django.core.cache import cache
from django.utils.html import escape

LLM_LOG_DIR = os.path.join(os.path.dirname(__file__), "llm_logs")
os.makedirs(LLM_LOG_DIR, exist_ok=True)
LLM_LOG_FILE = os.path.join(LLM_LOG_DIR, "llm_calls.jsonl")

CACHE_TTL = 60 * 10 

def _log_llm_call(prompt: str, response: str, meta: dict):
    entry = {
        "timestamp": timezone.now().isoformat(),
        "prompt": prompt,
        "response": response,
        "meta": meta,
    }
    with open(LLM_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _format_llm_response(text: str) -> str:
    """
    Convert markdown to HTML 
    """
    if not text:
        return ""
    
    if text.strip().startswith("```markdown"):
        # Cari ``````` terakhir dan hapus semuanya dari awal sampai akhir blok
        last_code_block_end = text.rfind("```")
        if last_code_block_end != -1:
            # Ambil teks di antara ```markdown dan ``` terakhir
            text = text[len("```markdown"):last_code_block_end].strip()
        else:
            # Fallback 
            text = text[len("```markdown"):].strip()
    elif text.strip().startswith("```"):
        # Jika hanya ````` tanpa identifier 'markdown'
        last_code_block_end = text.rfind("```")
        if last_code_block_end != -1:
            text = text[3:last_code_block_end].strip()
            
    # Convert markdown ke HTML
    html = markdown.markdown(
        text,
        extensions=['tables', 'nl2br', 'sane_lists']
    )
    
    # Remove <p> tags single line
    html = html.replace('<p><strong>', '<strong>')
    html = html.replace('</strong></p>', '</strong>')
    
    return html


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
    yt_creds = request.session.get("yt_creds")
    oauth_ok = yt_creds is not None
    ctx = {
        "oauth_ok": oauth_ok,
        "yt_user": yt_creds.get("user") if yt_creds else None,
    }

    selected_limit = ""
    rows = []
    results = []
    llm_insight = None
    llm_insight_html = None
    top_keywords = []
    
    meta = {}

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
            ctx.update({
                "error_message": "URL yang Anda masukkan tidak valid. Mohon periksa kembali link video YouTube.",
                "url": url, 
                "selected_limit": selected_limit,
            })
            return render(request, "html/crawling_analyze.html", ctx)
        
        # ambil komentar
        rows = collect_comments(url, limit=limit)

        # prediksi tiap komentar dan kumpulkan hasilnya
        results = []
        for r in rows:
            pred = predict_comment(r["text"])
            results.append({
                **r,
                "text_clean": pred["clean"],
                "label": pred["label"],
                "proba": pred["proba"],
            })

        # subset kategori
        positive_cleans = [item["text_clean"] for item in results if item["label"] == 1]
        negative_cleans = [item["text_clean"] for item in results if item["label"] == 0]

        # hitung top keywords dari subset
        top_keywords = top_keywords_from_texts(positive_cleans, top_n=30)
        top_keywords_negative = top_keywords_from_texts(negative_cleans, top_n=30)
        
        # ambil sampel komentar spam dengan confidence tinggi dan komentar bersih
        high_confidence_spam = sorted(
            [r for r in results if r["label"] == 1], 
            key=lambda x: x["proba"], 
            reverse=True)[:7]
        
        # Komenrar ragu
        unsure_comments = sorted(
            [r for r in results if 0.40 <= r["proba"] <= 0.60], 
            key=lambda x: x["proba"], 
            reverse=True)[:10]
        
        # sampel spam, bersih dan ragu
        sample_spam_comments = [c["text"] for c in high_confidence_spam]
        sample_clean_comments = [r["text"] for r in results if r["label"] == 0][:3]
        unsure_samples_str = "\n".join([f"- {c['text']} (Probabilitas: {c['proba']:.2%})" for c in unsure_comments])
        
        # string untuk keyword
        spam_keywords_str = "\n".join([f"- {w}: {c}" for w, c in top_keywords[:15]])
        clean_keywords_str = "\n".join([f"- {w}: {c}" for w, c in top_keywords_negative[:10]])
        
        # string untuk sampel komentar
        spam_samples_str = "\n".join([f"- {c}" for c in sample_spam_comments])
        clean_samples_str = "\n".join([f"- {c}" for c in sample_clean_comments])

        # ---- LLM flow  ----
        cache_key = f"llm_insight::{url}::limit::{limit}"
        cached = cache.get(cache_key)
        if cached:
            llm_insight = cached.get("insight")
            llm_insight_html = cached.get("html")
            meta = cached.get("meta", {})
        else:
            lines = [f"{w}: {c}" for w, c in top_keywords[:20]]
            prompt_text = (
                f"""
                    Berikut adalah data yang telah diproses:

                    **1. Top Keywords dari Komentar yang Diprediksi SPAM (Promosi Judi):**
                    {spam_keywords_str}
                    
                    **2. Top Keywords dari Komentar yang Diprediksi BERSIH (untuk perbandingan):**
                    {clean_keywords_str}
                    
                    **3. Contoh Komentar SPAM yang Paling Jelas:**
                    {spam_samples_str}
                    
                    **4. Contoh Komentar BERSIH:**
                    {clean_samples_str}
                    
                    **5. Contoh Komentar yang Model Ragu-ragu (Probabilitas 40-60%):**
                    {unsure_samples_str}

                    Berdasarkan data di atas, berikan insight yang **singkat, padat, dan jelas** dalam format markdown. Fokus pada:
                    a. **Taktik dan Pola Kalimat:** Bagaimana para spammer menyusun kalimatnya? Apakah mereka menggunakan trik tertentu (misal: karakter khusus, huruf besar, iming-iming)?
                    b. **Brand atau Nama Situs yang Paling Menonjol:** Sebutkan 2-3 brand judi yang paling sering muncul.
                    c. **Perbedaan Khas:** Apa perbedaan paling mencolok antara pola bahasa komentar spam dan bersih?
                    
                    Jawaban harus ringkas dan langsung ke intinya.
                    **Jika ada sampel spam yang terlihat jelas sebagai spam berikan catatan dan sebutkan brandnya kalau ada**
                    **Jika tidak ada komentar spam yang terdeteksi**, berikan ringkasan singkat (1-2 kalimat) bahwa komentar video tersebut bersih dan relevan dengan topik.**
                    **PENTING: Berikan jawaban langsung dalam format markdown tanpa membungkusnya di dalam blok kode.**
                    **PENTING: Bisa saja sampel yang diberikan merupakan prediksi salah, anda harus dapat mengenalinya.**
                    """
            )

            messages = [
                {"role": "system", "content": "Anda adalah ahli analisis keamanan digital berbahasa indonesia yang sedang menganalisis spam promosi judi online di komentar platform YouTube."},
                {"role": "user", "content": prompt_text}
            ]

            content, meta = call_openrouter_with_fallback(messages)
            if content:
                llm_insight = content.strip()
                llm_insight_html = _format_llm_response(llm_insight)
                
                # print("="*50)
                # print(f' Komentar tidak yakin {unsure_samples_str}')
                # print("RAW MARKDOWN DARI LLM:")
                # print(llm_insight)
                # print("-"*50)
                # print("HASIL KONVERSI KE HTML:")
                # print(llm_insight_html)
                # print("="*50)
                
                
                cache.set(cache_key, {
                    "insight": llm_insight,
                    "html": llm_insight_html,
                    "meta": meta
                }, CACHE_TTL)
                try:
                    _log_llm_call(prompt_text, llm_insight, meta or {})
                except Exception:
                    pass
            else:
                has_spam = any(item["label"] == 1 for item in results)
                if has_spam:
                    # fallback 
                    top3 = top_keywords[:3]
                    keywords_str = ', '.join([w for w, _ in top3])
                    
                    insight_text = f"""## Ringkasan Analisis

                            ### Pola Dominan
                            - Mayoritas promosi mengandung: **{keywords_str}**
                            - Banyak pola obfuscation (angka/leet/spacing)
                            - Ada frasa yang mengarahkan ke link eksternal

                            ### Brand Judi biasanya
                            - Slot online, Gacor, Bonus, Deposit
                            - Togel, Pulauwin, Garuda Hoki, Totot
                            - Live casino

                            """
                    meta = {
                    "model_used": "Fallback (Lokal)",
                    "error": "LLM API call failed"
                }
                else:
                # Fallback 
                    insight_text = f"""## Hasil Analisis
                    Tidak ada aktivitas spam promosi judi online yang terdeteksi pada komentar video ini. Semua komentar terlihat relevan dan bersih."""
                llm_insight = insight_text
                llm_insight_html = _format_llm_response(insight_text)

        ctx.update({"url": url})
        
    # Hitung statistik server-side
    total_comments = len(results)
    judi_count = sum(1 for item in results if item["label"] == 1)
    clean_count = total_comments - judi_count

    ctx.update({
        "rows": results,
        "selected_limit": selected_limit,
        "llm_insight": llm_insight,
        "llm_insight_html": llm_insight_html or _format_llm_response(llm_insight) if llm_insight else None,
        "meta": meta,
        "total_comments": total_comments,
        "judi_count": judi_count,
        "clean_count": clean_count,
    })

    return render(request, "html/crawling_analyze.html", ctx)

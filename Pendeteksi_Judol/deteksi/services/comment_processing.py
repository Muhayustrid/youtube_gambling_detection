from ..services.youtube import collect_comments, extract_youtube_video_id
from ..ml.predict import predict_comment
from ..ml.utils_text import top_keywords_from_texts

def process_youtube_comments(url, limit=100):
    """
    Mengambil komentar, melakukan prediksi, dan menghitung statistik dasar.
    """
    # 1. Validasi URL (dilakukan di view/controller, tapi helper ini bisa return None/Error jika perlu)
    
    # 2. Ambil komentar
    rows = collect_comments(url, limit=limit)

    # 3. Prediksi
    results = []
    for r in rows:
        pred = predict_comment(r["text"])
        results.append({
            **r,
            "text_clean": pred["clean"],
            "label": pred["label"],
            "proba": pred["proba"],
        })

    # 4. Hitung Statistik
    total_comments = len(results)
    judi_count = sum(1 for item in results if item["label"] == 1)
    clean_count = total_comments - judi_count

    # Subset
    positive_cleans = [item["text_clean"] for item in results if item["label"] == 1]
    negative_cleans = [item["text_clean"] for item in results if item["label"] == 0]

    # Top Keywords
    top_keywords = top_keywords_from_texts(positive_cleans, top_n=30)
    top_keywords_negative = top_keywords_from_texts(negative_cleans, top_n=30)

    # Samples
    # Spam confidence tinggi
    high_confidence_spam = sorted(
        [r for r in results if r["label"] == 1], 
        key=lambda x: x["proba"], 
        reverse=True)[:7]
    
    # Ragu (Unsure)
    unsure_comments = sorted(
        [r for r in results if 0.40 <= r["proba"] <= 0.60], 
        key=lambda x: x["proba"], 
        reverse=True)[:10]

    # Clean samples
    sample_clean_comments = [r["text"] for r in results if r["label"] == 0][:3]

    # Formatting strings for LLM or Display
    unsure_samples_str = "\n".join([f"- {c['text']} (Probabilitas: {c['proba']:.2%})" for c in unsure_comments])
    spam_keywords_str = "\n".join([f"- {w}: {c}" for w, c in top_keywords[:15]])
    clean_keywords_str = "\n".join([f"- {w}: {c}" for w, c in top_keywords_negative[:10]])
    spam_samples_str = "\n".join([f"- {c['text']}" for c in high_confidence_spam]) # Note: original code used c["text"]
    clean_samples_str = "\n".join([f"- {c}" for c in sample_clean_comments])

    stats = {
        "total": total_comments,
        "judi_count": judi_count,
        "clean_count": clean_count,
        "top_keywords": top_keywords,
        "top_keywords_negative": top_keywords_negative,
        "spam_keywords_str": spam_keywords_str,
        "clean_keywords_str": clean_keywords_str,
        "spam_samples_str": spam_samples_str,
        "clean_samples_str": clean_samples_str,
        "unsure_samples_str": unsure_samples_str,
        "high_confidence_spam": high_confidence_spam,
        "unsure_comments": unsure_comments,
    }

    return results, stats

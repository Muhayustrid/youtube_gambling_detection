from ..services.youtube import collect_comments, extract_youtube_video_id
from ..ml.predict import predict_comment
from ..ml.utils_text import top_keywords_from_texts

# ===== FUNGSI PEMROSESAN KOMENTAR =====
def process_raw_comments(rows):
    """
    Memproses daftar komentar raw (list of dict) menjadi hasil prediksi dan statistik.
    Helper ini dipisahkan agar bisa digunakan untuk data gabungan dari banyak video.
    Returns: (results, stats)
    """
    results = []
    
    # Batch predict (optimalisasi: jika model support batch, lakukan di sini. 
    # Saat ini loop satu per satu sesuai existing logic)
    for r in rows:
        pred = predict_comment(r["text"])
        results.append({
            **r,
            "text_clean": pred["clean"],
            "label": pred["label"],
            "proba": pred["proba"],
        })

    # Hitung Statistik
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
    high_confidence_spam = sorted(
        [r for r in results if r["label"] == 1], 
        key=lambda x: x["proba"], 
        reverse=True)[:7]
    
    unsure_comments = sorted(
        [r for r in results if 0.40 <= r["proba"] <= 0.60], 
        key=lambda x: x["proba"], 
        reverse=True)[:10]

    sample_clean_comments = [r["text"] for r in results if r["label"] == 0][:3]

    # Formatting strings
    unsure_samples_str = "\n".join([f"- {c['text']} (Probabilitas: {c['proba']:.2%})" for c in unsure_comments])
    spam_keywords_str = "\n".join([f"- {w}: {c}" for w, c in top_keywords[:15]])
    clean_keywords_str = "\n".join([f"- {w}: {c}" for w, c in top_keywords_negative[:10]])
    spam_samples_str = "\n".join([f"- {c['text']}" for c in high_confidence_spam])
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

def process_youtube_comments(url, limit=100):
    """
    Mengambil komentar dari satu video, lalu memprosesnya.
    """
    # 1. Ambil komentar
    rows = collect_comments(url, limit=limit)
    
    # 2. Proses
    return process_raw_comments(rows)
# ===== END FUNGSI PEMROSESAN KOMENTAR =====

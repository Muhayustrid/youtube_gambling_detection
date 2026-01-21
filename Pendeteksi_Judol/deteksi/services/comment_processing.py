from ..services.youtube import collect_comments, extract_youtube_video_id
from ..ml.predict import predict_comment
from ..ml.utils_text import top_keywords_from_texts
from datetime import datetime

def process_raw_comments(rows):
    """
    Memproses daftar komentar mentah (list of dict) untuk mendapatkan hasil prediksi judi online 
    dan statistik terkait.
    
    Args:
        rows (list[dict]): Daftar komentar mentah yang diambil dari YouTube.
        
    Returns:
        tuple: (results, stats)
            - results (list): Daftar komentar dengan tambahan prediksi (label, proba, clean text).
            - stats (dict): Statistik ringkasan (total, judi, clean, keywords, sampel).
    """
    results = []
    
    for r in rows:
        pred = predict_comment(r["text"])
        
        pub_at = r.get("published_at")
        if isinstance(pub_at, str):
            try:
                pub_at = datetime.fromisoformat(pub_at.replace("Z", "+00:00"))
            except ValueError:
                pass

        results.append({
            **r,
            "published_at": pub_at,
            "text_clean": pred["clean"],
            "label": pred["label"],
            "proba": pred["proba"],
        })

    total_comments = len(results)
    judi_count = sum(1 for item in results if item["label"] == 1)
    clean_count = total_comments - judi_count

    positive_cleans = [item["text_clean"] for item in results if item["label"] == 1]
    negative_cleans = [item["text_clean"] for item in results if item["label"] == 0]

    top_keywords = top_keywords_from_texts(positive_cleans, top_n=30)
    top_keywords_negative = top_keywords_from_texts(negative_cleans, top_n=30)

    high_confidence_spam = sorted(
        [r for r in results if r["label"] == 1], 
        key=lambda x: x["proba"], 
        reverse=True)[:7]
    
    unsure_comments = sorted(
        [r for r in results if 0.40 <= r["proba"] <= 0.60], 
        key=lambda x: x["proba"], 
        reverse=True)[:10]

    sample_clean_comments = [r["text"] for r in results if r["label"] == 0][:3]

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
    Fungsi wrapper untuk mengambil komentar dari satu video YouTube, 
    kemudian langsung memproses prediksinya.
    
    Args:
        url (str): URL video YouTube.
        limit (int): Batas maksimum komentar yang diambil.
        
    Returns:
        tuple: (results, stats) hasil dari process_raw_comments.
    """
    rows = collect_comments(url, limit=limit)
    
    return process_raw_comments(rows)

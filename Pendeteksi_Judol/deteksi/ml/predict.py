from __future__ import annotations
from pathlib import Path
from threading import Lock
import joblib

USE_PREPROCESS = True
BEST_THR = 0.50

_MODEL_PATH = Path(__file__).resolve().parent / "model" / "judol_pipeline_v16.joblib"

_lock = Lock()
_PIPE = None

if USE_PREPROCESS:
    from .preprocess import preprocess

def _lazy_load():
    """
    Memuat model secara lazy (hanya saat pertama kali dibutuhkan).
    Menggunakan mekanisme Thread Lock untuk keamanan concurrency.
    """
    global _PIPE
    if _PIPE is not None:
        return
    with _lock:
        if _PIPE is None:
            blob = joblib.load(_MODEL_PATH)
            _PIPE = blob["pipeline"]

def predict_comment(raw_text: str) -> dict:
    """
    Melakukan prediksi klasifikasi judi online pada teks komentar tunggal.
    
    Args:
        raw_text (str): Teks komentar mentah.
        
    Returns:
        dict: Dictionary berisi:
            - 'label': 1 (Judi) atau 0 (Non-Judi)
            - 'proba': Probabilitas kelas positif (Judi)
            - 'clean': Teks hasil preprocessing
    """
    _lazy_load()
    text = (raw_text or "")
    try:
        clean = preprocess(text) if USE_PREPROCESS else text
    except Exception:
        clean = text

    if not clean.strip():
        return {"label": 0, "proba": 0.0, "clean": clean}

    proba = float(_PIPE.predict_proba([clean])[0, 1])
    label = int(proba >= BEST_THR)
    return {"label": label, "proba": proba, "clean": clean}

def predict_and_explain(raw_text: str) -> dict:
    """
    Melakukan prediksi teks dan mengembalikan detail koefisien fitur yang berpengaruh (Explainability).
    Berguna untuk menampilkan alasan di balik keputusan model kepada pengguna.
    
    Args:
        raw_text (str): Teks komentar mentah.
        
    Returns:
        dict: Dictionary lengkap berisi detail prediksi, probabilitas, dan daftar fitur (token)
              beserta kontribusinya (TF-IDF * Koefisien).
    """
    _lazy_load()
    text = (raw_text or "")
    try:
        clean = preprocess(text) if USE_PREPROCESS else text
    except Exception:
        clean = text

    if not clean.strip():
        return {
            "text": text,
            "clean": clean,
            "label": 0,
            "label_desc": "NON-JUDOL",
            "proba": 0.0,
            "proba_judol_pct": 0.0,
            "proba_non_pct": 100.0,
            "features": []
        }

    probs = _PIPE.predict_proba([clean])[0]  
    prediction = 1 if probs[1] >= BEST_THR else 0
    
    vect = None
    clf = None
    
    for name, step in _PIPE.named_steps.items():
        if "tfidf" in name.lower() or "vect" in name.lower():
            vect = step
        if "clf" in name.lower() or "svm" in name.lower() or "log" in name.lower() or "saga" in name.lower():
            clf = step
            
    if vect is None or clf is None:
        for name, step in _PIPE.named_steps.items():
            if hasattr(step, "transform") and hasattr(step, "get_feature_names_out") and vect is None:
                vect = step
            if hasattr(step, "coef_") and clf is None:
                clf = step

    active_features = []
    
    if vect and clf:
        try:
            text_tfidf = vect.transform([clean])
            
            feature_names = vect.get_feature_names_out()
            coefs = clf.coef_[0]
            
            row_indices = text_tfidf.nonzero()[1]
            
            for idx in row_indices:
                feat_name = feature_names[idx]
                tfidf_val = text_tfidf[0, idx]
                
                if idx < len(coefs):
                    coeff_val = coefs[idx]
                    contribution = tfidf_val * coeff_val
                    
                    if "char__" in feat_name:
                         continue

                    display_name = feat_name.replace("word__", "")

                    active_features.append({
                        "feature": display_name,
                        "tfidf": float(tfidf_val),
                        "coefficient": float(coeff_val),
                        "contribution": float(contribution)
                    })
            
            active_features.sort(key=lambda x: abs(x["contribution"]), reverse=True)
            
        except Exception as e:
            print(f"Error extracting features: {e}")
            pass

    return {
        "text": text,
        "clean": clean,
        "label": prediction,
        "label_desc": "JUDOL" if prediction == 1 else "NON-JUDOL",
        "proba_judol": float(probs[1]),
        "proba_non": float(probs[0]),
        "proba_judol_pct": float(probs[1]) * 100,
        "features": active_features
    }

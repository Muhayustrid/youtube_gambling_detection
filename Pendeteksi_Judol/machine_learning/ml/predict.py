import sys
sys.path.append(r'd:\Semester7\Skripsi\Project Judol Promotion Detection\Pendeteksi_Judol\machine_learning\ml')
import joblib
from scipy.sparse import hstack
from preprosess import preprosesing

# load artefak saat pertama kali
word_vec = joblib.load(r"d:\Semester7\Skripsi\Project Judol Promotion Detection\Pendeteksi_Judol\machine_learning\ml\tfidf_word.pkl")
char_vec = joblib.load(r"d:\Semester7\Skripsi\Project Judol Promotion Detection\Pendeteksi_Judol\machine_learning\ml\tfidf_char.pkl")
clf = joblib.load(r"d:\Semester7\Skripsi\Project Judol Promotion Detection\Pendeteksi_Judol\machine_learning\ml\model_lr.pkl")
BEST_THR = 0.39

def predict_comment(raw_text: str):
    clean = preprosesing(raw_text)
    if not clean.strip():
        return {"label": 0, "proba": 0.0, "clean": clean}

    Xw = word_vec.transform([clean])
    Xc = char_vec.transform([clean])
    X  = hstack([Xw, Xc])
    proba = clf.predict_proba(X)[0,1]
    label = int(proba >= BEST_THR)

    return {"label": label, "proba": float(proba), "clean": clean}

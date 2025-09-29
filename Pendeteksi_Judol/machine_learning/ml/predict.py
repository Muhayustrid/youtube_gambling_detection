import sys
sys.path.append(r'D:\Semester7\Skripsi\Project Judol Promotion Detection\youtube_gambling_detection\Pendeteksi_Judol\machine_learning\ml\joblib')
import joblib
from scipy.sparse import hstack
from .preprosess import preprosesing

# load artefak 
word_vec = joblib.load(r"D:\Semester7\Skripsi\Project Judol Promotion Detection\youtube_gambling_detection\Pendeteksi_Judol\machine_learning\ml\joblib\tfidf_word.pkl")
char_vec = joblib.load(r"D:\Semester7\Skripsi\Project Judol Promotion Detection\youtube_gambling_detection\Pendeteksi_Judol\machine_learning\ml\joblib\tfidf_char.pkl")
clf = joblib.load(r"D:\Semester7\Skripsi\Project Judol Promotion Detection\youtube_gambling_detection\Pendeteksi_Judol\machine_learning\ml\joblib\model_lr.pkl")
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

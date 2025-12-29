from __future__ import annotations
from pathlib import Path
from threading import Lock
import joblib

USE_PREPROCESS = True
BEST_THR = 0.50

_MODEL_PATH = Path(__file__).resolve().parent / "model" / "judol_pipeline_v4_saga.joblib"

_lock = Lock()
_PIPE = None

if USE_PREPROCESS:
    # from .preprosess import preprosesing
    from .preprocessing import preprocess as preprosesing

def _lazy_load():
    global _PIPE
    if _PIPE is not None:
        return
    with _lock:
        if _PIPE is None:
            blob = joblib.load(_MODEL_PATH)
            # ekspektasi: blob = {"pipeline": pipe, ...}
            _PIPE = blob["pipeline"]

def predict_comment(raw_text: str) -> dict:
    """Return dict {'label', 'proba', 'clean'}."""
    _lazy_load()
    text = (raw_text or "")
    try:
        clean = preprosesing(text) if USE_PREPROCESS else text
    except Exception:
        clean = text

    if not clean.strip():
        return {"label": 0, "proba": 0.0, "clean": clean}

    proba = float(_PIPE.predict_proba([clean])[0, 1])
    label = int(proba >= BEST_THR)
    return {"label": label, "proba": proba, "clean": clean}

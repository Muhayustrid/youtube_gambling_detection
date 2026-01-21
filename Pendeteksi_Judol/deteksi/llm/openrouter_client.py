import os
import requests
import json
from typing import Tuple, Optional, Dict, List

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.environ.get("OPENROUTER_API_KEY")

MODEL_FALLBACK_LIST: List[str] = [
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "liquid/lfm-2.5-1.2b-thinking:free",
    "arcee-ai/trinity-mini:free",
    "xiaomi/mimo-v2-flash:free",
    "tngtech/deepseek-r1t2-chimera:free",
    "amazon/nova-2-lite-v1:free",
    "mistralai/devstral-2512:free",
]

sort_name_model = {
    "arcee-ai/trinity-mini:free": "Trinity Mini",
    "nvidia/nemotron-3-nano-30b-a3b:free": "Nemotron",
    "xiaomi/mimo-v2-flash:free": "Xiaomi",
    "tngtech/deepseek-r1t2-chimera:free": "Deepseek",
    "amazon/nova-2-lite-v1:free": "Nova",
    "mistralai/devstral-2512:free": "Mistral",
    "liquid/lfm-2.5-1.2b-thinking:free": "LFM",
}

def call_openrouter_with_fallback(messages: list, timeout: int = 15) -> Tuple[Optional[str], Dict]:
    """
    Mencoba melakukan permintaan ke API OpenRouter menggunakan strategi fallback model.

    Fungsi ini akan mencoba satu per satu model yang ada dalam daftar `MODEL_FALLBACK_LIST`.
    Jika permintaan ke satu model gagal (karena timeout atau error koneksi), fungsi akan
    melanjutkan ke model berikutnya. Mengembalikan respons dari model pertama yang berhasil.

    Args:
        messages (list): Daftar pesan (list of dictionaries) yang akan dikirim ke LLM.
        timeout (int): Batas waktu tunggu dalam detik untuk setiap permintaan request. Default 15 detik.

    Returns:
        Tuple[Optional[str], Dict]: 
            - String respons dari LLM jika berhasil, atau None jika semua percobaan gagal.
            - Dictionary metadata yang berisi nama model yang digunakan atau informasi error.
    """
    last_error = None

    for model_name in MODEL_FALLBACK_LIST:
        print(f"[LLM] Mencoba model: {model_name}...")
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/muhayustrid/youtube_gambling_detection", 
        }
        
        body = {
            "model": model_name,
            "messages": messages,
        }
        
        try:
            r = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(body), timeout=timeout)
            r.raise_for_status()
            
            j = r.json()
            
            choice = j["choices"][0]["message"]
            content = choice.get("content", "")
            
            short_name = sort_name_model.get(model_name, "Unknown Model")
            
            print(f"[LLM] ✅ Berhasil dengan model: {model_name}")
            
            return content, {
                "model_used": short_name
            }
            
        except requests.exceptions.RequestException as exc:
            print(f"[LLM] ❌ Gagal dengan model {model_name}: {exc}")
            last_error = str(exc)
            continue

    print("[LLM] 🚨 Semua model gagal.")
    return None, {"error": f"All models failed. Last error: {last_error}"}
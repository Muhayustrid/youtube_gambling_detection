# openrouter_client.py
import os
import requests
import json
from typing import Tuple, Optional, Dict, List

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.environ.get("OPENROUTER_API_KEY")

# Daftar Model Fallback
MODEL_FALLBACK_LIST: List[str] = [
    "xiaomi/mimo-v2-flash:free",            # Model Utama
    "tngtech/deepseek-r1t2-chimera:free",  # Model Utama kedua
    "amazon/nova-2-lite-v1:free",          # Cadangan 1
    "mistralai/devstral-2512:free",         # Cadangan 2
    "nvidia/nemotron-3-nano-30b-a3b:free"  # Cadangan 3
]

# Mapping nama pendek untuk logging
sort_name_model = {
    "xiaomi/mimo-v2-flash:free": "Xiaomi",
    "tngtech/deepseek-r1t2-chimera:free": "Deepseek",
    "amazon/nova-2-lite-v1:free": "Nova",
    "mistralai/devstral-2512:free": "Mistral",
    "nvidia/nemotron-3-nano-30b-a3b:free": "Nemotron"
}

def call_openrouter_with_fallback(messages: list, timeout: int = 15) -> Tuple[Optional[str], Dict]:
    """
    Mencoba memanggil API OpenRouter dengan strategi fallback.
    Hanya mengembalikan konten dan nama model yang berhasil digunakan.
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
            
            # Ambil konten
            choice = j["choices"][0]["message"]
            content = choice.get("content", "")
            
            # Ambil nama pendek model
            short_name = sort_name_model.get(model_name, "Unknown Model")
            
            print(f"[LLM] ✅ Berhasil dengan model: {model_name}")
            
            # Return ringan: Konten + Metadata minimal
            return content, {
                "model_used": short_name
            }
            
        except requests.exceptions.RequestException as exc:
            print(f"[LLM] ❌ Gagal dengan model {model_name}: {exc}")
            last_error = str(exc)
            continue

    print("[LLM] 🚨 Semua model gagal.")
    return None, {"error": f"All models failed. Last error: {last_error}"}
# openrouter_client.py
import os
import requests
import json
from typing import Tuple, Optional, List

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.environ.get("OPENROUTER_API_KEY") 

def call_openrouter(messages: list, model: str = "tngtech/deepseek-r1t2-chimera:free", timeout: int = 15) -> Tuple[Optional[str], dict]:
    """Kembalikan (assistant_content, raw_response). Jika error, kembalikan (None, info)."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "extra_body": {"reasoning": {"enabled": True}}
    }
    try:
        r = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(body), timeout=timeout)
        r.raise_for_status()
        j = r.json()
        choice = j["choices"][0]["message"]
        content = choice.get("content")
        reasoning = choice.get("reasoning_details", {})
        # simpan log di DB/file 
        return content, {"raw": j, "reasoning": reasoning}
    except Exception as exc:
        return None, {"error": str(exc)}
    
MODEL_FALLBACK_LIST: List[str] = [
    "z-ai/glm-4.5-air:free",            # Model Utama
    "tngtech/deepseek-r1t2-chimera:free",  # Model Utama kedua
    "amazon/nova-2-lite-v1:free",          # Cadangan 1
    "mistralai/devstral-2512:free",         # Cadangan 2
    "nvidia/nemotron-3-nano-30b-a3b:free"  # Cadangan 3
]
sort_name_model = {
    "z-ai/glm-4.5-air:free": "GLM",            
    "tngtech/deepseek-r1t2-chimera:free":"Deepseek",  
    "amazon/nova-2-lite-v1:free":"Nova",         
    "mistralai/devstral-2512:free":"Misitral",         
    "nvidia/nemotron-3-nano-30b-a3b:free":"Nemotron"  
    }

def call_openrouter_with_fallback(messages: list, timeout: int = 15) -> Tuple[Optional[str], Dict]:
    """
    Mencoba memanggil API OpenRouter dengan beberapa model (fallback).
    Jika model utama gagal, fungsi akan otomatis mencoba model cadangan berikutnya.

    Args:
        messages (list): Daftar pesan untuk percakapan.
        timeout (int): Timeout untuk setiap permintaan dalam detik.

    Returns:
        Tuple[Optional[str], Dict]: 
        - Jika berhasil: (assistant_content, metadata seperti model yang digunakan).
        - Jika semua gagal: (None, info error).
    """
    last_error = None

    # Iterasi melalui setiap model dalam daftar fallback
    for model_name in MODEL_FALLBACK_LIST:
        print(f"[LLM] Mencoba model: {model_name}...") # Untuk logging di console
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model_name,
            "messages": messages,
            # "extra_body": {"reasoning": {"enabled": True}} 
        }
        
        try:
            # Lakukan permintaan POST ke API
            r = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(body), timeout=timeout)
            r.raise_for_status()  # Akan memunculkan error jika status bukan 2xx
            
            j = r.json()
            choice = j["choices"][0]["message"]
            content = choice.get("content")
            reasoning = choice.get("reasoning_details", {})
            
            sort_name = sort_name_model.get(model_name, model_name)
            # Jika berhasil, kembalikan hasil dan hentikan loop
            print(f"[LLM] ✅ Berhasil dengan model: {model_name}")
            return content, {
                "raw": j, 
                "reasoning": reasoning,
                "model_used": sort_name 
            }
            
        except requests.exceptions.RequestException as exc:
            # Jika gagal, catat errornya dan coba model berikutnya
            print(f"[LLM] ❌ Gagal dengan model {model_name}: {exc}")
            last_error = str(exc)
            continue # Lanjut ke model berikutnya dalam daftar

    # Jika semua model dalam daftar gagal
    print("[LLM] 🚨 Semua model gagal.")
    return None, {"error": f"All models failed. Last error: {last_error}"}

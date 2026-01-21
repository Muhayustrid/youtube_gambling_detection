import os
import json

from django.utils import timezone
from django.core.cache import cache
from ..llm.openrouter_client import call_openrouter_with_fallback
from django.conf import settings

BASE_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
LLM_LOG_DIR = os.path.join(BASE_APP_DIR, "llm_logs")
os.makedirs(LLM_LOG_DIR, exist_ok=True)
LLM_LOG_FILE = os.path.join(LLM_LOG_DIR, "llm_calls.jsonl")

CACHE_TTL = 60 * 10 

def _log_llm_call(prompt: str, response: str, meta: dict):
    """
    Mencatat pemanggilan LLM ke dalam file log JSONL.
    
    Args:
        prompt (str): Prompt input yang dikirim ke LLM.
        response (str): Respons teks dari LLM.
        meta (dict): Metadata pemanggilan (model, latency, dll).
    """
    entry = {
        "timestamp": timezone.now().isoformat(),
        "prompt": prompt,
        "response": response,
        "meta": meta,
    }
    with open(LLM_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def _clean_llm_response(text: str) -> str:
    """
    Membersihkan format markdown code block dari respons LLM.
    
    Args:
        text (str): Teks respons mentah dari LLM.
        
    Returns:
        str: Teks bersih tanpa wrapper markdown.
    """
    if not text:
        return ""
    
    if text.strip().startswith("```markdown"):
        last_code_block_end = text.rfind("```")
        if last_code_block_end != -1:
            text = text[len("```markdown"):last_code_block_end].strip()
        else:
            text = text[len("```markdown"):].strip()
    elif text.strip().startswith("```"):
        last_code_block_end = text.rfind("```")
        if last_code_block_end != -1:
            text = text[3:last_code_block_end].strip()
            
    return text

def generate_insight(url, limit, stats, results_sample_check=None):
    """
    Menghasilkan analisis insight menggunakan LLM berdasarkan statistik komentar.
    
    Args:
        url (str): URL sumber data.
        limit (int): Batas pengambilan data.
        stats (dict): Statistik hasil analisis komentar.
        results_sample_check (list, optional): Data sampel untuk pengecekan fallback.
        
    Returns:
        tuple: (insight_raw, insight_cleaned, meta)
    """
    cache_key = f"llm_insight::{url}::limit::{limit}"
    cached = cache.get(cache_key)
    
    if cached:
        return cached.get("insight"), cached.get("html"), cached.get("meta", {})

    prompt_text = (
    f"""
    Tugas: Analisis pola indikasi judi online dan validasi potensi salah deteksi (False Positive).
    
    DATA STATISTIK:
    - Total Komentar: {stats['total']}
    - Terdeteksi Spam Promosi Judi: {stats['judi_count']}
    - Terdeteksi Bersih: {stats['clean_count']}

    DATA INPUT:
    1. Keywords Spam Dominan: {stats['spam_keywords_str'] if stats['spam_keywords_str'] else "-"}
    2. Sampel Spam (Yakin): {stats['spam_samples_str'] if stats['spam_samples_str'] else "-"}
    3. Sampel Ragu/Ambigu (Perlu Cek): {stats['unsure_samples_str'] if stats['unsure_samples_str'] else "-"}

    ATURAN FORMATTING (STRICT):
    - DILARANG menggunakan kalimat pembuka.
    - Langsung mulai dengan bullet point (*).
    - Hapus kata sambung tidak perlu.

    TEMPLATE OUTPUT (Wajib 4 Poin):
    * **Pola Deteksi**: (Sebutkan keyword utama dan jika ada teknik penyamaran seperti spasi/simbol)
    * **Modus**: (Jelaskan taktiknya: janji maxwin, link di bio, atau spam massal)
    * **Analisis Ambigu**: (Cek 'Sampel Ragu'. JIKA isinya berita/edukasi/curhat kalah judi, tegaskan bahwa itu BUKAN promosi. JIKA kosong/promosi samar, tulis "-")
    * **Kesimpulan Risiko**: (Simpulkan tingkat keparahan: Rendah/Sedang/Tinggi berdasarkan dominasi spam)

    EXCEPTION (Jika data statistik 0 spam):
    "✅ **Aman:** Tidak ditemukan indikator promosi judi online. Interaksi didominasi diskusi relevan."
    """
)


    messages = [
        {"role": "system", "content": "Anda adalah ahli analisis keamanan digital berbahasa indonesia yang sedang menganalisis spam promosi judi online di komentar platform YouTube."},
        {"role": "user", "content": prompt_text}
    ]

    llm_insight = None
    llm_insight_html = None
    meta = {}

    content, meta = call_openrouter_with_fallback(messages)
    
    if content:
        llm_insight = content.strip()
        llm_insight_cleaned = _clean_llm_response(llm_insight)
        
        cache.set(cache_key, {
            "insight": llm_insight,
            "html": llm_insight_cleaned,
            "meta": meta
        }, CACHE_TTL)
        try:
            _log_llm_call(prompt_text, llm_insight, meta or {})
        except Exception:
            pass
    else:
        has_spam = stats['judi_count'] > 0
        if has_spam:
            total = stats['total'] if stats['total'] > 0 else 1
            ratio = (stats['judi_count'] / total) * 100
            
            risk_label = "TINGGI" if ratio > 20 else "SEDANG" if ratio > 5 else "RENDAH"
            
            insight_text = (
                f"* **Laporan Deteksi**: Ditemukan **{stats['judi_count']}** komentar promosi judi dari total {stats['total']} komentar ({ratio:.1f}%).\n"
                f"* **Tingkat Risiko**: **{risk_label}**. Sistem merekomendasikan pemeriksaan manual atau penghapusan pada komentar yang ditandai."
            )
        else:
            insight_text = (
                f"**Aman:** Tidak ditemukan indikator promosi judi online pada {stats['total']} komentar yang dianalisis."
            )
        
        llm_insight = insight_text
        llm_insight_cleaned = _clean_llm_response(insight_text)
        meta = {"model": "fallback-stat-only", "status": "ai_failed"}

    return llm_insight, llm_insight_cleaned, meta

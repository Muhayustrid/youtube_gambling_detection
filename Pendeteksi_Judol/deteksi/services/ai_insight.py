import os
import json
import markdown
from django.utils import timezone
from django.core.cache import cache
from ..llm.openrouter_client import call_openrouter_with_fallback
from django.conf import settings

# Setup Logging
# Parent directory of 'services' is 'deteksi'
BASE_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
LLM_LOG_DIR = os.path.join(BASE_APP_DIR, "llm_logs")
os.makedirs(LLM_LOG_DIR, exist_ok=True)
LLM_LOG_FILE = os.path.join(LLM_LOG_DIR, "llm_calls.jsonl")

CACHE_TTL = 60 * 10 

def _log_llm_call(prompt: str, response: str, meta: dict):
    entry = {
        "timestamp": timezone.now().isoformat(),
        "prompt": prompt,
        "response": response,
        "meta": meta,
    }
    with open(LLM_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def _format_llm_response(text: str) -> str:
    """
    Convert markdown to HTML 
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
            
    html = markdown.markdown(
        text,
        extensions=['tables', 'nl2br', 'sane_lists']
    )
    
    html = html.replace('<p><strong>', '<strong>')
    html = html.replace('</strong></p>', '</strong>')
    
    return html

def generate_insight(url, limit, stats, results_sample_check):
    """
    Generate insight using LLM based on statistics.
    results_sample_check: list of results to check if any spam exists (for fallback).
    """
    cache_key = f"llm_insight::{url}::limit::{limit}"
    cached = cache.get(cache_key)
    
    if cached:
        return cached.get("insight"), cached.get("html"), cached.get("meta", {})

    # Construct prompt
    prompt_text = (
    f"""
    Tugas: Ekstrak pola indikasi judi online dari data mentah di bawah.
    
    DATA STATISTIK:
    - Total Komentar: {stats['total']}
    - Terdeteksi Spam Promosi Judi Online: {stats['judi_count']}
    - Terdeteksi Clean: {stats['clean_count']})

    DATA INPUT:
    1. Keywords spam: {stats['spam_keywords_str'] if stats['spam_keywords_str'] else "-"}
    2. Keywords pasca preprocessing: {stats['clean_keywords_str'] if stats['clean_keywords_str'] else "-"}
    3. Sampel Spam: {stats['spam_samples_str'] if stats['spam_samples_str'] else "-"}
    4. Sampel Clean: {stats['clean_samples_str'] if stats['clean_samples_str'] else "-"}
    5. Sampel Ragu: {stats['unsure_samples_str'] if stats['unsure_samples_str'] else "-"}

    ATURAN FORMATTING (STRICT):
    - **DILARANG** menggunakan kalimat pembuka (Contoh: "Berdasarkan data...", "Berikut analisis...", "Halo user").
    - Output harus **DIMULAI LANGSUNG** dengan simbol bullet point (*).
    - Hapus semua kata sambung yang tidak perlu. Langsung ke inti fakta.

    TEMPLATE OUTPUT (Gunakan persis):
    * **Pola Deteksi**: (Jelaskan trigger kata kunci dan variasi penulisan unik/alay yang ditemukan)
    * **Modus**: (Jelaskan taktik persuasi, misal: janji maxwin, link di bio, manipulasi testimoni)
    * **Tingkat Risiko**: (Kesimpulan singkat: Rendah/Sedang/Tinggi dan alasannya)

    EXCEPTION (Jika data kosong/strip "-"):
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
        llm_insight_html = _format_llm_response(llm_insight)
        
        cache.set(cache_key, {
            "insight": llm_insight,
            "html": llm_insight_html,
            "meta": meta
        }, CACHE_TTL)
        try:
            _log_llm_call(prompt_text, llm_insight, meta or {})
        except Exception:
            pass
    else:
        # Fallback Logic
        has_spam = any(item["label"] == 1 for item in results_sample_check)
        if has_spam:
            top_kw_list = stats.get('top_keywords', [])
            keywords_str = ', '.join([w for w, _ in top_kw_list[:3]])
            
            insight_text = f"""## Ringkasan Analisis

                    ### Pola Dominan
                    - Mayoritas promosi mengandung: **{keywords_str}**
                    - Banyak pola obfuscation (angka/leet/spacing)
                    - Ada frasa yang mengarahkan ke link eksternal

                    ### Brand Judi biasanya
                    - Slot online, Gacor, Bonus, Deposit
                    - Togel, Pulauwin, Garuda Hoki, Totot
                    - Live casino

                    """
        else:
            insight_text = f"""## Hasil Analisis
            Tidak ada aktivitas spam promosi judi online yang terdeteksi pada komentar video ini. Semua komentar terlihat relevan dan bersih."""
        
        llm_insight = insight_text
        llm_insight_html = _format_llm_response(insight_text)

    return llm_insight, llm_insight_html, meta

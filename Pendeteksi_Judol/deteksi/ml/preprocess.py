import re
import unicodedata
import difflib
from typing import List, Optional
from unidecode import unidecode

# ==============================================================================
# KONFIGURASI & KONSTANTA
# ==============================================================================

# Regex Pattern
_RE_DASHES = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]")
_RE_APOS   = re.compile(r"[\u2018\u2019\u02BC]")
_RE_ZW     = re.compile(r"[\u200B-\u200F\uFEFF\u2060-\u2063]") 
_RE_URLS   = re.compile(r'https?://\S+|www\.\S+', re.I)
_RE_MENTIONS = re.compile(r'(?<![A-Za-z0-9_])@[a-zA-Z0-9_-]+')
_RE_BRACKETS = re.compile(r'[\[\]\{\}\(\)【［〔｢\]\}\)】］〕｣]')
_RE_TIMESTAMPS = re.compile(r"""\b(?:[01]?\d|2[0-3])\s*[:：;]\s*[0-5]\d(?:\s*[:：;]\s*[0-5]\d)?\b""", re.X)
_RE_AT_INFIX = re.compile(r'(?i)(?<=[a-z])@(?=[a-z])')
_RE_ALNUM_MIX = re.compile(r'(?i)(?:[a-z]+\d+|\d+[a-z]+)')

# Simbol Khusus
VS16 = "\uFE0F"
COEN = "\u20E3"
HARD_SEPARATORS = r"/|\\:;~_.,\-()\[\]{}<>=+\"'"
VOWELS = set("aiueo")

# Mapping Leet Speak (Angka ke Huruf)
LEET_MAP_TABLE = {
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', 
    '6': 'g', '5': 's', '@': 'a', '9': 'g'
}

# Mapping Kata Slang/Plesetan (Dapat disesuaikan)
SUBS = {
    # MAXWIN
    'maxw!n': 'maxwin', 'maxwinn': 'maxwin', 'm14xwin': 'maxwin', 'm4ksvin': 'maxwin',
    # SLOT
    '5lot': 'slot', 's1ot': 'slot', 'slott': 'slot', 'sloot': 'slot', 
    's|ot': 'slot', 'sl07': 'slot', 's!ot': 'slot', 'sgpin': 'spin',
    # GACOR
    'gacoor':'gacor', 'g4k0r':'gacor', 'ggacor':'gacor', '9acor':'gacor',
    # HOKI
    'hokii': 'hoki', 'hokl': 'hoki', 'h0kl':'hoki', 'garudahokl':'garudahoki',
    # UMUM
    'bette':'bet', 'wdw':'wd', 'w1d':'wd', 't0g3ll':'togel', 
    'pr0m':'promo', 'b0nuss':'bonus', '9aruda':'garuda', 
    'arwanatt':'arwanatoto', 't0to':'toto', 'm0na4d':'mona4d', 
    'jepe':'jp', 'jepey':'jp', 'jepee':'jp',
}

# Daftar Kata Kunci Domain Judi (Untuk fuzzy matching)
DOMAIN_WORDS = {
    "maxwin", "gacor", "slot", "spin", "garudahoki", "pulauwin", "hoki", "jp",
    "deposit", "depo", "wd", "jackpot", "togel", "casino", "promo", "bonus", 
    "bet", "withdraw", "rtp"
}

# Mapping Homoglyph
HOMO_MAP = {
    # Cyrillic
    "А": "A", "а": "a", "В": "B", "в": "b", "Е": "E", "е": "e", "К": "K", "к": "k", "М": "M", "Т": "T",
    "Х": "X", "х": "x", "О": "O", "о": "o", "Н": "H", "н": "h", "Р": "P", "р": "p", "С": "C", "с": "c",
    "У": "Y", "у": "y", "З": "Z", "з": "z", "Я": "R", "Ч": "4", "Ж": "X", "Ц": "LL", "і": "i", "ј": "j",
    "ѕ": "s", "ѡ": "w", "ә": "e", "б": "6", "г": "r", "д": "a", "и": "u", "й": "u", "л": "n", "м": "m",
    "п": "n", "т": "t", "ф": "o", "ц": "u", "ш": "w", "щ": "w", "ъ": "b", "ы": "bi", "ь": "b", "э": "e",
    "ю": "io", "я": "r", "ї": "i", "є": "e",

    # ARMENIAN LETTERS
    'Ա': 'U', 'ա': 'w', 'Բ': 'B', 'բ': 'b', 'Գ': '9', 'գ': 'q', 'Դ': 'N', 'դ': 'n', 'Ե': 'E', 'ե': 't',
    'Զ': 'Z', 'զ': 'q', 'Է': 'E', 'է': 't', 'Ը': 'P', 'ը': 'p', 'Թ': 'P', 'թ': 'p', 'Ժ': 'D', 'ժ': 'd',
    'Ի': 'H', 'ի': 'h', 'Լ': 'L', 'լ': 'l', 'Խ': 'X', 'խ': 'x', 'Ծ': 'G', 'ծ': 'd', 'Կ': 'Y', 'կ': 'k',
    'Հ': 'H', 'հ': 'h', 'Ձ': 'A', 'ձ': 'a', 'Ղ': 'N', 'ղ': 'n', 'Ճ': 'U', 'ճ': 'u', 'Մ': 'M', 'մ': 'u',
    'Յ': 'J', 'յ': 'j', 'Ն': 'U', 'ն': 'u', 'Շ': '2', 'շ': '2', 'Ո': 'N', 'ո': 'n', 'Չ': '4', 'չ': 'n',
    'Պ': 'M', 'պ': 'm', 'Ջ': '2', 'ջ': '2', 'Ռ': 'N', 'ռ': 'n', 'Ս': 'U', 'ս': 'u', 'Վ': '4', 'վ': '4',
    'Տ': 'T', 'տ': 't', 'Ր': 'R', 'ր': 'r', 'Ց': 'G', 'ց': 'g', 'Ւ': 'L', 'ւ': 'L', 'Փ': 'P', 'փ': 'p',
    'Ք': 'P', 'ք': 'p', 'Օ': 'O', 'օ': 'o', 'Ֆ': 'F', 'ֆ': 'f',

    # GREEK
    "η": "n", "Η": "H", "σ": "o", "ς": "o", "Σ": "S", "ο": "o", "Ο": "O", "ρ": "p", "Ρ": "P", "κ": "k",
    "Κ": "K", "ν": "v", "Ν": "N", "τ": "t", "Τ": "T", "χ": "x", "Χ": "X", "μ": "m", "Μ": "M", "λ": "a",
    "Λ": "a", "α": "a", "β": "b", "γ": "y", "δ": "d", "ε": "e", "ζ": "z", "θ": "0", "ι": "i", "ξ": "e",
    "π": "n", "υ": "u", "φ": "o", "ψ": "w", "ω": "w", "ϲ": "c", "ϵ": "e", "Ϛ": "s", "ϫ": "x", "Α": "A",
    "Β": "B", "Δ": "A", "Γ": "r", "Ω": "W", "Ϝ": "F",

    # CJK UNIFIED & KANJI
    "丅": "t", "丄": "t", "丫": "y", "厶": "a", "乇": "e", "乚": "l", "囗": "o", "工": "i", "尺": "r", "丁": "t",
    "十": "t", "一": "-", "二": "=", "三": "e", "口": "o", "人": "y", "入": "y", "X": "x", "匕": "t", "マ": "v",
    "ム": "a", "カ": "n", "丨": "I", "亅": "J", "ロ": "O", "回": "O", "曰": "O", "乂": "X", "⻌": "Z", "八": "a",
    "〇": "0",

    # SMALL CAPITALS
    'ᴀ': 'a', 'ʙ': 'b', 'ᴄ': 'c', 'ᴅ': 'd', 'ᴇ': 'e', 'ғ': 'f', 'ɢ': 'g', 'ʜ': 'h', 'ɪ': 'i', 'ᴊ': 'j', 'ᴋ': 'k',
    'ʟ': 'l', 'ᴍ': 'm', 'ɴ': 'n', 'ᴏ': 'o', 'ᴘ': 'p', 'ꞯ': 'q', 'ʀ': 'r', 'ꜱ': 's', 'ᴛ': 't', 'ᴜ': 'u', 'ᴠ': 'v',
    'ᴡ': 'w', 'x': 'x', 'ʏ': 'y', 'ᴢ': 'z',

    # varian visual angka/huruf
    '𝟶': '0', '𝟷': '1', '𝟸': '2', '𝟹': '3', '𝟺': '4', '𝟻': '5', '𝟼': '6', '𝟽': '7', '𝟾': '8', '𝟿': '9',
    '𝟢': '0', '𝟣': '1', '𝟤': '2', '𝟹': '3', '𝟺': '4', '𝟻': '5', '𝟼': '6', '𝟽': '7', '𝟾': '8', '𝟿': '9',

    # CANADIAN SYLLABICS
    'ᗩ': 'a', 'ᐯ': 'v', 'ᐠ': 'v', 'ᑕ': 'c', 'ᑐ': 'j', 'ᗷ': 'b', 'ᑌ': 'u', 'ᑎ': 'n', 'ᑘ': 'u', 'ᑭ': 'p', 'ᑯ': 'd',
    'ᑲ': 'b', 'ᑫ': 'q', 'ᕒ': 'p', 'ᙀ': 'q', 'ᒪ': 'l',  'ᒧ': 'j', 'ᒥ': 'r', 'ᗰ': 'm', 'ᗯ': 'w', 'ᙡ': 'w', 'ᔕ': 's',
    'ᔅ': 'z', '᙭': 'x', 'ᔦ': 'y', 'ᕼ': 'h', 'ᖇ':'r',

    # --- MATHEMATICAL SCRIPT (HURUF KURSIF) ---
    '𝒜': 'A', '𝒞': 'C', '𝒟': 'D', '𝒢': 'G', '𝒥': 'J', '𝒦': 'K', '𝒩': 'N', '𝒪': 'O', '𝒫': 'P', '𝒬': 'Q',
    '𝒮': 'S', '𝒯': 'T', '𝒰': 'U', '𝒱': 'V', '𝒲': 'W','𝒳': 'X', '𝒴': 'Y', '𝒵': 'Z',
    'ℬ': 'B', 'ℰ': 'E', 'ℱ': 'F', 'ℋ': 'H', 'ℐ': 'I', 'ℒ': 'L', 'ℳ': 'M', 'ℛ': 'R', '𝒶': 'a',
    '𝒷': 'b', '𝒸': 'c', '𝒹': 'd', '𝒻': 'f', '𝒽': 'h', '𝒾': 'i', '𝒿': 'j', '𝓀': 'k', '𝓁': 'l', '𝓂': 'm', '𝓃': 'n', '𝓅': 'p', '𝓆': 'q',
    '𝓇': 'r', '𝓈': 's', '𝓉': 't', '𝓊': 'u', '𝓋': 'v', '𝓌': 'w', '𝓍': 'x', '𝓎': 'y', '𝓏': 'z', 'ℯ': 'e', 'ℊ': 'g', 'ℴ': 'o',

    # --- LATIN EXTENDED (HOOKS, BARS, STROKES) ---
    'Ɦ': 'H', 'ƙ': 'k', 'ƣ': 'g', 'ʞ': 'k', 'Ħ': 'H', 'ħ': 'h', 'Ɨ': 'I', 'ɨ': 'i', 'ł': 'l', 'Ɵ': 'O', 'Ɱ': 'M',
    'Ⱡ': 'L', 'Ⱨ': 'H', 'Ɽ': 'R', 'Ꜹ': 'A',

    # Emoji
    # '🏵':'o'


}

# ==============================================================================
# 1. EMOJI HANDLING
# ==============================================================================

def remove_variation_selectors(s: str) -> str:
    """Menghapus karakter variation selector emoji."""
    return s.replace(COEN, "").replace(VS16, "")

def _emoji_digit_word_to_int(name: str) -> Optional[int]:
    """Mengubah nama digit emoji (e.g., 'DIGIT NINE') menjadi integer."""
    words_to_num = {
        "ZERO": 0, "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4,
        "FIVE": 5, "SIX": 6, "SEVEN": 7, "EIGHT": 8, "NINE": 9
    }
    parts = name.split()
    for i in range(len(parts)-1):
        if parts[i] == "DIGIT":
            return words_to_num.get(parts[i+1])
    return None

def emoji_letter_digit_to_ascii(s: str) -> str:
    """Mengubah emoji huruf/angka (regional indicator, squared, keycap) menjadi ASCII."""
    out = []
    for ch in s:
        try:
            name = unicodedata.name(ch)
        except ValueError:
            out.append(ch)
            continue

        if "DAGGER" in name:
            out.append("t")
        elif "REGIONAL INDICATOR SYMBOL LETTER" in name:
            out.append(name.split()[-1])
        elif "LATIN CAPITAL LETTER" in name and any(x in name for x in ["SQUARED", "CIRCLED", "NEGATIVE CIRCLED", "BUTTON"]):
            out.append(name.split()[-1])
        elif "KEYCAP" in name and "DIGIT" in name:
            n = _emoji_digit_word_to_int(name)
            out.append(str(n) if n is not None else ch)
        else:
            # Cek angka enclosed/circled biasa
            try:
                val = unicodedata.numeric(ch)
                if float(val).is_integer() and 0 <= int(val) <= 9:
                    out.append(str(int(val)))
                    continue
            except Exception:
                pass
            out.append(ch)
    return "".join(out)

def normalize_emoji_text(s: str) -> str:
    """Pipeline khusus normalisasi emoji."""
    s = remove_variation_selectors(s)
    s = emoji_letter_digit_to_ascii(s)
    return s

# ==============================================================================
# 2. UNICODE & TEXT NORMALIZATION
# ==============================================================================

def normalize_unicode(text: str) -> str:
    """Normalisasi unicode ke bentuk NFKC."""
    return unicodedata.normalize("NFKC", text)

def normalize_punct(text: str) -> str:
    """Normalisasi tanda baca seperti dash, apostrophe, dan zero width char."""
    text = _RE_DASHES.sub("-", text)
    text = _RE_APOS.sub("'", text)
    text = _RE_ZW.sub("", text)
    return text

def strip_combining_marks(text: str) -> str:
    """Menghapus tanda aksen/diakritik."""
    d = unicodedata.normalize("NFKD", text)
    f = "".join(ch for ch in d if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFKC", f)

def fold_homoglyphs(text: str) -> str:
    """Mengubah karakter homoglyph (mirip bentuk) menjadi karakter ASCII standar."""
    return "".join(HOMO_MAP.get(ch, ch) for ch in text)

def strip_symbol_chars(text: str) -> str:
    """Menghapus karakter kategori Symbol/Other (selain huruf/angka yang valid)."""
    out = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith(('S', 'C')): # Symbol, Control
            continue
        out.append(ch)
    return "".join(out)

def safe_unidecode(text: str) -> str:
    """Mengubah karakter non-ASCII menjadi ASCII terdekat dengan aman."""
    out = []
    for ch in text:
        out.append(unidecode(ch) if ch.isalpha() or ch.isdigit() else ch)
    return "".join(out)

# ==============================================================================
# 3. CLEANING & REMOVAL
# ==============================================================================

def remove_urls_mentions_hashtags(text: str) -> str:
    """Menghapus URL dan Mention (@user)."""
    text = _RE_URLS.sub(" ", text)
    text = _RE_MENTIONS.sub(" ", text)
    return text

def remove_bracket(text: str) -> str:
    """Menghapus segala jenis tanda kurung."""
    return _RE_BRACKETS.sub("", text)

def remove_timestamps(s: str) -> str:
    """Menghapus penanda waktu (misal: 12:30)."""
    return _RE_TIMESTAMPS.sub(" ", s)

def handle_intraword_symbols(text: str) -> str:
    """
    Menangani simbol di tengah kata. 
    Mengubah separator keras menjadi spasi, menghapus simbol obfuscation.
    """
    # hard separator → space
    text = re.sub(rf"[{HARD_SEPARATORS}]+", " ", text)
    # obfuscation intraword → remove (contoh: s.l.o.t -> slot)
    text = re.sub(r"(?<=\w)[^\w\s]+(?=\w)", "", text)
    # other symbols → space
    text = re.sub(r"[^\w\s]+", " ", text)
    return text.strip()

def keep_alnum_and_space(text: str) -> str:
    """Whitelist: Hanya menyisakan huruf, angka, spasi, dan @!$%."""
    return re.sub(r"[^0-9a-zA-Z@!\$%]+", " ", text)

def squeeze_spaces(text: str) -> str:
    """Mengubah spasi berlebih menjadi satu spasi."""
    return re.sub(r"\s+", " ", text).strip()

# ==============================================================================
# 4. TOKEN RECONSTRUCTION
# ==============================================================================

def rejoin_split_letters(tokens: List[str]) -> List[str]:
    """
    Menggabungkan huruf yang terpisah spasi (obfuscation).
    Contoh: ['p', 'u', 'l', 'a', 'u'] -> ['pulau']
    """
    out, i, n = [], 0, len(tokens)
    while i < n:
        j, letters = i, []
        # Gabungkan huruf terpisah
        while j < n and re.fullmatch(r'[A-Za-z]', tokens[j]):
            letters.append(tokens[j].lower())
            j += 1
        
        if len(letters) >= 3:
            word = ''.join(letters)
            # Cek jika diikuti digit 
            k, digits = j, []
            while k < n and re.fullmatch(r'\d+', tokens[k]):
                digits.append(tokens[k]); k += 1
            if digits:
                word += ''.join(digits)
                j = k
            
            # Validasi panjang kata & vokal
            if any(ch in VOWELS for ch in word) and 3 <= len(word) <= 24:
                out.append(word)
                i = j
                continue

        # Blok digit murni digabungkan
        if re.fullmatch(r'\d+', tokens[i]):
            k, digits = i, []
            while k < n and re.fullmatch(r'\d+', tokens[k]):
                digits.append(tokens[k]); k += 1
            digits_str = ''.join(digits)
            out.append(digits_str)
            i = k
            continue

        out.append(tokens[i])
        i += 1
    return out

# ==============================================================================
# 5. DOMAIN CORRECTION (PLESETAN & LEET)
# ==============================================================================

def map_chars(tok: str) -> str:
    """Mengubah leet speak (angka jadi huruf) kecuali untuk pola tertentu (4d)."""
    t = tok
    if t.lower().endswith('4d'):
        return t

    # Ganti @ di tengah kata
    t = _RE_AT_INFIX.sub('a', t)

    out = []
    n, i = len(t), 0
    while i < n:
        ch = t[i]
        if ch.isdigit():
            j = i + 1
            while j < n and t[j].isdigit():
                j += 1
            run_len = j - i
            # Jika angka berurutan 
            if run_len >= 2:
                out.append(t[i:j])
            else:
                # 1 digit → petakan jadi huruf
                out.append(LEET_MAP_TABLE.get(ch, ch))
            i = j
            continue
        out.append(LEET_MAP_TABLE.get(ch, ch))
        i += 1
    return ''.join(out)

def fix_infix_digits_with_domain(tok: str, domain=DOMAIN_WORDS, thr: float = 0.80) -> str:
    """Memperbaiki kata yang tersisip angka menggunakan fuzzy matching ke domain words."""
    t = tok.lower()
    if not re.search(r'[a-z]\d+[a-z]', t):
        return tok
        
    letters_only = re.sub(r'[^a-z]', '', t)
    if len(letters_only) < 3:
        return tok
        
    best, best_ratio = None, 0.0
    for cand in domain:
        r = difflib.SequenceMatcher(None, letters_only, cand).ratio()
        if r > best_ratio:
            best, best_ratio = cand, r
            
    if best and best_ratio >= thr:
        # Cek kesesuaian awal/akhir huruf
        if letters_only[0] == best[0] or letters_only[-2:] == best[-2:]:
            return best
    return tok

def squeeze_repeats(token: str, max_repeat: int = 2) -> str:
    """Mengurangi karakter berulang berlebihan (misal: 'gacorrr' -> 'gacorr')."""
    out, cnt, prev = [], 0, ''
    for ch in token:
        if ch == prev:
            cnt += 1
            if cnt <= max_repeat or ch.isdigit():
                out.append(ch)
        else:
            prev = ch
            cnt = 1
            out.append(ch)
    return ''.join(out)

def normalize_plesetan(tokens: List[str]) -> List[str]:
    """Fungsi utama normalisasi kata plesetan/alay."""
    out = []
    for t in tokens:
        t = t.lower()
        
        # Jika murni angka, biarkan
        if t.isdigit():
            out.append(t)
            continue

        # Cek kamus substitusi langsung
        if t in SUBS:
            out.append(SUBS[t])
            continue

        # Jika campuran alnum valid (misal user ID), biarkan
        if _RE_ALNUM_MIX.fullmatch(t):
            out.append(t)
            continue
            
        # Proses cleaning mendalam
        t = map_chars(t)               
        t = SUBS.get(t, t)            
        t = squeeze_repeats(t)        
        t = fix_infix_digits_with_domain(t)
        t = SUBS.get(t, t)             
        
        out.append(t)
    return out

# ==============================================================================
# 6. PIPELINE UTAMA
# ==============================================================================

def preprocess(text: str) -> str:
    """
    Fungsi utama preprocessing teks deteksi judi online.
    Input: Raw string komentar YouTube.
    Output: String bersih yang siap untuk vektorisasi.
    """
    if not isinstance(text, str) or not text:
        return ""

    # 1. Normalisasi Karakter & Simbol
    text = normalize_emoji_text(text)
    text = normalize_unicode(text)
    text = strip_combining_marks(text)
    text = fold_homoglyphs(text)       
    text = normalize_punct(text)
    
    # 2. Cleaning Konten Tidak Relevan
    text = remove_urls_mentions_hashtags(text)
    text = remove_timestamps(text)
    text = remove_bracket(text)
    
    # 3. Penanganan Simbol dalam Kata & Whitespace
    text = handle_intraword_symbols(text)
    text = strip_symbol_chars(text)
    text = safe_unidecode(text)
    text = text.lower()
    
    # 4. Final Cleaning sebelum Tokenisasi
    text = keep_alnum_and_space(text)
    text = squeeze_spaces(text)

    # 5. Operasi Level Token
    tokens = text.split()
    tokens = rejoin_split_letters(tokens) 
    tokens = normalize_plesetan(tokens)   

    # 6. Rejoin
    final_text = " ".join(tokens)
    return final_text
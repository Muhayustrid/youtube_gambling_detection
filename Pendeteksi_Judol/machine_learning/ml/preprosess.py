import re, unicodedata
"""## 1.   Konversi emoji ke huruf normal, konversi karakter dan casefolding"""

VS16 = "\uFE0F"

def remove_variation_selectors(s: str) -> str:
    return s.replace(VS16, "")

def emoji_letter_digit_to_ascii(s: str) -> str:
    out = []
    for ch in s:
        try:
            name = unicodedata.name(ch)
        except ValueError:
            out.append(ch); continue

        # Regional indicator 🇦..🇿
        if "REGIONAL INDICATOR SYMBOL LETTER" in name:
            out.append(name.split()[-1]); continue

        # SQUARED / CIRCLED / NEGATIVE CIRCLED letters
        if "LATIN CAPITAL LETTER" in name and (
            "SQUARED" in name or "CIRCLED" in name or "NEGATIVE CIRCLED" in name or name.endswith("BUTTON")
        ):
            out.append(name.split()[-1]); continue

        # Keycap digits 0️⃣..9️⃣
        if "KEYCAP" in name and "DIGIT" in name:
            out.append(name.split()[-1]); continue

        # Enclosed/circled numbers ①②…❿, ⓿…
        if "DIGIT" in name and len(ch) == 1:
            m = re.search(r'\b([0-9])\b', name)
            if m:
                out.append(m.group(1)); continue

        out.append(ch)
    return "".join(out)

def normalize_emoji_text(s: str) -> str:
    s = remove_variation_selectors(s)
    s = emoji_letter_digit_to_ascii(s)
    return s


def normalize_unicode(text):
    return unicodedata.normalize("NFKC", text)


def to_lower(text: str) -> str:
    return text.lower()


def norm_char_casfold(text: str) ->str:
  text = normalize_emoji_text(text)
  text = normalize_unicode(text)
  text = to_lower(text)
  return text


"""## 2. Remove noise"""

import re

_TS = re.compile(
    r"""\b
    (?:[01]?\d|2[0-3])      
    \s*[:：]\s*
    [0-5]\d                 
    (?:\s*[:：]\s*[0-5]\d)? 
    \b
    """,
    re.X,
)

def remove_timestamps(s: str) -> str:
    s = _TS.sub(" ", s)
    s = re.sub(r"\b(?:[0-5]?\d)\s+(?:[0-5]?\d)\b", " ", s)
    return s


def remove_urls_mentions_hashtags(text: str) -> str:
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)
    text = re.sub(r'@\w+', ' ', text)
    text = re.sub(r'#\w+', ' ', text)
    return text


def strip_combining_marks(text: str) -> str:
    decomposed = unicodedata.normalize('NFKD', text)
    filtered = ''.join(ch for ch in decomposed if unicodedata.category(ch) != 'Mn')
    return unicodedata.normalize('NFKC', filtered)


def keep_alnum_and_space(text: str) -> str:
    text = re.sub(r'[^0-9a-zA-Z]+', ' ', text)
    return text


def squeeze_spaces(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

def remove_noise(text: str) -> str:
    text = remove_timestamps(text)
    text = remove_urls_mentions_hashtags(text)
    text = strip_combining_marks(text)
    text = keep_alnum_and_space(text)
    text = squeeze_spaces(text)
    return text


"""## Langkah 3: Normalisasi Plesetan & Rejoin"""

def tokenize(text:str) ->str:
  return text.split()

VOWELS = set("aiueo")

def rejoin_split_letters(text: list[str]) -> list[str]:
    out = []
    i = 0
    while i < len(text):
        j = i
        letters = []
        while j < len(text) and re.fullmatch(r'[a-zA-Z]', text[j]):
            letters.append(text[j].lower()); j += 1

        if len(letters) >= 3:
            word = ''.join(letters)
            k = j
            digits = []

            while k < len(text) and re.fullmatch(r'\d+', text[k]):
                digits.append(text[k]); k += 1
            if digits:
                word += ''.join(digits); j = k

            if any(ch in VOWELS for ch in word) and 3 <= len(word) <= 12:
                if out and re.fullmatch(r'[a-z]+', out[-1]):
                    out[-1] = out[-1] + word
                else:
                    out.append(word)
                i = j
                continue
        out.append(text[i]); i += 1
    return out


SEP = r'[@!\$\-\._·]'

def merge_digit_or_symbol_between_letters(tokens):
    """
    Gabungkan pola:
      huruf + (digit|SEP) + huruf(1–2) [+ opsional 1 huruf]
    Contoh:
      ['h','0','kl']      -> ['h0kl']
      ['g','@','ruda']    -> ['g@ruda']
      ['m','1','4','x','win'] -> ['m14xwin'] (kalau sudah kepisah per char)
    """
    out, i = [], 0
    while i < len(tokens):
        if i+2 < len(tokens):
            a, b, c = tokens[i], tokens[i+1], tokens[i+2]
            if re.fullmatch(r'[a-zA-Z]+', a) and (b.isdigit() or re.fullmatch(SEP, b)) and re.fullmatch(r'[a-zA-Z]{1,2}', c):
                merged = a.lower() + b + c.lower()
                i += 3
                if i < len(tokens) and re.fullmatch(r'[a-zA-Z]', tokens[i]):
                    merged += tokens[i].lower(); i += 1
                out.append(merged)
                continue
        out.append(tokens[i].lower()); i += 1
    return out


def merge_word_digit_suffix(tokens, min_word_len=4, min_digit_len=2, max_digit_len=4):
    out = []
    i = 0
    n = len(tokens)
    while i < n:
        t = tokens[i].lower()
        if (i + 1 < n
            and t.isalpha()
            and len(t) >= min_word_len
            and tokens[i+1].isdigit()
            and min_digit_len <= len(tokens[i+1]) <= max_digit_len):
            out.append(t + tokens[i+1])
            i += 2
            continue
        out.append(tokens[i].lower())
        i += 1
    return out



PROMO_CUES = {
    "slot","gacor","maxwin","depo","deposit","wd","jackpot",
    "togel","casino","bonus","spin","bet","jp"
}

_RE_ALNUM_MIX   = re.compile(r'(?i)(?:[a-z]+\d+|\d+[a-z]+)')
_RE_REP3_DIGITS = re.compile(r'^(\d)\1{2,}$')
_RE_REP2_DIGITS = re.compile(r'^(\d)\1$')

def _has_promo_near(tokens: list[str], idx: int, window: int = 2) -> bool:
    start = max(0, idx - window)
    end   = min(len(tokens), idx + window + 1)
    for j in range(start, end):
        if j == idx:
            continue
        tj = tokens[j].lower()
        if tj in PROMO_CUES:
            return True
        if _RE_ALNUM_MIX.search(tj): 
            return True
    return False

def filter_numbers_dynamic(tokens: list[str], replace_with_num: bool = False) -> list[str]:
    out = []
    for i, t in enumerate(tokens):
        tok = t.lower()

        # 1) Campur huruf+angka (pulau777, miaw4d, alexis17, istanabet17) -> keep
        if _RE_ALNUM_MIX.fullmatch(tok):
            out.append(tok)
            continue

        # 2) Non-digit -> keep (JANGAN dibuang)
        if not tok.isdigit():
            out.append(tok)
            continue

        # 3) Pure digit
        # 3a) phone-like (panjang) -> keep
        if len(tok) >= 8:
            out.append(tok); continue

        # 3b) repeated-digit >=3 (777/888/666) -> keep
        if _RE_REP3_DIGITS.fullmatch(tok):
            out.append(tok); continue

        # 3c) repeated-digit 2 (88/66) -> keep HANYA jika ada promo cue di sekitar
        if _RE_REP2_DIGITS.fullmatch(tok) and _has_promo_near(tokens, i):
            out.append(tok); continue

        # 3d) ada promo cue di sekitar -> keep (angka likely relevan)
        if _has_promo_near(tokens, i):
            out.append(tok); continue

        # 3e) selain itu: drop atau tandai
        if replace_with_num:
            out.append("<NUM>")
        # else: skip (hapus angka lepas)

    return out


LEET_MAP = str.maketrans({'0':'o','1':'i','3':'e','4':'a','6':'g','5':'s','@':'a'})

LEET_EXCEPTIONS = {"4d","2d","3d","24d","12d"}

SUBS = {
    # MAXWIN
    'm4xwin': 'maxwin', 'm@xwin':'maxwin', 'm4xw1n':'maxwin',
    'maxw!n':'maxwin', 'maxwinn':'maxwin',
    'm14xwin':'maxwin',
    'm4ksvin':'maxwin',

    # SLOT
    'sl0t':'slot','s1ot':'slot','slott':'slot','sloot':'slot',
    's|ot':'slot','sl07':'slot',
    's6pin':'spin',

    # GACOR
    'g4cor':'gacor','g@c0r':'gacor','gacoor':'gacor',
    'g4k0r':'gacor','gac0r':'gacor','g4c0r':'gacor',
    'g64cor':'gacor',

    # HOKI
    'hokii':'hoki','h0ki':'hoki','hokl':'hoki','h0kl':'hoki',
    'h0 kl':'hoki', 'ho k1':'hoki',

    # LAIN-LAIN
    'b3t':'bet','bette':'bet',
    'd3po':'depo','dep0':'depo','d3posit':'deposit',
    'wdw':'wd','w1d':'wd',
    'c4sin0':'casino',
    'jackp0t':'jackpot','j4ckp0t':'jackpot',
    't0g3l':'togel','t0g3ll':'togel',
    'pr0m0':'promo','pr0m':'promo',
    'ref3rral':'referral','ref3r':'refer',
    'b0nus':'bonus','b0nuss':'bonus',
    'g@ruda':'garudahoki', 'garudahokl':'garudahoki'
}
DOMAIN_WORDS = {
    "maxwin","gacor","slot","spin","garudahoki", "pulau", "hoki",
    "deposit","depo","wd","jackpot","togel","casino","promo","bonus","bet"
}

EXCEPT_SUFFIX_RE = re.compile(r'(?:2|3|4)d$')

def should_map_leet(tok: str) -> bool:
    t = tok.lower()
    if t.isdigit():
        return False
    if re.fullmatch(r'[a-z]+\d+', t):
        return False
    if EXCEPT_SUFFIX_RE.search(t):
        return False
    return bool(re.search(r'[a-z]\d+[a-z]', t))

def map_chars(tok: str) -> str:
    return tok.translate(LEET_MAP) if should_map_leet(tok) else tok

import difflib

def fix_infix_digits_with_domain(tok: str, domain=DOMAIN_WORDS, thr=0.80) -> str:
    t = tok.lower()
    if not re.search(r'[a-z]\d+[a-z]', t):
        return tok
    # buang non-huruf untuk bandingkan bentuk dasarnya
    letters_only = re.sub(r'[^a-z]', '', t)
    if len(letters_only) < 3:
        return tok
    # pilih kandidat domain terbaik
    best, best_ratio = None, 0.0
    for cand in domain:
        r = difflib.SequenceMatcher(None, letters_only, cand).ratio()
        if r > best_ratio:
            best, best_ratio = cand, r
    # ekstra cek prefix/suffix agar tidak ngawur
    if best and best_ratio >= thr:
        # butuh sedikit jangkar: minimal prefix 1 huruf atau suffix 2 huruf cocok
        if letters_only[0] == best[0] or letters_only[-2:] == best[-2:]:
            return best
    return tok

def squeeze_repeats(token: str, max_repeat: int = 1) -> str:
    out, cnt, prev = [], 0, ''
    for ch in token:
        if ch == prev:
            cnt += 1
            max_repeat = 2 if ch == 'g' else 1
            if ch.isdigit() or cnt <= max_repeat:
                out.append(ch)
        else:
            prev = ch; cnt = 1; out.append(ch)
    return ''.join(out)

def normalize_plesetan(tokens: list[str]) -> list[str]:
    out = []
    for t in tokens:
        t0 = t.lower()
        # 1) SUBS cepat
        t1 = SUBS.get(t0, t0)
        # 2) Domain fix untuk digit di tengah (heuristik dinamis)
        t2 = fix_infix_digits_with_domain(t1)
        # 3) Leet-map (aman)—tidak sentuh ...4d / suffix digit
        t3 = map_chars(t2)
        # 4) Squeeze huruf berulang
        t4 = squeeze_repeats(t3, max_repeat=1)
        # 5) SUBS lagi untuk hasil pasca-mapping/squeeze
        t5 = SUBS.get(t4, t4)
        out.append(t5)
    return out


def load_lexicon(path_txt: str) -> set[str]:
    # file KBBI format satu kata per baris
    lex = set()
    with open(path_txt, "r", encoding="utf-8") as f:
        for line in f:
            w = line.strip().lower()
            if w and w.isalpha():
                lex.add(w)
    return lex

LETTER_CHUNK_RE = re.compile(r'^[a-zA-Z]{1,2}$')

def stitch_by_lexicon(tokens: list[str],
                      lexicon: set[str],
                      domain: set[str] = DOMAIN_WORDS,
                      min_len: int = 3,
                      max_len: int = 12) -> list[str]:
    """
    Susun ulang run token 1–2 huruf menjadi kata2 sesuai kamus (lexicon ∪ domain),
    greedy dari kiri (longest valid). Jika gagal → fallback biarkan as-is.
    """
    LEX = lexicon | set(domain)
    out = []
    i, n = 0, len(tokens)

    def is_chunk(t): return bool(LETTER_CHUNK_RE.fullmatch(t))

    while i < n:
        if not is_chunk(tokens[i]):
            out.append(tokens[i]); i += 1; continue

        # Kumpulkan seluruh run 1–2 huruf
        parts = []
        j = i
        while j < n and is_chunk(tokens[j]):
            parts.append(tokens[j].lower())
            j += 1

        # Greedy segmentation: bangun kata terpanjang yang valid, berulang
        k = 0
        changed = False
        while k < len(parts):
            best_word = None
            best_end = k
            cur = ""
            # perpanjang selama tidak lewat max_len
            for t in range(k, len(parts)):
                if len(cur) + len(parts[t]) > max_len:
                    break
                cur += parts[t]
                if len(cur) >= min_len and cur in LEX:
                    best_word, best_end = cur, t + 1
            if best_word is not None:
                out.append(best_word)
                k = best_end
                changed = True
            else:
                # tidak ada match → keluarkan part mentah & geser 1
                out.append(parts[k])
                k += 1

        i = j

    return out


def rejoin_norm_plesetan(text: str) -> list[str]:
    lexicon = load_lexicon("machine_learning/ml/asset/Kumpulan_Kata_Indonesia.txt")
    toks = tokenize(text)                       
    toks = rejoin_split_letters(toks)
    toks = stitch_by_lexicon(toks, lexicon, DOMAIN_WORDS)         
    toks = merge_digit_or_symbol_between_letters(toks)     
    toks = merge_word_digit_suffix(toks)
    toks = filter_numbers_dynamic(toks, replace_with_num=False)
    toks = normalize_plesetan(toks)             
    return toks


"""## 4 Langkah hapus stopword dan Steming"""

from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
#objek
factory = StopWordRemoverFactory()
stopwords = factory.get_stop_words()

def remove_stopwords(tokens: list[str]) -> list[str]:
    return [t for t in tokens if t not in stopwords]

# pip install Sastrawi
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

_factory = StemmerFactory()
_stemmer = _factory.create_stemmer()

def stem_tokens(tokens: list[str]) -> list[str]:
    return [_stemmer.stem(t) for t in tokens]


def removestopword_steming(text: list[str]) -> str:
  text = remove_stopwords(text)
  text = stem_tokens(text)
  return text


"""# Preproses Final"""

def preprosesing(text: str) -> str:
    text = norm_char_casfold(text)
    text = remove_noise(text)
    text = rejoin_norm_plesetan(text)
    text = removestopword_steming(text)
    return " ".join(text)
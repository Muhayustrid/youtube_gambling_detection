# ========== Import & Setup ==========
import re
import unicodedata
import difflib
from typing import List

from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory


# ========== 1) Emoji → huruf/angka + hapus Variation Selector 16 ==========
VS16 = "\uFE0F"

def remove_variation_selectors(s: str) -> str:
    return s.replace(VS16, "")

def _emoji_digit_word_to_int(name: str):
    """Helper untuk ambil digit 0–9 dari nama Unicode seperti 'KEYCAP DIGIT NINE' / 'CIRCLED DIGIT ONE'."""
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
    out = []
    for ch in s:
        try:
            name = unicodedata.name(ch)
        except ValueError:
            out.append(ch)
            continue

        # dagger lookalikes → 't'
        if "DAGGER" in name:
            out.append("t")
            continue

        # regional indicators 🇦..🇿 → huruf ASCII
        if "REGIONAL INDICATOR SYMBOL LETTER" in name:
            out.append(name.split()[-1])
            continue

        # SQUARED/CIRCLED/NEGATIVE CIRCLED/BUTTON letters → huruf ASCII
        if "LATIN CAPITAL LETTER" in name and (
            "SQUARED" in name or "CIRCLED" in name or "NEGATIVE CIRCLED" in name or name.endswith("BUTTON")
        ):
            out.append(name.split()[-1])
            continue

        # keycap/enclosed numbers → digit 0–9
        if "KEYCAP" in name and "DIGIT" in name:
            n = _emoji_digit_word_to_int(name)
            out.append(str(n) if n is not None else ch)
            continue

        # angka enclosed/circled lain yang punya nilai numerik
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
    s = remove_variation_selectors(s)
    s = emoji_letter_digit_to_ascii(s)
    return s


# ========== 2) Unicode normalize (NFKC) + normalisasi punct/bracket/case ==========
_DASHES = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]")
_APOS   = re.compile(r"[\u2018\u2019\u02BC]")
_ZW     = re.compile(r"[\u200B-\u200F\uFEFF]")
_BRACKET_BUKA  = re.compile(r'[\[\{\(【［〔｢]')
_BRACKET_TUTUP = re.compile(r'[\]\}\)】］〕｣]')

def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)

def normalize_punct(text: str) -> str:
    text = _DASHES.sub("-", text)
    text = _APOS.sub("'", text)
    text = _ZW.sub("", text)
    return text

def normalize_bracket(text: str) -> str:
    text = _BRACKET_BUKA.sub("[", text)
    text = _BRACKET_TUTUP.sub("]", text)
    return text

def to_lower(text: str) -> str:
    return text.lower()


# ========== 3) Remove URL/mention/hashtag + bracket steril ==========
_RE_URLS     = re.compile(r'https?://\S+|www\.\S+', re.I)
_RE_MENTIONS = re.compile(r'(?<![A-Za-z0-9_])@\w+')
_RE_HASHTAGS = re.compile(r'(?<!\w)#\w+')
_RE_BRACKETS = re.compile(r'[\[\]]')

def remove_urls_mentions_hashtags(text: str) -> str:
    text = _RE_URLS.sub(" ", text)
    text = _RE_MENTIONS.sub(" ", text)
    text = _RE_HASHTAGS.sub(" ", text)
    return text

def remove_bracket(text: str) -> str:
    return _RE_BRACKETS.sub("", text)


# ========== 4) Hapus timestamps jam:menit(:detik) ==========
_TS = re.compile(r"""\b(?:[01]?\d|2[0-3])\s*[:：]\s*[0-5]\d(?:\s*[:：]\s*[0-5]\d)?\b""", re.X)
def remove_timestamps(s: str) -> str:
    return _TS.sub(" ", s)


# ========== 5) Akrítik + homoglyph folding ==========
def strip_combining_marks(text: str) -> str:
    d = unicodedata.normalize("NFKD", text)
    f = "".join(ch for ch in d if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFKC", f)

HOMO_MAP = {
    # Greek
    "η": "n", "Η": "H", "σ": "o", "ς": "o", "Σ": "S", "ο": "o", "Ο": "O",
    "ρ": "p", "Ρ": "P", "κ": "k", "Κ": "K", "ν": "v", "Ν": "N", "τ": "t", "Τ": "T",
    "χ": "x", "Χ": "X", "μ": "m", "Μ": "M", "λ": "l", "Λ": "L","ε":"e","¢":"c",
    # Cyrillic
    "а":"a","е":"e","о":"o","р":"p","с":"c","х":"x","у":"y","к":"k",
    "А":"A","Е":"E","О":"O","Р":"P","С":"C","Х":"X","У":"Y","К":"K",
    "і":"i","ї":"i","ı":"i","Ѕ":"S","ѕ":"s",
    # CJK (yang sering dipakai)
    "丅":"t","ι":"i"
}
def fold_homoglyphs(text: str) -> str:
    return "".join(HOMO_MAP.get(ch, ch) for ch in text)


# ========== 6) Intraword symbols handling ==========
_PUNCT_TO_SPACE = r"[',.!?\u2026;]+"

def _allowed_chars(keep_at: bool) -> str:
    return r"@._\-" if keep_at else r"._\-"

def handle_intraword_symbols(text: str, *, keep_at: bool = True) -> str:
    allowed = _allowed_chars(keep_at)
    text = re.sub(rf"(?iu)(?<=\w){_PUNCT_TO_SPACE}(?=\w)", " ", text)
    text = re.sub(rf"(?iu)(?<=\w){_PUNCT_TO_SPACE}[^\w{allowed}\s]+(?=\w)", " ", text)
    text = re.sub(rf"(?iu)(?<=\d)[^\w{allowed}\s]+(?=[a-z])", " ", text)
    text = re.sub(rf"(?iu)(?<=\w)[^\w{allowed}\s]+(?=\w)", "", text)
    text = re.sub(rf"(?iu)(?<=\s)[^\w{allowed}\s]+|[^\w{allowed}\s]+(?=\s)", " ", text)
    text = re.sub(rf"(?iu)^[^\w{allowed}\s]+(?=\w)", " ", text)
    text = re.sub(rf"(?iu)(?<=\w)[^\w{allowed}\s]+$", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ========== 7) Whitelist global + squeeze spaces ==========
def keep_alnum_and_space(text: str) -> str:
    return re.sub(r"[^0-9a-zA-Z@!\$]+", " ", text)

def squeeze_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# ========== 8) Leet minimal per token ==========
LEET_TABLE_MIN = {'0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '6': 'g'}

def leet_min_token(tok: str, *, map_at: bool = False) -> str:
    if re.search(r'[A-Za-z]', tok) and re.search(r'\d', tok):
        return tok
    out = []
    n = len(tok)
    for i, ch in enumerate(tok):
        nxt = tok[i+1].lower() if i+1 < n else ''
        if ch == '@':
            out.append('a' if map_at else '@')
            continue
        if ch.isdigit():
            is_last = (i == n-1)
            next_is_digit = (i+1 < n and tok[i+1].isdigit())
            if is_last or next_is_digit:
                out.append(ch)
                continue
            if ch == '4' and nxt == 'd':
                out.append('4')
                continue
            out.append(LEET_TABLE_MIN.get(ch, ch))
            continue
        out.append(ch.lower())
    return ''.join(out)

def leet_min_line(text: str, *, map_at: bool = False) -> str:
    return ' '.join(leet_min_token(t, map_at=map_at) for t in text.split())


# ========== 9) Rejoin huruf terpisah & trailing digits ==========
VOWELS = set("aiueo")

def rejoin_split_letters(tokens: List[str]) -> List[str]:
    out, i, n = [], 0, len(tokens)
    while i < n:
        j, letters = i, []
        while j < n and re.fullmatch(r'[A-Za-z]', tokens[j]):
            letters.append(tokens[j].lower())
            j += 1
        if len(letters) >= 3:
            word = ''.join(letters)
            k, digits = j, []
            while k < n and re.fullmatch(r'\d+', tokens[k]):
                digits.append(tokens[k]); k += 1
            if digits:
                word += ''.join(digits); j = k
            if any(ch in VOWELS for ch in word) and 3 <= len(word) <= 24:
                out.append(word); i = j; continue
        if re.fullmatch(r'\d+', tokens[i]):
            k, digits = i, []
            while k < n and re.fullmatch(r'\d+', tokens[k]):
                digits.append(tokens[k]); k += 1
            digits_str = ''.join(digits)
            if out and re.fullmatch(r'[A-Za-z]+', out[-1]):
                out[-1] = out[-1] + digits_str
            else:
                out.append(digits_str)
            i = k; continue
        out.append(tokens[i]); i += 1
    return out


# ========== 10) Heuristik angka dinamis untuk konteks promosi ==========
PROMO_CUES = {
    "slot","gacor","maxwin","depo","deposit","wd","jackpot",
    "togel","casino","bonus","spin","bet","jp"
}

_RE_ALNUM_MIX   = re.compile(r'(?i)(?:[a-z]+\d+|\d+[a-z]+)')
_RE_REP3_DIGITS = re.compile(r'^(\d)\1{2,}$')
_RE_REP2_DIGITS = re.compile(r'^(\d)\1$')

def _has_promo_near(tokens: List[str], idx: int, window: int = 2) -> bool:
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

def filter_numbers_dynamic(tokens: List[str], replace_with_num: bool = False) -> List[str]:
    out: List[str] = []
    for i, t in enumerate(tokens):
        tok = t.lower()

        if _RE_ALNUM_MIX.fullmatch(tok):
            out.append(tok); continue

        if not tok.isdigit():
            out.append(tok); continue

        if len(tok) >= 8:
            out.append(tok); continue

        if _RE_REP3_DIGITS.fullmatch(tok):
            out.append(tok); continue

        if _RE_REP2_DIGITS.fullmatch(tok) and _has_promo_near(tokens, i):
            out.append(tok); continue

        if _has_promo_near(tokens, i):
            out.append(tok); continue

        if replace_with_num:
            out.append("<NUM>")
        # else drop
    return out


# ========== 11) Leet/Plesetan Normalization (agresif terkontrol) ==========
LEET_MAP_TABLE = {'0': 'o', '1': 'i', '3': 'e', '4': 'a', '6': 'g', '5': 's', '@': 'a'}
_RE_PURE_2_3_DIGIT = re.compile(r'^\d{2,3}$')
_RE_AT_INFIX = re.compile(r'(?i)(?<=[a-z])@(?=[a-z])')

def map_chars(tok: str) -> str:
    t = tok
    if t.lower().endswith('4d'):
        return t
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
            if run_len >= 2:
                out.append(t[i:j])
            else:
                out.append(LEET_MAP_TABLE.get(ch, ch))
            i = j
            continue
        out.append(LEET_MAP_TABLE.get(ch, ch))
        i += 1
    return ''.join(out)

SUBS = {
    # MAXWIN
    'm4xwin': 'maxwin','m@xwin':'maxwin','m4xw1n':'maxwin','maxw!n':'maxwin',
    'maxwinn':'maxwin','m14xwin':'maxwin','m4ksvin':'maxwin',
    # SLOT
    'sl0t':'slot','s1ot':'slot','slott':'slot','sloot':'slot','s|ot':'slot','sl07':'slot',
    'sgpin':'spin',
    # GACOR
    'g4cor':'gacor','g@c0r':'gacor','gacoor':'gacor','g4k0r':'gacor','gac0r':'gacor','g4c0r':'gacor','ggacor':'gacor',
    # HOKI
    'hokii':'hoki','h0ki':'hoki','hokl':'hoki','h0kl':'hoki','h0 kl':'hoki','ho k1':'hoki',
    # LAIN
    'b3t':'bet','bette':'bet',
    'd3po':'depo','dep0':'depo','d3posit':'deposit',
    'wdw':'wd','w1d':'wd',
    'c4sin0':'casino',
    'jackp0t':'jackpot','j4ckp0t':'jackpot',
    't0g3l':'togel','t0g3ll':'togel',
    'pr0m0':'promo','pr0m':'promo',
    'ref3rral':'referral','ref3r':'refer',
    'b0nus':'bonus','b0nuss':'bonus',
    'g@ruda':'garudahoki','garudahokl':'garudahoki'
}

DOMAIN_WORDS = {
    "maxwin","gacor","slot","spin","garudahoki","pulau","hoki",
    "deposit","depo","wd","jackpot","togel","casino","promo","bonus","bet"
}

def fix_infix_digits_with_domain(tok: str, domain=DOMAIN_WORDS, thr: float = 0.80) -> str:
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
        if letters_only[0] == best[0] or letters_only[-2:] == best[-2:]:
            return best
    return tok

def squeeze_repeats(token: str, max_repeat: int = 1) -> str:
    out, cnt, prev = [], 0, ''
    for ch in token:
        if ch == prev:
            cnt += 1
            limit = 2
            if ch.isdigit() or cnt <= limit:
                out.append(ch)
        else:
            prev = ch
            cnt = 1
            out.append(ch)
    return ''.join(out)

def normalize_plesetan(tokens: List[str]) -> List[str]:
    out: List[str] = []
    for t in tokens:
        if t.isdigit():
            out.append(t)
            continue
        t0 = t.lower()
        t1 = map_chars(t0)
        t2 = SUBS.get(t1, t1)
        t3 = squeeze_repeats(t2, max_repeat=1)
        t4 = fix_infix_digits_with_domain(t3)
        t5 = SUBS.get(t4, t4)
        out.append(t5)
    return out


# ========== 12) Stopword & Stemming (Sastrawi) ==========
_factory_sw = StopWordRemoverFactory()
_stopwords_set = set(_factory_sw.get_stop_words())

def remove_stopwords(tokens: List[str]) -> List[str]:
    return [t for t in tokens if t not in _stopwords_set]

_factory_stem = StemmerFactory()
_stemmer = _factory_stem.create_stemmer()

def stem_tokens(tokens: List[str]) -> List[str]:
    return [_stemmer.stem(t) for t in tokens]

def removestopword_stemming(tokens: List[str]) -> List[str]:
    tokens = remove_stopwords(tokens)
    tokens = stem_tokens(tokens)
    return tokens


# ========== 13) Pipeline utama ==========
def preprosesing(text: str, *, keep_at: bool = True, map_at_leet: bool = False) -> str:
    # A) Normalisasi bentuk
    text = normalize_emoji_text(text)
    text = normalize_unicode(text)
    text = normalize_punct(text)
    text = normalize_bracket(text)
    text = to_lower(text)

    # B) Noise pola khusus
    text = remove_urls_mentions_hashtags(text)
    text = remove_timestamps(text)
    text = remove_bracket(text)

    # C) Akrítik + homoglyph
    text = strip_combining_marks(text)
    text = fold_homoglyphs(text)

    # D) Intraword symbols
    text = handle_intraword_symbols(text, keep_at=keep_at)

    # E) Whitelist + spasi
    text = keep_alnum_and_space(text)
    text = squeeze_spaces(text)

    # F) Leet minimal
    text = leet_min_line(text, map_at=map_at_leet)

    # G) Rejoin huruf terpisah (+ trailing digits)
    tokens = text.split()
    tokens = rejoin_split_letters(tokens)

    # H) Plesetan + angka dinamis + stopword+stemming
    tokens = normalize_plesetan(tokens)
    tokens = filter_numbers_dynamic(tokens, replace_with_num=False)
    tokens = removestopword_stemming(tokens)

    return squeeze_spaces(' '.join(tokens))

import re
from collections import Counter
from typing import List, Tuple

_WORD_RE = re.compile(r"[0-9a-z]+", re.I)

def tokenize_simple(text: str):
    """Asumsi text sudah preprocessed (lowercase, no weird chars)."""
    return _WORD_RE.findall(text)

def top_keywords_from_texts(texts: List[str], top_n: int = 30, min_len: int = 1) -> List[Tuple[str,int]]:
    c = Counter()
    for t in texts:
        toks = tokenize_simple(t)
        for w in toks:
            if len(w) >= min_len:
                c[w] += 1
    return c.most_common(top_n)

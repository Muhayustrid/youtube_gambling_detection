import re
import unicodedata
import difflib
from typing import List, Optional
from unidecode import unidecode
from functools import lru_cache

_RE_DASHES = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]")
_RE_APOS = re.compile(r"[\u2018\u2019\u02BC]")
_RE_ZW = re.compile(r"[\u200B-\u200F\uFEFF\u2060-\u2063]") 
_RE_URLS = re.compile(r'https?://\S+|www\.\S+', re.I)
_RE_MENTIONS = re.compile(r'(?<![A-Za-z0-9_])@[a-zA-Z0-9_-]+')
_RE_BRACKETS = re.compile(r'[\[\]\{\}\(\)【［〔｢\]\}\)】］〕｣]')
_RE_TIMESTAMPS = re.compile(r"""\b(?:[01]?\d|2[0-3])\s*[:：;]\s*[0-5]\d(?:\s*[:：;]\s*[0-5]\d)?\b""", re.X)
_RE_AT_INFIX = re.compile(r'(?i)(?<=[a-z])@(?=[a-z])')
_RE_ALNUM_MIX = re.compile(r'(?i)(?:[a-z]+\d+|\d+[a-z]+)')

VS16 = "\uFE0F"
COEN = "\u20E3"
HARD_SEPARATORS = r"/|\\:;~_.,\-!()\[\]{}<>=+\"'"
VOWELS = set("aiueo")

LEET_MAP_TABLE = {
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', 
    '6': 'g', '5': 's', '@': 'a', '9': 'g'
}

INDONESIAN_STOPWORDS = frozenset([
    "ada", "adalah", "adanya", "akankah", "akhir", "akhiri", "akhirnya", "aku", "akulah",
    "amat", "amatlah", "anda", "andalah", "antar", "antara", "antaranya", "apa", "apaan",
    "apabila", "apakah", "apalagi", "apatah", "atau", "ataukah", "ataupun", "bagai",
    "bagaikan", "bagaimana", "bagaimanakah", "bagaimanapun", "bagi", "bagian", "bahkan",
    "bahwa", "bahwasanya", "baik", "bakal", "bakalan", "balik", "banyak", "bapak",
    "baru", "bawah", "beberapa", "begini", "beginian", "beginikah", "beginilah",
    "begitu", "begitukah", "begitulah", "begitupun", "bekerja", "belakang", "belakangan",
    "belum", "belumlah", "benar", "benarkah", "benarlah", "berada", "berakhir", "berakhirlah",
    "berapa", "berapakah", "berapalah", "berapapun", "berarti", "berawal", "berbagai",
    "berdatangan", "beri", "berikan", "berikannya", "bermacam", "bermacam-macam",
    "bermaksud", "bermula", "bersama", "bersama-sama", "bersiap", "bersiap-siap",
    "bertanya", "bertanya-tanya", "berturut", "berturut-turut", "bertutur", "besar",
    "betapa", "betulkah", "biasa", "biasanya", "bila", "bilakah", "bisa", "bisakah",
    "boleh", "bolehkah", "bolehlah", "buat", "bukan", "bukankah", "bukanlah",
    "bukannya", "bulan", "bung", "cara", "caranya", "cukup", "cukupkah", "cukuplah",
    "dahulu", "dalam", "dan", "dapat", "dari", "daripada", "datang", "dekat", "demi",
    "demikian", "demikianlah", "dengan", "depan", "di", "dia", "diakhiri", "diakhirinya",
    "dialah", "diantara", "diantaranya", "diberi", "diberikan", "diberikannya",
    "dibuat", "dibuatnya", "didapat", "didatangkan", "digunakan", "diibaratkan",
    "diibaratkannya", "diingat", "diingatkan", "diinginkan", "dijawab", "dijelaskan",
    "dijelaskannya", "dikarenakan", "dikatakan", "dikatakannya", "dikerjakan",
    "diketahui", "diketahuinya", "dikira", "dilakukan", "dilalui", "dilihat",
    "dimaksud", "dimaksudkan", "dimaksudkannya", "diminta", "dimintai", "dimisalkan",
    "dimulai", "dimulailah", "dimulainya", "dinamai", "dinamakan", "dini", "dipastikan",
    "diperbuat", "diperbuatnya", "dipergunakan", "diperkirakan", "diperlihatkan",
    "diperlukan", "diperlukannya", "dipersoalkan", "dipertanyakan", "dipunyai",
    "diri", "dirinya", "disampaikan", "disebut", "disebutkan", "disebutkannya",
    "disinilah", "ditandaskan", "ditanya", "ditanyai", "ditanyakan", "ditegaskan",
    "ditujukan", "ditunjuk", "ditunjuki", "ditunjukkan", "ditunjukkannya", "ditunjuknya",
    "dituturkan", "dituturkannya", "diucapkan", "diucapkannya", "diungkapkan", "dong",
    "dua", "dulu", "empat", "engkau", "engkaukah", "engkaulah", "entah", "entahlah",
    "guna", "guna", "hal", "hal", "hal-hal", "hampir", "hanya", "hanyalah", "hari",
    "harus", "haruslah", "harusnya", "hendak", "hendaklah", "hendaknya", "hingga",
    "ia", "ialah", "ibarat", "ibaratkan", "ibaratnya", "ibu", "ikut", "ingat",
    "ingin", "inginkah", "inginkan", "ini", "inikah", "inilah", "itu", "itukah",
    "itulah", "jadi", "jadilah", "jadinya", "jangan", "jangankan", "janganlah",
    "jauh", "jawab", "jawaban", "jawabnya", "jelas", "jelaskan", "jelaslah", "jelasnya",
    "jika", "jikalau", "juga", "jumlah", "justru", "kala", "kalau", "kalaulah",
    "kalaupun", "kalian", "kami", "kamilah", "kami", "kamu", "kamulah", "kan",
    "kapan", "kapankah", "kapanpun", "karena", "karenanya", "kasus", "kata",
    "katakan", "katakanlah", "katanya", "ke", "keadaan", "kebetulan", "kecil",
    "kedua", "keduanya", "keinginan", "kelamaan", "keluar", "kembali", "kemudian",
    "kemungkinan", "kemungkinannya", "kenapa", "kepada", "kepadanya", "ketika",
    "ketiganya", "ketika", "khususnya", "kini", "kinilah", "kira", "kira-kira",
    "kiranya", "kita", "kitalah", "kok", "lagi", "lagian", "lah", "lain", "lainnya",
    "lalu", "lama", "lamanya", "lebih", "lewat", "lima", "luar", "macam", "maka",
    "makanya", "makin", "malah", "malahan", "mampu", "mampukah", "mana", "manakah",
    "manalagi", "masa", "masalah", "masalahnya", "masih", "masihkah", "masing",
    "masing-masing", "mau", "maukah", "maupun", "melainkan", "melakukan", "melalui",
    "melihat", "melihatnya", "memang", "memastikan", "memberi", "memberikan",
    "membuat", "memerlukan", "memihak", "memiliki", "memikirkan", "memililiki",
    "meminta", "memintai", "memisalkan", "memperbuat", "mempergunakan", "memperkirakan",
    "memperlihatkan", "memperoleh", "mempergunakan", "memperkirakan", "memperlihatkan",
    "memperoleh", "memperolehnya", "mempersiapkan", "mempersoalkan", "mempertanyakan",
    "mempunyai", "menanti", "menanti-nanti", "menanyakkan", "menawar", "menawarkan",
    "mendapat", "mendapatkan", "mendatangi", "mendatangkan", "menegaskan", "mengakhiri",
    "mengapa", "mengatakan", "mengatakannya", "mengenai", "mengerjakan", "mengetahui",
    "menggunakan", "menghendaki", "mengibaratkan", "mengibaratkannya", "mengingat",
    "mengingatkan", "menginginkan", "mengira", "mengucapkan", "mengucapkannya",
    "mengungkapkan", "menjadi", "menjawab", "menjelaskan", "menuju", "menunjuk",
    "menunjuki", "menunjukkan", "menunjuknya", "menurut", "menuturkan", "menyampaikan",
    "menyangkut", "menyatakan", "menyebutkan", "menyeluruh", "menyiapkan", "merasa",
    "mereka", "merekalah", "merupakan", "meski", "meskipun", "meyakini", "meyakinkan",
    "minta", "mirip", "misal", "misalkan", "misalnya", "mula", "mulai", "mulailah",
    "mulanya", "mungkin", "mungkinkah", "nah", "naik", "namun", "nanti", "nantinya",
    "nyaris", "nyatanya", "oleh", "oleh karena itu", "olehnya", "pada", "padahal",
    "padanya", "paling", "pantas", "para", "pasti", "pastilah", "penting", "pentingnya",
    "per", "perlu", "perlukah", "perlunya", "pernah", "persoalan", "pertama",
    "pertama-tama", "pertanyaan", "pertanyakan", "pihak", "pihaknya", "pukul",
    "pula", "pun", "punya", "rasa", "rasanya", "rata", "rupanya", "saat", "saatnya",
    "saja", "sajakah", "sajalah", "saling", "sama", "sama-sama", "sambil", "sampai",
    "sampai-sampai", "sampaikan", "sana", "sangat", "sangatlah", "satu", "saya",
    "sayalah", "se", "sebab", "sebabnya", "sebagai", "sebagaimana", "sebagainya",
    "sebagian", "sebanyak", "sebegini", "sebegitu", "sebelum", "sebelumnya",
    "sebenarnya", "sebetulnya", "sebisanya", "sebuah", "sebut", "sebutlah", "sebutnya",
    "secara", "secukupnya", "sedang", "sedangkan", "sedemikian", "sedikit",
    "sedikitnya", "segala", "segalanya", "segera", "seharusnya", "sehingga",
    "sejak", "sejauh", "sejenak", "sekali", "sekali-kali", "sekalian", "sekaligus",
    "sekalipun", "sekarang", "sekecil", "seketika", "sekiranya", "sekitar",
    "sekitarnya", "sekalipun", "sekarang", "sekecil", "seketika", "sekiranya",
    "sekitar", "sekitarnya", "sela", "selagi", "selain", "selaku", "selalu",
    "selama", "selamanya", "selanjutnya", "seluruh", "seluruhnya", "semakin",
    "semakin", "sementara", "semisal", "semua", "semuanya", "semula", "sendiri",
    "sendirian", "sendirinya", "seolah", "seolah-olah", "seorang", "sepanjang",
    "sepantasnya", "sepantasnyalah", "seperlunya", "seperti", "sepertinya",
    "sering", "seringkali", "serupa", "sesaat", "sesama", "sesegera", "sesuai",
    "sesungguhnya", "sesungguhnyalah", "setelah", "setempat", "setengah", "seterusnya",
    "setiap", "setiakali", "sewaktu", "siap", "siapa", "siapakah", "siapapun",
    "sini", "sinilah", "soal", "soalnya", "suatu", "sudah", "sudahkah", "sudahlah",
    "supaya", "tadi", "tadinya", "tak", "tambah", "tambahnya", "tampak", "tampaknya",
    "tanpa", "tanya", "tanyakan", "tanyanya", "tap", "tapi", "telah", "tempat",
    "tentang", "tentu", "tentulah", "tentunya", "terasa", "terbanyak", "terdahulu",
    "terdapat", "terdiri", "terhenti", "terjadinya", "terkait", "terlalu",
    "terlebih", "terlebih dulu", "termasuk", "ternyata", "tersampaikan", "tersebut",
    "tersebutlah", "tertentu", "tertuju", "terus", "terutama", "tetap", "tetapi",
    "tiap", "tiba", "tiba-tiba", "tidak", "tidakkah", "tidaklah", "tidaknya",
    "tiga", "toh", "tunjuk", "turut", "tutur", "tuturnya", "ucap", "ucapnya",
    "uang", "ujar", "ujarnya", "umum", "umumnya", "ungkap", "ungkapnya", "untuk",
    "untuknya", "upah", "waduh", "wah", "wahai", "waktu", "waktunya", "walau",
    "walaupun", "wong", "yaitu", "yakin", "yakni", "yang"
])

SUBS = {
    'maxw!n': 'maxwin', 'maxwinn': 'maxwin', 'm14xwin': 'maxwin', 'm4ksvin': 'maxwin',
    '5lot': 'slot', 's1ot': 'slot', 'slott': 'slot', 'sloot': 'slot', 
    's|ot': 'slot', 'sl07': 'slot', 's!ot': 'slot', 'sgpin': 'spin',
    'gacoor':'gacor', 'g4k0r':'gacor', 'ggacor':'gacor', '9acor':'gacor',
    'hokii': 'hoki', 'hokl': 'hoki', 'h0kl':'hoki', 'garudahokl':'garudahoki',
    'bette':'bet', 'wdw':'wd', 'w1d':'wd', 't0g3ll':'togel', 
    'pr0m':'promo', 'b0nuss':'bonus', '9aruda':'garuda', 
    'arwanatt':'arwanatoto', 't0to':'toto', 'm0na4d':'mona4d', 
    'jepe':'jp', 'jepey':'jp', 'jepee':'jp',
}

DOMAIN_WORDS = {
    "maxwin", "gacor", "slot", "spin", "garudahoki", "pulauwin", "hoki", "jp",
    "deposit", "depo", "wd", "jackpot", "togel", "casino", "promo", "bonus", 
    "bet", "withdraw", "rtp"
}

HOMO_MAP = {
    "А": "A", "а": "a", "В": "B", "в": "b", "Е": "E", "е": "e", "К": "K", "к": "k", "М": "M", "Т": "T",
    "Х": "X", "х": "x", "О": "O", "о": "o", "Н": "H", "н": "h", "Р": "P", "р": "p", "С": "C", "с": "c",
    "У": "Y", "у": "y", "З": "Z", "з": "z", "Я": "R", "Ч": "4", "Ж": "X", "Ц": "LL", "і": "i", "ј": "j",
    "ѕ": "s", "ѡ": "w", "ә": "e", "б": "6", "г": "r", "д": "a", "и": "u", "й": "u", "л": "n", "м": "m",
    "п": "n", "т": "t", "ф": "o", "ц": "u", "ш": "w", "щ": "w", "ъ": "b", "ы": "bi", "ь": "b", "э": "e",
    "ю": "io", "я": "r", "ї": "i", "є": "e",
    'Ա': 'U', 'ա': 'w', 'Բ': 'B', 'բ': 'b', 'Գ': '9', 'գ': 'q', 'Դ': 'N', 'դ': 'n', 'Ե': 'E', 'ե': 't',
    'Զ': 'Z', 'զ': 'q', 'Է': 'E', 'է': 't', 'Ը': 'P', 'ը': 'p', 'Թ': 'P', 'թ': 'p', 'Ժ': 'D', 'ժ': 'd',
    'Ի': 'H', 'ի': 'h', 'Լ': 'L', 'լ': 'l', 'Խ': 'X', 'խ': 'x', 'Ծ': 'G', 'ծ': 'd', 'Կ': 'Y', 'կ': 'k',
    'Հ': 'H', 'հ': 'h', 'Ձ': 'A', 'ձ': 'a', 'Ղ': 'N', 'ղ': 'n', 'Ճ': 'U', 'ճ': 'u', 'Մ': 'M', 'մ': 'u',
    'Յ': 'J', 'յ': 'j', 'Ն': 'U', 'ն': 'u', 'Շ': '2', 'շ': '2', 'Ո': 'N', 'ո': 'n', 'Չ': '4', 'չ': 'n',
    'Պ': 'M', 'պ': 'm', 'Ջ': '2', 'ջ': '2', 'Ռ': 'N', 'ռ': 'n', 'Ս': 'U', 'ս': 'u', 'Վ': '4', 'վ': '4',
    'Տ': 'T', 'տ': 't', 'Ր': 'R', 'ր': 'r', 'Ց': 'G', 'ց': 'g', 'Ւ': 'L', 'ւ': 'L', 'Փ': 'P', 'փ': 'p',
    'Ք': 'P', 'ք': 'p', 'Օ': 'O', 'օ': 'o', 'Ֆ': 'F', 'ֆ': 'f',
    "η": "n", "Η": "H", "σ": "o", "ς": "o", "Σ": "S", "ο": "o", "Ο": "O", "ρ": "p", "Ρ": "P", "κ": "k",
    "Κ": "K", "ν": "v", "Ν": "N", "τ": "t", "Τ": "T", "χ": "x", "Χ": "X", "μ": "m", "Μ": "M", "λ": "a",
    "Λ": "a", "α": "a", "β": "b", "γ": "y", "δ": "d", "ε": "e", "ζ": "z", "θ": "0", "ι": "i", "ξ": "e",
    "π": "n", "υ": "u", "φ": "o", "ψ": "w", "ω": "w", "ϲ": "c", "ϵ": "e", "Ϛ": "s", "ϫ": "x", "Α": "A",
    "Β": "B", "Δ": "A", "Γ": "r", "Ω": "W", "Ϝ": "F",
    "丅": "t", "丄": "t", "丫": "y", "厶": "a", "乇": "e", "乚": "l", "囗": "o", "工": "i", "尺": "r", "丁": "t",
    "十": "t", "一": "-", "二": "=", "三": "e", "口": "o", "人": "y", "入": "y", "X": "x", "匕": "t", "マ": "v",
    "ム": "a", "カ": "n", "丨": "I", "亅": "J", "ロ": "O", "回": "O", "曰": "O", "乂": "X", "⻌": "Z", "八": "a",
    "〇": "0",
    'ᴀ': 'a', 'ʙ': 'b', 'ᴄ': 'c', 'ᴅ': 'd', 'ᴇ': 'e', 'ғ': 'f', 'ɢ': 'g', 'ʜ': 'h', 'ɪ': 'i', 'ᴊ': 'j', 'ᴋ': 'k',
    'ʟ': 'l', 'ᴍ': 'm', 'ɴ': 'n', 'ᴏ': 'o', 'ᴘ': 'p', 'ꞯ': 'q', 'ʀ': 'r', 'ꜱ': 's', 'ᴛ': 't', 'ᴜ': 'u', 'ᴠ': 'v',
    'ᴡ': 'w', 'x': 'x', 'ʏ': 'y', 'ᴢ': 'z',
    '𝟶': '0', '𝟷': '1', '𝟸': '2', '𝟹': '3', '𝟺': '4', '𝟻': '5', '𝟼': '6', '𝟽': '7', '𝟾': '8', '𝟿': '9',
    '𝟢': '0', '𝟣': '1', '𝟤': '2', '𝟹': '3', '𝟺': '4', '𝟻': '5', '𝟼': '6', '𝟽': '7', '𝟾': '8', '𝟿': '9',
    'ᗩ': 'a', 'ᐯ': 'v', 'ᐠ': 'v', 'ᑕ': 'c', 'ᑐ': 'j', 'ᗷ': 'b', 'ᑌ': 'u', 'ᑎ': 'n', 'ᑘ': 'u', 'ᑭ': 'p', 'ᑯ': 'd',
    'ᑲ': 'b', 'ᑫ': 'q', 'ᕒ': 'p', 'ᙀ': 'q', 'ᒪ': 'l',  'ᒧ': 'j', 'ᒥ': 'r', 'ᗰ': 'm', 'ᗯ': 'w', 'ᙡ': 'w', 'ᔕ': 's',
    'ᔅ': 'z', '᙭': 'x', 'ᔦ': 'y', 'ᕼ': 'h', 'ᖇ':'r',
    '𝒜': 'A', '𝒞': 'C', '𝒟': 'D', '𝒢': 'G', '𝒥': 'J', '𝒦': 'K', '𝒩': 'N', '𝒪': 'O', '𝒫': 'P', '𝒬': 'Q',
    '𝒮': 'S', '𝒯': 'T', '𝒰': 'U', '𝒱': 'V', '𝒲': 'W','𝒳': 'X', '𝒴': 'Y', '𝒵': 'Z',
    'ℬ': 'B', 'ℰ': 'E', 'ℱ': 'F', 'ℋ': 'H', 'ℐ': 'I', 'ℒ': 'L', 'ℳ': 'M', 'ℛ': 'R', '𝒶': 'a',
    '𝒷': 'b', '𝒸': 'c', '𝒹': 'd', '𝒻': 'f', '𝒽': 'h', '𝒾': 'i', '𝒿': 'j', '𝓀': 'k', '𝓁': 'l', '𝓂': 'm', '𝓃': 'n', '𝓅': 'p', '𝓆': 'q',
    '𝓇': 'r', '𝓈': 's', '𝓉': 't', '𝓊': 'u', '𝓋': 'v', '𝓌': 'w', '𝓍': 'x', '𝓎': 'y', '𝓏': 'z', 'ℯ': 'e', 'ℊ': 'g', 'ℴ': 'o',
    'Ɦ': 'H', 'ƙ': 'k', 'ƣ': 'g', 'ʞ': 'k', 'Ħ': 'H', 'ħ': 'h', 'Ɨ': 'I', 'ɨ': 'i', 'ł': 'l', 'Ɵ': 'O', 'Ɱ': 'M',
    'Ⱡ': 'L', 'Ⱨ': 'H', 'Ɽ': 'R', 'Ꜹ': 'A', 
    '᥇':'b', 'ꪖ':'a', 'ꪻ':'t', '᥅':'r','ꫀ':'e', 'ᔰ': '4', 'ᦔ':'d',
}

_HOMO_TRANS = str.maketrans(HOMO_MAP)

STOPWORDS_ID = {
    'ada', 'adanya', 'adalah', 'adapun', 'agak', 'agaknya', 'agar', 'akan', 
    'akankah', 'akhir', 'akhiri', 'akhirnya', 'aku', 'akulah', 'amat', 'amatlah',
    'anda', 'andalah', 'antar', 'antara', 'antaranya', 'apa', 'apaan', 'apabila',
    'apakah', 'apalagi', 'apatah', 'artinya', 'asal', 'asalkan', 'atas', 'atau',
    'ataukah', 'ataupun', 'awal', 'awalnya', 'bagai', 'bagaikan', 'bagaimana',
    'bagaimanakah', 'bagaimanapun', 'bagi', 'bagian', 'bahkan', 'bahwa', 'bahwasanya',
    'baik', 'bakal', 'bakalan', 'balik', 'banyak', 'banyaknya', 'bapak', 'baru',
    'bawah', 'beberapa', 'begini', 'beginian', 'beginikah', 'beginilah', 'begitu',
    'begitukah', 'begitulah', 'begitulan', 'belakang', 'belakangan', 'belum',
    'belumlah', 'benar', 'benarkah', 'benarlah', 'berada', 'berakhir', 'berakhirlah',
    'berakhirnya', 'berapa', 'berapakah', 'berapalah', 'berapapun', 'berarti',
    'berawal', 'berbagai', 'berdatangan', 'beri', 'berikan', 'berikut', 'berikutnya',
    'berjumlah', 'berkehendak', 'berkeinginan', 'berkenaan', 'berlainan', 'berlalu',
    'berlangsung', 'berlebihan', 'bermacam', 'bermaksud', 'bermula', 'bersama',
    'bersama-sama', 'bersiap', 'bersiap-siap', 'bertanya', 'bertanya-tanya',
    'berturut', 'berturut-turut', 'bertutur', 'berujar', 'berupa', 'besar', 'betul',
    'betulkah', 'biasa', 'biasanya', 'bila', 'bilakah', 'bisa', 'bisakah', 'boleh',
    'bolehkah', 'bolehlah', 'buat', 'bukan', 'bukankah', 'bukanlah', 'bukannya',
    'bulan', 'bung', 'cara', 'caranya', 'cukup', 'cukupkah', 'cukuplah', 'cuma',
    'dahulu', 'dalam', 'dan', 'dapat', 'dari', 'daripada', 'datang', 'dekat', 'demi',
    'demikian', 'demikianlah', 'dengan', 'depan', 'di', 'dia', 'diakhiri', 'diakhirinya',
    'dialah', 'diantara', 'diantaranya', 'diberi', 'diberikan', 'diberikannya',
    'dibuat', 'dibuatnya', 'didapat', 'didatangkan', 'digunakan', 'diibaratkan',
    'diibaratkannya', 'diingat', 'diingatkan', 'diinginkan', 'dijawab', 'dijelaskan',
    'dijelaskannya', 'dikatakan', 'dikatakannya', 'dikehendaki', 'dikenakan',
    'dikerjakan', 'diketahui', 'diketahuinya', 'dikira', 'dilakukan', 'dilalui',
    'dilihat', 'dimaksud', 'dimaksudkan', 'dimaksudkannya', 'dimaksudnya', 'diminta',
    'dimintai', 'dimisalkan', 'dimulai', 'dimulailah', 'dimulainya', 'dimungkinkan',
    'dini', 'dipastikan', 'diperbuat', 'diperbuatnya', 'dipergunakan', 'diperkirakan',
    'diperlihatkan', 'diperlukan', 'diperlukannya', 'dipersoalkan', 'dipertanyakan',
    'dipunyai', 'diri', 'dirinya', 'disampaikan', 'disebut', 'disebutkan',
    'disebutkannya', 'disini', 'disinilah', 'ditambahkan', 'ditandaskan', 'ditanya',
    'ditanyai', 'ditanyakan', 'ditegaskan', 'ditujukan', 'ditunjuk', 'ditunjuki',
    'ditunjukkan', 'ditunjukkannya', 'ditunjuknya', 'dituturkan', 'dituturkannya',
    'diucapkan', 'diucapkannya', 'diungkapkan', 'dong', 'dua', 'dulu', 'empat',
    'enggak', 'enggaknya', 'entah', 'entahlah', 'guna', 'gunakan', 'hal', 'hampir',
    'hanya', 'hanyalah', 'hari', 'harus', 'haruslah', 'harusnya', 'hendak',
    'hendaklah', 'hendaknya', 'hingga', 'ia', 'ialah', 'ibarat', 'ibaratkan',
    'ibaratnya', 'ibu', 'ikut', 'ingat', 'ingat-ingat', 'ingin', 'inginkah',
    'inginkan', 'ini', 'inikah', 'inilah', 'itu', 'itukah', 'itulah', 'jadi',
    'jadilah', 'jadinya', 'jangan', 'jangankan', 'janganlah', 'jauh', 'jawab',
    'jawaban', 'jawabnya', 'jelas', 'jelaskan', 'jelaslah', 'jelasnya', 'jika',
    'jikalau', 'juga', 'jumlah', 'jumlahnya', 'justru', 'kala', 'kalau', 'kalaulah',
    'kalaupun', 'kalian', 'kami', 'kamilah', 'kamu', 'kamulah', 'kan', 'kapan',
    'kapankah', 'kapanpun', 'karena', 'karenanya', 'kasus', 'kata', 'katakan',
    'katakanlah', 'katanya', 'ke', 'keadaan', 'kebetulan', 'kecil', 'kedua',
    'keduanya', 'keinginan', 'kelamaan', 'kelihatan', 'kelihatannya', 'kelima',
    'keluar', 'kembali', 'kemudian', 'kemungkinan', 'kemungkinannya', 'kenapa',
    'kepada', 'kepadanya', 'kesampaian', 'keseluruhan', 'keseluruhannya', 'keterlaluan',
    'ketika', 'khususnya', 'kini', 'kinilah', 'kira', 'kira-kira', 'kiranya', 'kita',
    'kitalah', 'kok', 'kurang', 'lagi', 'lagian', 'lah', 'lain', 'lainnya', 'lalu',
    'lama', 'lamanya', 'langsung', 'lebih', 'lewat', 'lima', 'luar', 'macam', 'maka',
    'makanya', 'makin', 'malah', 'malahan', 'mampu', 'mampukah', 'mana', 'manakala',
    'manalagi', 'masa', 'masalah', 'masalahnya', 'masih', 'masihkah', 'masing',
    'masing-masing', 'mau', 'maupun', 'melainkan', 'melakukan', 'melalui', 'melihat',
    'melihatnya', 'memang', 'memastikan', 'memberi', 'memberikan', 'membuat',
    'memerlukan', 'memihak', 'meminta', 'memintakan', 'memisalkan', 'memperbuat',
    'mempergunakan', 'memperkirakan', 'memperlihatkan', 'mempersiapkan',
    'mempersoalkan', 'mempertanyakan', 'mempunyai', 'memulai', 'memungkinkan',
    'menaiki', 'menambahkan', 'menandaskan', 'menanti', 'menanti-nanti', 'menantikan',
    'menanya', 'menanyai', 'menanyakan', 'mendapat', 'mendapatkan', 'mendatang',
    'mendatangi', 'mendatangkan', 'menegaskan', 'mengakhiri', 'mengapa', 'mengatakan',
    'mengatakannya', 'mengenai', 'mengerjakan', 'mengetahui', 'menggunakan',
    'menghendaki', 'mengibaratkan', 'mengibaratkannya', 'mengingat', 'mengingatkan',
    'menginginkan', 'mengira', 'mengucapkan', 'mengucapkannya', 'mengungkapkan',
    'menjadi', 'menjawab', 'menjelaskan', 'menuju', 'menunjuk', 'menunjuki',
    'menunjukkan', 'menunjuknya', 'menurut', 'menuturkan', 'menyampaikan', 'menyangkut',
    'menyatakan', 'menyebutkan', 'menyeluruh', 'menyiapkan', 'merasa', 'mereka',
    'merekalah', 'merupakan', 'meski', 'meskipun', 'meyakini', 'meyakinkan', 'minta',
    'mirip', 'misal', 'misalkan', 'misalnya', 'mula', 'mulai', 'mulailah', 'mulanya',
    'mungkin', 'mungkinkah', 'nah', 'naik', 'namun', 'nanti', 'nantinya', 'nyaris',
    'nyatanya', 'oleh', 'olehnya', 'pada', 'padahal', 'padanya', 'pak', 'paling',
    'panjang', 'pantas', 'para', 'pasti', 'pastilah', 'per', 'percuma', 'perlu',
    'perlukah', 'perlunya', 'pernah', 'persoalan', 'pertama', 'pertama-tama',
    'pertanyaan', 'pertanyakan', 'pihak', 'pihaknya', 'pukul', 'pula', 'pun', 'punya',
    'rasa', 'rasanya', 'rata', 'rupanya', 'saat', 'saatnya', 'saja', 'sajalah',
    'salam', 'saling', 'sama', 'sama-sama', 'sambil', 'sampai', 'sampai-sampai',
    'sampaikan', 'sana', 'sangat', 'sangatlah', 'satu', 'saya', 'sayalah', 'se',
    'sebab', 'sebabnya', 'sebagai', 'sebagaimana', 'sebagainya', 'sebagian', 'sebaik',
    'sebaik-baiknya', 'sebaiknya', 'sebaliknya', 'sebanyak', 'sebegini', 'sebegitu',
    'sebelum', 'sebelumnya', 'sebenarnya', 'seberapa', 'sebesar', 'sebetulnya',
    'sebisanya', 'sebuah', 'sebut', 'sebutlah', 'sebutnya', 'secara', 'secukupnya',
    'sedang', 'sedangkan', 'sedemikian', 'sedikit', 'sedikitnya', 'seenaknya',
    'segala', 'segalanya', 'segera', 'seharusnya', 'sehingga', 'seingat', 'sejak',
    'sejauh', 'sejenak', 'sejumlah', 'sekadar', 'sekadarnya', 'sekali', 'sekali-kali',
    'sekalian', 'sekaligus', 'sekalipun', 'sekarang', 'sekarang-sekarang', 'sekecil',
    'seketika', 'sekiranya', 'sekitar', 'sekitarnya', 'sekurang-kurangnya',
    'sekurangnya', 'sela', 'selain', 'selaku', 'selalu', 'selama', 'selama-lamanya',
    'selamanya', 'selanjutnya', 'seluruh', 'seluruhnya', 'semacam', 'semakin',
    'semampu', 'semampunya', 'semasa', 'semasih', 'semata', 'semata-mata', 'semaunya',
    'sementara', 'semisal', 'semisalnya', 'sempat', 'semua', 'semuanya', 'semula',
    'sendiri', 'sendirian', 'sendirinya', 'seolah', 'seolah-olah', 'seorang', 'sepanjang',
    'sepantasnya', 'sepantasnyalah', 'seperlunya', 'seperti', 'sepertinya', 'sepihak',
    'sering', 'seringnya', 'serta', 'serupa', 'sesaat', 'sesama', 'sesampai',
    'sesegera', 'sesekali', 'seseorang', 'sesuatu', 'sesuatunya', 'sesudah',
    'sesudahnya', 'setelah', 'setelahnya', 'setempat', 'setengah', 'seterusnya',
    'setiap', 'setiba', 'setibanya', 'setidak-tidaknya', 'setidaknya', 'setinggi',
    'sesuai', 'sewajarnya', 'sewaktu', 'siap', 'siapa', 'siapakah', 'siapapun',
    'sini', 'sinilah', 'soal', 'soalnya', 'suatu', 'sudah', 'sudahkah', 'sudahlah',
    'supaya', 'tadi', 'tadinya', 'tahu', 'tahun', 'tak', 'tambah', 'tambahnya',
    'tampak', 'tampaknya', 'tandas', 'tandasnya', 'tanpa', 'tanya', 'tanyakan',
    'tanyanya', 'tapi', 'tegas', 'tegasnya', 'telah', 'tempat', 'tengah', 'tentang',
    'tentu', 'tentulah', 'tentunya', 'tepat', 'terakhir', 'terasa', 'terbanyak',
    'terdahulu', 'terdapat', 'terdiri', 'terhadap', 'terhadapnya', 'teringat',
    'teringat-ingat', 'terjadi', 'terjadilah', 'terjadinya', 'terkira', 'terlalu',
    'terlebih', 'terlihat', 'termasuk', 'ternyata', 'tersampaikan', 'tersebut',
    'tersebutlah', 'tertentu', 'tertuju', 'terus', 'terutama', 'tetap', 'tetapi',
    'tiap', 'tiba', 'tiba-tiba', 'tidak', 'tidakkah', 'tidaklah', 'tiga', 'tinggi',
    'toh', 'tuju', 'tunjuk', 'turut', 'tutur', 'tuturnya', 'ucap', 'ucapnya', 'ujar',
    'ujarnya', 'umum', 'umumnya', 'ungkap', 'ungkapnya', 'untuk', 'usah', 'usai',
    'waduh', 'wah', 'wahai', 'waktu', 'waktunya', 'walau', 'walaupun', 'wong', 'yaitu',
    'yakin', 'yakni', 'yang'
}


def remove_variation_selectors(s: str) -> str:
    """Menghapus karakter pemilih variasi (variation selectors) dari string."""
    return s.replace(COEN, "").replace(VS16, "")

def _emoji_digit_word_to_int(name: str) -> Optional[int]:
    """Mengubah nama digit dalam deskripsi emoji menjadi integer."""
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
    """Mengonversi emoji huruf dan angka menjadi karakter ASCII yang setara."""
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
    """Normalisasi teks yang mengandung emoji, mengubahnya menjadi bentuk ASCII jika memungkinkan."""
    s = remove_variation_selectors(s)
    s = emoji_letter_digit_to_ascii(s)
    return s

def normalize_punct(text: str) -> str:
    """Menormalisasi tanda baca seperti tanda hubung, apostrof, dan karakter zero-width."""
    text = _RE_DASHES.sub("-", text)
    text = _RE_APOS.sub("'", text)
    text = _RE_ZW.sub("", text)
    return text

def normalize_chars(text: str) -> str:
    """Menormalisasi karakter Unicode, mengganti homoglyph, dan menghapus aksen."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = unicodedata.normalize("NFKC", text)
    return text.translate(_HOMO_TRANS)

def strip_symbol_chars(text: str) -> str:
    """Menghapus karakter yang termasuk dalam kategori simbol atau kontrol."""
    out = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith(('S', 'C')):
            continue
        out.append(ch)
    return "".join(out)

def safe_unidecode(text: str) -> str:
    """Mengonversi teks ke format ASCII dengan aman, mempertahankan karakter non-ASCII yang bukan huruf/angka."""
    out = []
    for ch in text:
        out.append(unidecode(ch) if ch.isalpha() or ch.isdigit() else ch)
    return "".join(out)

def remove_urls_mentions_hashtags(text: str) -> str:
    """Menghapus URL dan mention pengguna dari teks."""
    text = _RE_URLS.sub(" ", text)
    text = _RE_MENTIONS.sub(" ", text)
    return text

def remove_bracket(text: str) -> str:
    """Menghapus semua jenis tanda kurung dari teks."""
    return _RE_BRACKETS.sub("", text)

def remove_timestamps(s: str) -> str:
    """Menghapus format waktu (timestamp) dari string."""
    return _RE_TIMESTAMPS.sub(" ", s)

def handle_intraword_symbols(text: str) -> str:
    """Menangani simbol yang berada di dalam kata dengan mengubah separator keras menjadi spasi atau menghapusnya."""
    text = re.sub(rf"[{HARD_SEPARATORS}]+", " ", text)
    text = re.sub(r"(?<=\w)[^\w\s]+(?=\w)", "", text)
    text = re.sub(r"[^\w\s]+", " ", text)
    return text.strip()

def keep_alnum_and_space(text: str) -> str:
    """Hanya mempertahankan karakter alfanumerik, spasi, dan beberapa simbol tertentu."""
    return re.sub(r"[^0-9a-zA-Z@!\$%]+", " ", text)

def squeeze_spaces(text: str) -> str:
    """Mengganti beberapa spasi berurutan menjadi satu spasi tunggal."""
    return re.sub(r"\s+", " ", text).strip()

def rejoin_split_letters(tokens: List[str]) -> List[str]:
    """Menggabungkan kembali huruf-huruf yang terpisah spasi menjadi satu kata."""
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
                word += ''.join(digits)
                j = k
            
            if any(ch in VOWELS for ch in word) and 3 <= len(word) <= 24:
                out.append(word)
                i = j
                continue

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

def map_chars(tok: str) -> str:
    """Memetakan karakter leet speak menjadi huruf biasa, kecuali untuk pola tertentu."""
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

@lru_cache(maxsize=1024)
def _find_best_match(letters_only: str) -> tuple:
    best, best_ratio = None, 0.0
    for cand in DOMAIN_WORDS:
        r = difflib.SequenceMatcher(None, letters_only, cand).ratio()
        if r > best_ratio:
            best, best_ratio = cand, r
    return best, best_ratio

def fix_infix_digits_with_domain(tok: str, thr: float = 0.80) -> str:
    """Memperbaiki kata yang mengandung angka di tengah menggunakan pencocokan fuzzy domain."""
    t = tok.lower()
    if not re.search(r'[a-z]\d+[a-z]', t):
        return tok

    letters_only = re.sub(r'[^a-z]', '', t)
    if len(letters_only) < 3:
        return tok

    best, best_ratio = _find_best_match(letters_only)

    if best and best_ratio >= thr:
        if letters_only[0] == best[0] or letters_only[-2:] == best[-2:]:
            return best
    return tok

def squeeze_repeats(token: str, max_repeat: int = 2) -> str:
    """Mengurangi karakter yang berulang secara berlebihan dalam satu token."""
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
    """Melakukan normalisasi kata-kata plesetan atau bahasa gaul dalam list token."""
    out = []
    for t in tokens:
        t = t.lower()
        
        if t.isdigit():
            out.append(t)
            continue

        if t in SUBS:
            out.append(SUBS[t])
            continue

        if _RE_ALNUM_MIX.fullmatch(t):
            out.append(t)
            continue
            
        t = map_chars(t)               
        t = SUBS.get(t, t)            
        t = squeeze_repeats(t)        
        t = fix_infix_digits_with_domain(t)
        t = SUBS.get(t, t)             
        
        out.append(t)
    return out

def remove_stopwords_fast(tokens):
    """Menghapus stop words dari list token dengan efisien."""
    return [word for word in tokens if word.lower() not in INDONESIAN_STOPWORDS]

def preprocess(text: str) -> str:
    """
    Fungsi utama untuk memproses teks sebelum analisis deteksi perjudian.
    
    Langkah-langkah:
    1. Normalisasi karakter dan simbol
    2. Pembersihan konten yang tidak relevan
    3. Penanganan simbol dalam kata dan spasi
    4. Pembersihan akhir sebelum tokenisasi
    5. Operasi tingkat token (penggabungan huruf, normalisasi plesetan)
    6. Penggabungan kembali token menjadi string
    """
    if not isinstance(text, str) or not text:
        return ""

    text = normalize_emoji_text(text)
    text = normalize_chars(text)    
    text = normalize_punct(text)
    
    text = remove_urls_mentions_hashtags(text)
    text = remove_timestamps(text)
    text = remove_bracket(text)
    
    text = handle_intraword_symbols(text)
    text = strip_symbol_chars(text)
    text = safe_unidecode(text)
    text = text.lower()
    
    text = keep_alnum_and_space(text)
    text = squeeze_spaces(text)

    tokens = text.split()
    tokens = rejoin_split_letters(tokens) 
    tokens = normalize_plesetan(tokens) 
    # tokens = remove_stopwords_fast(tokens, STOPWORDS_ID)  

    final_text = " ".join(tokens)
    return final_text
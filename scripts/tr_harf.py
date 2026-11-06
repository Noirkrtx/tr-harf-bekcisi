#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tr_harf.py: dosyalarda bozulmuş Türkçe harfleri bulur ve güvenli olanları onarır.

İki tür bozulmaya bakar:
  1. Mojibake: UTF-8 metnin cp1252/cp1254/latin-1/cp1253 ya da DOS kod sayfasıyla
     (cp857/cp850/cp437) yanlış okunması: "TÃ¼rkÃ§e", "T├╝rk├ğe", "ArkadaÅŸ";
     ve cp1254 baytlarının latin-1 diye okunması: "Arkadaþ", "ýþýk".
  2. ASCII'leşme: harfleri düşmüş Türkçe kelime: "cok", "icin", "gelistirildi".

Komutlar:
  tr_harf.py kontrol <dosya/dizin...> [--json]       sorun varsa çıkış kodu 1
  tr_harf.py onar <dosya...> [--yaz] [--json]          varsayılan kuru çalışma (diff)
  tr_harf.py hook [--onar]                             ajan hook'u: stdin JSON, sorun varsa çıkış 2

Saf Python 3.8+, bağımlılık yok. Sözlük: ../sozluk/tr-sozluk-*.txt.gz
"""
import argparse
import codecs
import difflib
import glob
import gzip
import io
import json
import os
import re
import sys
import time

SURUM = "0.1.0"
BURASI = os.path.dirname(os.path.abspath(__file__))
SOZLUK_DIZINI = os.environ.get("TR_HARF_SOZLUK") or os.path.join(os.path.dirname(BURASI), "sozluk")

# ---------------------------------------------------------------------------
# Harf yardımcıları
# ---------------------------------------------------------------------------
KATLA = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
                       "â": "a", "î": "i", "û": "u"})
TR_HARF = set("çğıöşüÇĞİÖŞÜ")


def tr_kucuk(s):
    return s.replace("I", "ı").replace("İ", "i").lower()


def tr_buyuk(s):
    return s.replace("i", "İ").replace("ı", "I").upper()


def katla(s):
    return tr_kucuk(s).translate(KATLA)


def harf_duzeni_uygula(asil, hedef):
    """Hedef kelimeye asıl kelimenin büyük/küçük harf düzenini uygular (Turkce -> Türkçe, TURKCE -> TÜRKÇE)."""
    if len(asil) != len(hedef):
        return hedef
    if asil.isupper() and len(asil) > 1:
        return tr_buyuk(hedef)
    return "".join(tr_buyuk(h) if a.isupper() else h for a, h in zip(asil, hedef))


def yalniz_harf_ekler(asil, hedef):
    """Düzeltme yalnız harf ekliyor mu (s -> ş gibi)? Var olan bir Türkçe harfi asla silmeyiz.
    Büyük ASCII 'I' hem 'İ' (i) hem 'I' (ı) olabilir."""
    if len(asil) != len(hedef):
        return False
    for x, y in zip(asil, hedef):
        if x == "I":
            if y not in "iı":
                return False
            continue
        x = tr_kucuk(x)
        if x == y:
            continue
        if x != y.translate(KATLA):
            return False
    return True


# ---------------------------------------------------------------------------
# Sözlük
# ---------------------------------------------------------------------------
class Sozluk:
    def __init__(self, dizin=SOZLUK_DIZINI):
        self.grup = {}      # anahtar -> (durum, hedef, biçimler)
        self.dil = set()    # Türkçe olduğunu gösteren yaygın ASCII kelimeler
        self.ozel_ascii = set()  # ASCII yazılışı da gerçek özel adlar (Durusu)
        self.i_ozel = set()
        self.i_bas = set()  # 'i' ile başlayan gerçek ASCII kelimeler: 'Ilk' aslında 'İlk'
        dosyalar = sorted(glob.glob(os.path.join(dizin, "tr-sozluk*.txt.gz")))
        if not dosyalar:
            raise SystemExit("tr_harf: sözlük bulunamadı: %s (TR_HARF_SOZLUK ile yol verilebilir)" % dizin)
        for yol in dosyalar:
            with gzip.open(yol, "rt", encoding="utf-8") as f:
                for satir in f:
                    p = satir.rstrip("\n").split("\t")
                    if p[0] == "T":
                        self.dil.add(p[1])
                    elif p[0] == "I":
                        self.i_bas.add(p[1])
                        if len(p) > 2 and p[2] == "P":
                            self.i_ozel.add(p[1])
                    elif p[0] == "O":
                        self.ozel_ascii.add(p[1])
                    elif p[0] in ("K", "B", "A"):
                        hedef = p[1]
                        bicim = {hedef}
                        if len(p) > 2 and p[2]:
                            bicim.update(p[2].split("|"))
                        ozel = len(p) > 3 and p[3] == "P"
                        self.grup[hedef.translate(KATLA)] = (p[0], hedef, frozenset(bicim), ozel)

    def bak(self, kelime):
        k = tr_kucuk(kelime)
        g = self.grup.get(k.translate(KATLA))
        if g is None and kelime[:1] == "I" and len(kelime) > 1:
            # 'Ilk', 'Iptal', 'Ic': baştaki I noktalı İ olabilir
            k2 = "i" + tr_kucuk(kelime[1:])
            g2 = self.grup.get(k2.translate(KATLA))
            if g2 is not None:
                return k, g2
            if k2 in self.i_bas and k not in self.i_bas:
                return k, ("K", k2, frozenset([k2]), k2 in self.i_ozel)
        return k, g


_SOZLUK = None


def sozluk():
    global _SOZLUK
    if _SOZLUK is None:
        _SOZLUK = Sozluk()
    return _SOZLUK


# ---------------------------------------------------------------------------
# Mojibake
# ---------------------------------------------------------------------------
# İzin verilen çözüm karakterleri: Latin harfleri, yaygın noktalama ve simgeler, emoji.
def _izinli(ch, ic=False):
    """Çözümde izin verilen karakter mi? ic=True: çift kodlamanın ara turu (C1 denetim karakterleri
    ve Latin Genişletilmiş-B de geçebilir, son sonuçta yeniden denetlenir)."""
    o = ord(ch)
    if (0xA0 <= o <= 0x17F or 0x2010 <= o <= 0x206F or 0x2070 <= o <= 0x20CF or 0x2100 <= o <= 0x218F
            or 0x2190 <= o <= 0x21FF or 0x2200 <= o <= 0x22FF or 0x2500 <= o <= 0x257F
            or 0x2600 <= o <= 0x27BF or 0x1F300 <= o <= 0x1FAFF):
        return True
    return ic and (0x80 <= o <= 0x9F or 0x180 <= o <= 0x24F or 0x2B0 <= o <= 0x2FF)


# Başka alfabeler (Kiril, Yunan, Arapça, İbranice): yalnız en az iki harflik bir çözümde kabul edilir;
# tek harf ("DAĞ’" -> Kiril В) Türkçe metindeki rastlantı olabilir.
def _alfabe(ch):
    return 0x370 <= ord(ch) <= 0x6FF


def _harita(kodlamalar):
    h = {}
    for kod in kodlamalar:
        for b in range(0x80, 0x100):
            try:
                ch = bytes([b]).decode(kod)
            except UnicodeDecodeError:
                continue
            h.setdefault(ch, b)
    return h


def _desen(h):
    def sinif(lo, hi):
        return "[" + "".join(re.escape(c) for c, b in h.items() if lo <= b <= hi) + "]"
    l2, l3, l4, d = sinif(0xC2, 0xDF), sinif(0xE0, 0xEF), sinif(0xF0, 0xF4), sinif(0x80, 0xBF)
    return re.compile("(?:%s%s|%s%s{2}|%s%s{3})+" % (l2, d, l3, d, l4, d))


# Windows ailesi tek harita (çakışma yok); DOS kod sayfaları ayrı ayrı (aralarında çakışma var).
AILELER = [("cp1252/cp1254/latin-1", _harita(["cp1252", "cp1254", "cp1253", "latin-1"]))]
for _k in ("cp857", "cp850", "cp437"):
    AILELER.append((_k, _harita([_k])))
AILELER = [(ad, h, _desen(h)) for ad, h in AILELER]

# cp1254 baytlarının cp1252/latin-1 diye okunması (eski site, altyazı): yalnız şu altı harf bozulur
TEK_BAYT = str.maketrans({"ý": "ı", "þ": "ş", "ð": "ğ", "Ý": "İ", "Þ": "Ş", "Ð": "Ğ"})
TEK_BAYT_DESEN = re.compile(r"[^\W\d_]*[ýþðÝÞÐ][^\W\d_]*")
def _ara(a, b):
    """Düzenli ifade için karakter aralığı (kaynakta kaçış dizisi kullanmadan)."""
    return re.escape(chr(a)) + "-" + re.escape(chr(b))


_C1 = _ara(0x80, 0x9F)
_YUNAN = _ara(0x370, 0x3FF) + re.escape(chr(0x192))
_LATIN = "A-Za-z" + _ara(0xC0, 0x17F)
YEDEK = chr(0xFFFD)  # Unicode yedek karakteri (çözülemeyen bayt)
SORU_VE_YEDEK = "?" + YEDEK
_YEDEK = re.escape(YEDEK)
# 'Ã', 'Ä', 'Å' + cp1252 devam baytı: onarılamamış UTF-8 kalıntısı; C1 denetim karakteri; yedek karakter;
# Latin harfine yapışık Yunan harfi ya da ƒ (claude-code#6246, hermes-agent#149025 biçimleri)
KALINTI_DESEN = re.compile(
    "[ÃÄÅ][" + _ara(0x80, 0xBF) + _ara(0x152, 0x178) + re.escape(chr(0x192) + chr(0x2C6) + chr(0x2DC))
    + _ara(0x2013, 0x203A) + re.escape(chr(0x20AC) + chr(0x2122)) + "?" + _YEDEK + "]"
    + "|[" + _C1 + "]|" + _YEDEK
    + "|(?<=[" + _LATIN + "])[" + _YUNAN + "]+|[" + _YUNAN + "]+(?=[" + _LATIN + "])")
SORU_DESEN = re.compile(r"(?<=[^\W\d_])[?" + _YEDEK + r"]+(?=[^\W\d_])")


def _coz(parca, h, ic=False):
    """Bir eşleşmeyi UTF-8 olarak çözer; çözülemeyen ya da izinsiz sonuçta None."""
    try:
        b = bytes(h[c] for c in parca)
        s = b.decode("utf-8")
    except (KeyError, UnicodeDecodeError):
        return None
    yabanci = sum(1 for c in s if _alfabe(c))
    if yabanci and (yabanci < 2 or yabanci != sum(1 for c in s if c.isalpha())):
        return None
    if not all(_izinli(c, ic) or _alfabe(c) for c in s):
        return None
    return s


def mojibake_bul(metin):
    """[(bas, son, bulunan, onarim, kodlama)] döndürür. Çift kodlamayı (Ã„Â±) tur tur çözer.
    Önce Windows ailesi, sonra DOS kod sayfaları; çakışan aralıklar atlanır."""
    sonuc = []

    def cakisir(b, s):
        return any(b < y and x < s for x, y, *_ in sonuc)

    for ad, h, desen in AILELER:
        for m in desen.finditer(metin):
            parca = m.group(0)
            if cakisir(m.start(), m.end()):
                continue
            cozum = _coz(parca, h, ic=True)
            if cozum is None:
                continue
            # çift kodlama: çözüm yine mojibake ise bir tur daha
            for _ in range(2):
                icler = list(desen.finditer(cozum))
                if not icler:
                    break
                yeni = cozum
                for im in reversed(icler):
                    c2 = _coz(im.group(0), h, ic=True)
                    if c2 is not None:
                        yeni = yeni[:im.start()] + c2 + yeni[im.end():]
                if yeni == cozum:
                    break
                cozum = yeni
            if not all(_izinli(c) or _alfabe(c) for c in cozum):
                continue  # ara turda kalan denetim karakteri vb.: güvenli değil, dokunma
            sonuc.append((m.start(), m.end(), parca, cozum, ad))
    sonuc.sort()
    return sonuc


# ---------------------------------------------------------------------------
# Dosya türüne göre metin bölgeleri
# ---------------------------------------------------------------------------
METIN_UZANTI = {".md", ".mdx", ".markdown", ".txt", ".rst", ".adoc", ".org", ".tex", ".srt", ".vtt",
                ".csv", ".tsv", ".html", ".htm", ".xml", ".svg", ".po", ".pot", ".ini", ".cfg", ".conf",
                ".properties", ".strings", ".arb", ".tr"}
JSON_UZANTI = {".json", ".jsonl", ".ipynb"}
YAML_UZANTI = {".yaml", ".yml", ".toml"}
KOD_C = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".java", ".kt", ".kts", ".swift", ".dart", ".c", ".h",
         ".cc", ".cpp", ".hpp", ".cs", ".go", ".rs", ".php", ".scala", ".vue", ".svelte", ".css", ".scss", ".less",
         ".groovy", ".gradle", ".m", ".mm", ".sql", ".lua", ".zig"}
KOD_HASH = {".py", ".pyi", ".rb", ".sh", ".bash", ".zsh", ".fish", ".ps1", ".pl", ".r", ".jl", ".ex", ".exs",
            ".nim", ".coffee", ".mk", ".dockerfile", ".tf", ".hcl", ".nix", ".cmake"}
JSX_UZANTI = {".tsx", ".jsx", ".vue", ".svelte", ".html", ".htm"}
TUM_UZANTI = METIN_UZANTI | JSON_UZANTI | YAML_UZANTI | KOD_C | KOD_HASH
ADSIZ_DOSYA = {"makefile", "dockerfile", "readme", "license", "changelog", "agents.md", "claude.md"}
ATLA_DIZIN = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", ".cache",
              "vendor", "target", ".tox", ".mypy_cache", ".idea", ".hg", ".svn"}


def _bolge_kod(metin, hash_yorum, c_yorum, jsx):
    """Kod dosyasında yorum ve string bölgeleri: [(bas, son, tur)] tur 'yorum' | 'dize' | 'jsx'."""
    bolgeler = []
    i, n = 0, len(metin)
    while i < n:
        c = metin[i]
        if c_yorum and metin.startswith("//", i):
            j = metin.find("\n", i)
            j = n if j < 0 else j
            bolgeler.append((i + 2, j, "yorum"))
            i = j
        elif c_yorum and metin.startswith("/*", i):
            j = metin.find("*/", i + 2)
            j = n if j < 0 else j
            bolgeler.append((i + 2, j, "yorum"))
            i = j + 2
        elif hash_yorum and c == "#":
            j = metin.find("\n", i)
            j = n if j < 0 else j
            bolgeler.append((i + 1, j, "yorum"))
            i = j
        elif c in "\"'`":
            uc = metin[i:i + 3]
            if hash_yorum and uc in ('"""', "'''"):
                j = metin.find(uc, i + 3)
                j = n if j < 0 else j
                bolgeler.append((i + 3, j, "dize"))
                i = j + 3
                continue
            j = i + 1
            while j < n and metin[j] != c:
                if metin[j] == "\\":
                    j += 1
                elif metin[j] == "\n" and c != "`":
                    break
                j += 1
            bolgeler.append((i + 1, min(j, n), "dize"))
            i = j + 1
        elif jsx and c == ">":
            j = i + 1
            while j < n and metin[j] not in "<>{}":
                j += 1
            if j < n and metin[j] in "<{" and j > i + 1 and re.search(r"[^\W\d_]{2,}", metin[i + 1:j]):
                bolgeler.append((i + 1, j, "jsx"))
            i = j if j > i + 1 else i + 1
        else:
            i += 1
    return bolgeler


def _bolge_json(metin):
    out = []
    for m in re.finditer(r'"((?:[^"\\\n]|\\.)*)"(\s*:)?', metin):
        if m.group(2):
            continue  # anahtar
        out.append((m.start(1), m.end(1), "dize"))
    return out


def _bolge_yaml(metin):
    out = []
    pos = 0
    for satir in metin.splitlines(True):
        govde = satir.rstrip("\r\n")
        m = re.match(r"^(\s*(?:-\s+)?)([\w.\-\"']+\s*[:=]\s?)(.*)$", govde)
        if m and not govde.lstrip().startswith("#"):
            bas = pos + len(m.group(1)) + len(m.group(2))
        elif govde.lstrip().startswith("#"):
            bas = pos + govde.index("#") + 1
        else:
            bas = pos + len(re.match(r"^\s*(?:-\s+)?", govde).group(0))
        out.append((bas, pos + len(govde), "dize"))
        pos += len(satir)
    return out


def _bolge_md(metin):
    """Markdown: kod blokları (``` ve ~~~), satır içi kod ve HTML yorumları dışında kalan her yer."""
    kapali = []
    for m in re.finditer(r"(?ms)^(\s*)(```|~~~)[^\n]*\n.*?^\s*\2[^\n]*$", metin):
        kapali.append((m.start(), m.end()))
    for m in re.finditer(r"(?s)^---\n.*?\n---\n", metin[:4000]):
        if m.start() == 0:
            # ön madde: yalnız değerler kalsın, anahtarlar maskelenir
            for km in re.finditer(r"(?m)^[\w-]+:", m.group(0)):
                kapali.append((km.start(), km.end()))
    for m in re.finditer(r"`[^`\n]+`|<!--.*?-->", metin, re.S):
        kapali.append((m.start(), m.end()))
    kapali.sort()
    out, pos = [], 0
    for b, s in kapali:
        if b > pos:
            out.append((pos, b, "metin"))
        pos = max(pos, s)
    if pos < len(metin):
        out.append((pos, len(metin), "metin"))
    return out


def bolgeler(metin, yol):
    ad = os.path.basename(yol).lower()
    uz = os.path.splitext(ad)[1]
    if uz in (".md", ".mdx", ".markdown"):
        return _bolge_md(metin)
    if uz in JSON_UZANTI:
        return _bolge_json(metin)
    if uz in YAML_UZANTI:
        return _bolge_yaml(metin)
    if uz in KOD_C:
        return _bolge_kod(metin, False, True, uz in JSX_UZANTI)
    if uz in KOD_HASH or ad in ("makefile", "dockerfile"):
        return _bolge_kod(metin, True, False, False)
    if uz in (".html", ".htm", ".xml", ".svg"):
        return _bolge_kod(metin, False, False, True)
    return [(0, len(metin), "metin")]


# Metin içinde maskelenen (dokunulmayan) parçalar
MASKE = re.compile(
    r"`[^`\n]+`"                                     # satır içi kod
    r"|(?:https?|ftp|file)://\S+|www\.\S+"
    r"|[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
    r"|\]\([^)]*\)"                                  # markdown bağlantı hedefi
    r"|<[^<>\n]{1,200}>"                             # HTML/JSX etiketi
    r"|\{\{.*?\}\}|\$\{[^}]*\}|\{[\w.]+\}|%\(?\w*\)?[sdif]"   # şablon yer tutucuları
    r"|(?:[\w.~-]*[/\\])+[\w.-]*"                    # dosya yolu
    r"|\b[\w-]+\.(?:py|js|ts|tsx|jsx|md|json|ya?ml|toml|txt|sh|html|css|go|rs|java|rb|php|lock|cfg|ini|gz|zip|exe)\b"
    r"|[@#$]\w+|\B--?[A-Za-z][\w-]*"
    r"|\b\w*[_\d]\w*\b"                              # snake_case, sayı içeren
    r"|\b[a-zçğıöşü]+[A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ]*\b"  # camelCase
    r"|\b[A-Z][a-z]+[A-Z]\w*\b"                     # PascalCase iç büyük harf (GitHub)
    r"|\b[a-z]+(?:-[a-z]+)+\b"                       # kebab-case (ASCII)
    r"|\b[A-ZÇĞİÖŞÜ]{1,3}\b"                         # kısaltma
)
KELIME = re.compile(r"[^\W\d_]+")


def _maskeli_parcalar(metin, bas, son):
    """Bölgeyi maskeye göre bölüp (b, s) aralıkları üretir."""
    pos = bas
    for m in MASKE.finditer(metin, bas, son):
        if m.start() > pos:
            yield pos, m.start()
        pos = max(pos, m.end())
    if pos < son:
        yield pos, son


# ---------------------------------------------------------------------------
# Çözümleme
# ---------------------------------------------------------------------------
class Bulgu(dict):
    pass


def _satir_sutun(satirbas, poz):
    import bisect
    i = bisect.bisect_right(satirbas, poz) - 1
    return i + 1, poz - satirbas[i] + 1


def _yoksay_satirlari(metin):
    """'tr-harf: yoksay' geçen satırlar ve 'tr-harf: kapat' ... 'tr-harf: ac' arası."""
    out, kapali = set(), False
    for no, s in enumerate(metin.splitlines(), 1):
        if "tr-harf: kapat" in s:
            kapali = True
        if kapali or "tr-harf: yoksay" in s:
            out.add(no)
        if "tr-harf: ac" in s:
            kapali = False
    return out


def _yoksay_dosyalari(yol):
    """Dosyanın dizininden yukarı doğru .tr-harf-yoksay dosyalarını bulur."""
    d = os.path.dirname(os.path.abspath(yol))
    for _ in range(30):
        p = os.path.join(d, ".tr-harf-yoksay")
        if os.path.isfile(p):
            yield d, p
        yeni = os.path.dirname(d)
        if yeni == d:
            break
        d = yeni


def _yoksay_kelimeleri(yol):
    """.tr-harf-yoksay: satır başına bir kelime; 'yol: kalıp' satırları dosya yolu kalıbıdır."""
    kel = set()
    for _, p in _yoksay_dosyalari(yol):
        with io.open(p, encoding="utf-8") as f:
            for x in f:
                x = x.strip()
                if x and not x.startswith("#") and not x.startswith("yol:"):
                    kel.add(tr_kucuk(x))
    return kel


def yol_yoksayiliyor(yol):
    import fnmatch
    tam = os.path.abspath(yol)
    for d, p in _yoksay_dosyalari(yol):
        goreli = os.path.relpath(tam, d).replace(os.sep, "/")
        with io.open(p, encoding="utf-8") as f:
            for x in f:
                x = x.strip()
                if x.startswith("yol:"):
                    kalip = x[4:].strip().rstrip("/")
                    if fnmatch.fnmatch(goreli, kalip) or goreli.startswith(kalip + "/"):
                        return True
    return False


def cozumle(metin, yol="metin.txt", yoksay=None):
    """Metni çözümler. Bulgular: tur in {mojibake, tek-bayt, kalinti, kayip-harf, ascii, belirsiz}."""
    sz = sozluk()
    yoksay = yoksay or set()
    satirbas = [0] + [m.end() for m in re.finditer("\n", metin)]
    yoksay_satir = _yoksay_satirlari(metin)
    bulgular = []

    def ekle(tur, b, s, bulunan, oneri, kesin, aciklama):
        satir, sutun = _satir_sutun(satirbas, b)
        if satir in yoksay_satir:
            return
        bulgular.append(Bulgu(tur=tur, satir=satir, sutun=sutun, bas=b, son=s, bulunan=bulunan,
                              oneri=oneri, kesin=kesin, aciklama=aciklama))

    bolge = bolgeler(metin, yol)
    kod_dosyasi = any(t in ("yorum", "dize", "jsx") for _, _, t in bolge)

    # 1) Mojibake: bölgelerin içinde (kod bloklarında değil)
    moj_aralik = []
    tek_dogrulanan, tek_supheli = [], []
    for b, s, tur in bolge:
        parca = metin[b:s]
        if tur == "dize" and "\\u" in parca and os.path.splitext(yol)[1].lower() in JSON_UZANTI:
            # JSON kaçışlı mojibake: "T" + kaçışlı "Ã¼" -> "Tü" (claude-code#6246 biçimi)
            try:
                acik = json.loads('"' + parca + '"')
            except ValueError:
                acik = None
            if acik:
                bul = mojibake_bul(acik)
                if bul:
                    yeni = acik
                    for mb, ms, _, onarim, _ in reversed(bul):
                        yeni = yeni[:mb] + onarim + yeni[ms:]
                    ekle("mojibake", b, s, parca, json.dumps(yeni, ensure_ascii=False)[1:-1], True,
                         "JSON kaçışlı dizede UTF-8 baytları ayrı harf diye yazılmış")
                    moj_aralik.append((b, s))
                    continue
        for mb, ms, bulunan, onarim, kod in mojibake_bul(parca):
            ekle("mojibake", b + mb, b + ms, bulunan, onarim, True,
                 "UTF-8 metin %s olarak okunmuş" % kod)
            moj_aralik.append((b + mb, b + ms))
        win_parca = [(x.start(), x.end()) for x in AILELER[0][2].finditer(parca)]
        for m in TEK_BAYT_DESEN.finditer(parca):
            w = m.group(0)
            if len(w) < 2 or not any(c.isascii() or c in "çöüÇÖÜ" for c in w) or any(x <= m.end() and m.start() <= y for x, y in win_parca):
                continue  # 'Ð§ÐµÑ€' gibi UTF-8 mojibake parçası, cp1254 karışması değil
            aday = w.translate(TEK_BAYT)
            k, g = sz.bak(aday)
            if g and k in g[2]:
                tek_dogrulanan.append(1)
                ekle("tek-bayt", b + m.start(), b + m.end(), w, aday, True,
                     "cp1254 metin latin-1/cp1252 olarak okunmuş")
            elif len(w) > 2:
                tek_supheli.append((b + m.start(), b + m.end(), w, aday))

    # sözlükte doğrulanmayan cp1254 kelimeleri: dosyada en az iki doğrulanmış örnek varsa aynı bozulma
    # sayılır ve onarılır (ý, þ, ð Türkçe metinde başka türlü geçmez); yoksa yalnız işaretlenir
    kanit = len(tek_dogrulanan) >= 2
    for tb, ts, w, aday in tek_supheli:
        if kanit and re.fullmatch(r"[A-Za-zçöüÇÖÜâîûýþðÝÞÐ]+", w):
            ekle("tek-bayt", tb, ts, w, aday, True,
                 "cp1254 metin latin-1/cp1252 olarak okunmuş (dosyadaki diğer örneklerle doğrulandı)")
        else:
            ekle("tek-bayt", tb, ts, w, aday, False, "cp1254 karışması olabilir; sözlükte yok, elle bakın")

    def mojide(p, q=None):
        if q is None:
            return any(x <= p < y for x, y in moj_aralik)
        # kelime bir mojibake parçasına değiyor mu ('arac' + '─▒'): o zaman ASCII analizine sokma
        return any(x <= q and p <= y for x, y in moj_aralik)

    # 2) Kalıntılar (onarılamayan mojibake izleri) ve kayıp harf (? ya da �)
    for b, s, tur in bolge:
        for m in KALINTI_DESEN.finditer(metin, b, s):
            if not mojide(m.start()):
                ekle("kalinti", m.start(), m.end(), m.group(0), None, False,
                     "bozuk kodlama izi; otomatik onarılamadı")
        son_kayip = -1
        for m in (m for pb, ps in _maskeli_parcalar(metin, b, s) for m in SORU_DESEN.finditer(metin, pb, ps)):
            if m.start() < son_kayip:
                continue
            sol = m.start()
            while sol > b and (metin[sol - 1].isalpha() or metin[sol - 1] in SORU_VE_YEDEK):
                sol -= 1
            sag = m.end()
            while sag < s and (metin[sag].isalpha() or metin[sag] in SORU_VE_YEDEK):
                sag += 1
            son_kayip = sag
            w = metin[sol:sag]
            if YEDEK not in w and (tur in ("dize", "yorum") and kod_dosyasi):
                continue
            adaylar = _soru_adaylari(w, sz)
            if not adaylar and YEDEK not in w:
                continue  # '?' ama sözlükte karşılığı yok: büyük olasılıkla noktalama
            ekle("kayip-harf", sol, sag, w, adaylar[0] if len(adaylar) == 1 else None, False,
                 "harf yerine '?' ya da yedek karakter var" + (": aday " + ", ".join(adaylar[:4]) if adaylar else ""))

    # 3) ASCII'leşme: Türkçe olduğu anlaşılan bölgelerde
    ascii_say = harfli_say = 0
    # dosyada hep büyük harfle geçen kelime (Apis, Durusu) özel ad sayılır
    buyuk_say, kucuk_say = {}, {}
    for m in KELIME.finditer(metin):
        w = m.group(0)
        hedef_say = buyuk_say if (w[0].isupper() and not w.isupper()) else kucuk_say
        hedef_say[tr_kucuk(w)] = hedef_say.get(tr_kucuk(w), 0) + 1
    belirsizler = []
    for b, s, tur in _paragraflar(metin, bolge):
        kelimeler = []
        for pb, ps in _maskeli_parcalar(metin, b, s):
            for m in KELIME.finditer(metin, pb, ps):
                w = m.group(0)
                if len(w) < 2 or mojide(m.start(), m.end()):
                    continue
                kelimeler.append((m.start(), m.end(), w))
        if not kelimeler:
            continue
        if tur == "dize" and kod_dosyasi and len(kelimeler) < 2:
            continue  # tek kelimelik dize kod içinde çoğu zaman anahtar/tanımlayıcıdır
        isaret = 0
        adaylar = []
        harfli_burada = 0
        for kb, ks, w in kelimeler:
            k, g = sz.bak(w)
            if any(c in TR_HARF for c in w):
                isaret += 1
                harfli_burada += 1
            elif k in sz.dil:
                isaret += 1
            if g is None:
                continue
            if k in g[2]:
                if g[0] == "B" and k != g[1] and not any(c in TR_HARF for c in w):
                    secenek = sorted(x for x in g[2] if x != k and yalniz_harf_ekler(w, x))
                    if secenek:
                        adaylar.append(("belirsiz", kb, ks, w, [harf_duzeni_uygula(w, x) for x in secenek]))
                continue
            if k in yoksay:
                continue
            buyuk_bas = w[0].isupper() and not w.isupper()
            if buyuk_bas and k in sz.ozel_ascii:
                continue  # ASCII yazılışı da gerçek bir özel ad (Durusu, Ozan)
            ozel_supheli = buyuk_bas and not g[3] and (
                not _cumle_basi(metin, kb, b) or (buyuk_say.get(k, 0) >= 2 and not kucuk_say.get(k)))
            if g[0] == "K" and yalniz_harf_ekler(w, g[1]) and ozel_supheli:
                # cümle ortasında büyük harfli, hedefi özel ad değil: yabancı ya da yerel ad olabilir (Apis)
                adaylar.append(("belirsiz", kb, ks, w, [harf_duzeni_uygula(w, g[1])]))
            elif g[0] == "K" and yalniz_harf_ekler(w, g[1]):
                adaylar.append(("ascii", kb, ks, w, harf_duzeni_uygula(w, g[1])))
                if not any(c in TR_HARF for c in w):
                    isaret += 1
            elif g[0] == "B" and yalniz_harf_ekler(w, g[1]):
                secenek = sorted(x for x in g[2] if x != k and yalniz_harf_ekler(w, x))
                if secenek:
                    adaylar.append(("belirsiz", kb, ks, w, [harf_duzeni_uygula(w, x) for x in secenek]))
        # kesme işaretinden sonraki ek: kökün son ünlüsüne göre (Dunya'nin -> Dünya'nın)
        duzeltme = {a[1]: a[4] for a in adaylar if a[0] == "ascii"}
        ek_bas = {a[1] for a in adaylar}
        onceki = None
        for kb, ks, w in kelimeler:
            if (onceki and kb >= 2 and metin[kb - 1] in "'\u2019" and onceki[1] == kb - 1
                    and not any(c in TR_HARF for c in w)):
                kok_ = duzeltme.get(onceki[0], onceki[2])
                kk, kg = sz.bak(kok_)
                turkce_kok = any(c in TR_HARF for c in kok_) or kk in sz.dil or (kg is not None and kk in kg[2])
                uyumlu = ek_uyumla(kok_, w) if turkce_kok else None
                if uyumlu and uyumlu != w and yalniz_harf_ekler(w, tr_kucuk(uyumlu)):
                    adaylar = [a for a in adaylar if a[1] != kb]
                    adaylar.append(("ascii", kb, ks, w, uyumlu))
                elif uyumlu == w and kb in ek_bas:
                    adaylar = [a for a in adaylar if a[1] != kb]  # ek zaten uyumlu: belirsiz deme
            onceki = (kb, ks, w)
        oran = isaret / float(len(kelimeler))
        turkce = (isaret >= 2 and oran >= 0.25) or (isaret >= 1 and len(kelimeler) <= 3 and oran >= 0.5)
        if not turkce:
            continue
        harfli_say += harfli_burada
        for a in adaylar:
            if a[0] == "ascii":
                ascii_say += 1
                ekle("ascii", a[1], a[2], a[3], a[4], True, "Türkçe harfleri düşmüş")
            else:
                belirsizler.append(a)

    if ascii_say or any(x["tur"] in ("mojibake", "tek-bayt") for x in bulgular):
        for _, kb, ks, w, sec in belirsizler:
            if kb > 0 and metin[kb - 1] in "'\u2019":
                continue  # kesme işaretinden sonraki ek (response'un): belirsiz diye gürültü yapma
            ekle("belirsiz", kb, ks, w, None, False,
                 ("büyük harfle başlıyor, özel ad olabilir; Türkçe kelimeyse: " if len(sec) == 1 and w[0].isupper()
                  and k_bul(w) not in sz.grup.get(tr_kucuk(w).translate(KATLA), (0, 0, ()))[2]
                  else "ASCII biçimi de gerçek kelime; şu da olabilir: ") + ", ".join(sec))

    bulgular.sort(key=lambda x: x["bas"])
    ozet = {"ascii": ascii_say, "harfli_kelime": harfli_say,
            "karisik": bool(ascii_say >= 2 and harfli_say >= 3)}
    return bulgular, ozet


_KALIN, _INCE_YUV, _KALIN_YUV = set("aıouAIOU"), set("öüÖÜ"), set("ouOU")


def ek_uyumla(kok, ek):
    """Kesme işaretinden sonraki ASCII eki köke göre uyumlar; yalnız ünlüleri değiştirir (i->ı, u->ü).
    Belirsizse None."""
    son = None
    for c in reversed(kok):
        if c.lower() in "aeıioöuü" or c in "AEIİOÖUÜ":
            son = tr_kucuk(c)
            break
    if son is None:
        return None
    sabit = ""
    if tr_kucuk(ek).endswith("ki") and len(ek) > 2:
        ek, sabit = ek[:-2], ek[-2:]  # -ki eki uyuma girmez (Mars'taki, Ankara'daki)
    elif tr_kucuk(ek) == "ki":
        return ek
    out = []
    for c in ek:
        lc = tr_kucuk(c) if c != "I" else "ı"
        if lc in "aeıioöuü":
            kalin = son in "aıou"
            yuv = son in "oöuü"
            if lc in "ae":
                yeni = "a" if kalin else "e"
                if yeni != lc:
                    return None  # a/e değiştirmek harf eklemek değil: elle bakılsın
            elif lc in "iıuü":
                if lc in "iı":
                    yeni = ("ı" if not yuv else "u") if kalin else ("i" if not yuv else "ü")
                else:
                    yeni = ("u" if kalin else "ü")
                if yeni.translate(KATLA) != lc.translate(KATLA):
                    return None  # i/u arası değişim gerekiyor: ek ASCII'leşmeden başka biçimde yanlış
            else:
                yeni = lc
            son = yeni
            out.append(tr_buyuk(yeni) if c.isupper() else yeni)
        else:
            out.append(c)
    return "".join(out) + sabit


def k_bul(w):
    return tr_kucuk(w)


def _paragraflar(metin, bolge):
    """Metin bölgelerini boş satırlardan paragraflara böler; kod bölgeleri olduğu gibi kalır."""
    for b, s, tur in bolge:
        if tur != "metin":
            yield b, s, tur
            continue
        pos = b
        for m in re.finditer(r"\n[ \t]*\n", metin[b:s]):
            yield pos, b + m.start(), tur
            pos = b + m.end()
        yield pos, s, tur


def _cumle_basi(metin, poz, bolge_bas):
    """Kelime cümle, satır ya da başlık başında mı? (Büyük harf orada olağandır.)"""
    i = poz - 1
    while i >= bolge_bas and metin[i] in " \t\"'“‘(«*_>#-–•`[":
        i -= 1
    if i < bolge_bas:
        return True
    if metin[i] in ".!?:;\n|":
        return True
    satir_bas = metin.rfind("\n", 0, poz) + 1
    return metin[satir_bas:poz].lstrip().startswith("#")


def _soru_adaylari(w, sz):
    import itertools
    yerler = [i for i, c in enumerate(w) if c in SORU_VE_YEDEK]
    if not yerler or len(yerler) > 3:
        return []
    harfler = "çğıöşü"
    out = []
    for secim in itertools.product(harfler, repeat=len(yerler)):
        lst = list(w)
        buyuk = w.isupper()
        for i, h in zip(yerler, secim):
            lst[i] = tr_buyuk(h) if buyuk else h
        aday = "".join(lst)
        k, g = sz.bak(aday)
        if g and k in g[2] and aday not in out:
            out.append(aday)
    return out


# ---------------------------------------------------------------------------
# Dosya okuma / onarım
# ---------------------------------------------------------------------------
def dosya_oku(yol):
    """(metin, bom, kodlama, uyari) döndürür. UTF-8 değilse cp1254 dener."""
    with open(yol, "rb") as f:
        ham = f.read()
    if b"\x00" in ham[:4096]:
        return None, False, None, "ikili dosya"
    bom = ham.startswith(codecs.BOM_UTF8)
    if bom:
        ham = ham[3:]
    try:
        return ham.decode("utf-8"), bom, "utf-8", None
    except UnicodeDecodeError:
        pass
    metin = ham.decode("cp1254", errors="replace")
    return metin, False, "cp1254", "dosya UTF-8 değil; cp1254 (Windows Türkçe) gibi okunuyor"


def onarim_uygula(metin, bulgular):
    """Yalnız kesin bulguları uygular; çakışanları atlar."""
    out, pos, uygulanan = [], 0, []
    for b in sorted((x for x in bulgular if x["kesin"] and x["oneri"] is not None and x["tur"] != "kodlama"),
                    key=lambda x: x["bas"]):
        if b["bas"] < pos:
            continue
        out.append(metin[pos:b["bas"]])
        out.append(b["oneri"])
        pos = b["son"]
        uygulanan.append(b)
    out.append(metin[pos:])
    return "".join(out), uygulanan


def dosya_cozumle(yol):
    if yol_yoksayiliyor(yol):
        return None
    metin, bom, kodlama, uyari = dosya_oku(yol)
    if metin is None:
        return None
    bulgular, ozet = cozumle(metin, yol, _yoksay_kelimeleri(yol))
    if kodlama != "utf-8":
        bulgular.insert(0, Bulgu(tur="kodlama", satir=1, sutun=1, bas=0, son=0, bulunan=kodlama,
                                 oneri="utf-8", kesin=True, aciklama=uyari))
    return {"dosya": yol, "metin": metin, "bom": bom, "kodlama": kodlama, "bulgular": bulgular, "ozet": ozet}


def dosya_onar(yol):
    """Onarılmış metni ve doğrulama sonucunu döndürür (yazmaz)."""
    c = dosya_cozumle(yol)
    if c is None:
        return None
    yeni, uygulanan = onarim_uygula(c["metin"], c["bulgular"])
    # doğrulama: onarılmış metinde mojibake kalmamalı, yeni ASCII sorun doğmamalı
    sonra, _ = cozumle(yeni, yol, _yoksay_kelimeleri(yol))
    kalinti_once = sum(1 for b in c["bulgular"] if b["tur"] == "kalinti")
    kalinti_sonra = sum(1 for b in sonra if b["tur"] == "kalinti")
    gecerli = all(b["tur"] != "mojibake" for b in sonra) and kalinti_sonra <= kalinti_once
    if not gecerli:
        # güvenli taraf: yalnız ASCII ve tek-bayt onarımlarını uygula
        yeni, uygulanan = onarim_uygula(c["metin"], [b for b in c["bulgular"] if b["tur"] != "mojibake"])
    c.update(yeni=yeni, uygulanan=uygulanan, dogrulandi=gecerli,
             kodlama_degisti=c["kodlama"] != "utf-8")
    return c


def dosyalari_topla(yollar, hepsi=False):
    for y in yollar:
        if os.path.isdir(y):
            for kok, dizinler, dosyalar in os.walk(y):
                dizinler[:] = sorted(d for d in dizinler if d not in ATLA_DIZIN and not d.startswith("."))
                for d in sorted(dosyalar):
                    uz = os.path.splitext(d)[1].lower()
                    if hepsi or uz in TUM_UZANTI or d.lower() in ADSIZ_DOSYA:
                        yield os.path.join(kok, d)
        elif os.path.isfile(y):
            yield y
        else:
            print("tr_harf: bulunamadı: %s" % y, file=sys.stderr)


# ---------------------------------------------------------------------------
# Çıktı
# ---------------------------------------------------------------------------
ETIKET = {"mojibake": "MOJIBAKE", "tek-bayt": "KODLAMA", "kalinti": "KALINTI", "kayip-harf": "KAYIP",
          "ascii": "HARFSIZ", "belirsiz": "BELIRSIZ", "kodlama": "KODLAMA"}


def bulgu_satiri(yol, b):
    if b["oneri"]:
        ne = "%s -> %s" % (b["bulunan"], b["oneri"])
    else:
        ne = b["bulunan"]
    durum = "" if b["kesin"] else "  (elle bakın)"
    return "%s:%d:%d: %s %s  [%s]%s" % (yol, b["satir"], b["sutun"], ETIKET[b["tur"]], ne, b["aciklama"], durum)


def sorunlu(bulgular):
    return [b for b in bulgular if b["tur"] != "belirsiz"]


def _json_bulgu(b):
    return {k: b[k] for k in ("tur", "satir", "sutun", "bulunan", "oneri", "kesin", "aciklama")}


def komut_kontrol(a):
    t0 = time.time()
    rapor, sorun_var, toplam = [], False, 0
    for yol in dosyalari_topla(a.yollar, a.hepsi):
        c = dosya_cozumle(yol)
        if c is None:
            continue
        toplam += 1
        bl = c["bulgular"]
        if sorunlu(bl):
            sorun_var = True
        if a.json:
            rapor.append({"dosya": yol, "kodlama": c["kodlama"], "ozet": c["ozet"],
                          "bulgular": [_json_bulgu(b) for b in bl]})
        else:
            for b in bl[: a.en_cok]:
                print(bulgu_satiri(yol, b))
            if len(bl) > a.en_cok:
                print("%s: ... %d bulgu daha" % (yol, len(bl) - a.en_cok))
            if c["ozet"]["karisik"]:
                print("%s: UYARI dosyada %d doğru harfli kelime ve %d harfsiz kelime var; metin sonradan "
                      "bozulmuş olabilir" % (yol, c["ozet"]["harfli_kelime"], c["ozet"]["ascii"]))
    if a.json:
        print(json.dumps({"surum": SURUM, "dosya_sayisi": toplam, "sorun": sorun_var,
                          "sure_sn": round(time.time() - t0, 3), "dosyalar": rapor}, ensure_ascii=False, indent=1))
    elif not sorun_var:
        print("tr_harf: %d dosya, sorun yok" % toplam, file=sys.stderr)
    return 1 if sorun_var else 0


def komut_onar(a):
    sorun_var = False
    rapor = []
    for yol in dosyalari_topla(a.yollar, a.hepsi):
        c = dosya_onar(yol)
        if c is None:
            continue
        kalan = [b for b in c["bulgular"] if b not in c["uygulanan"] and b["tur"] != "kodlama"]
        degisti = c["yeni"] != c["metin"] or c["kodlama_degisti"]
        if sorunlu(c["bulgular"]):
            sorun_var = True
        if a.json:
            rapor.append({"dosya": yol, "degisti": degisti, "yazildi": bool(a.yaz and degisti),
                          "dogrulandi": c["dogrulandi"],
                          "uygulanan": [_json_bulgu(b) for b in c["uygulanan"]],
                          "elle_bakilacak": [_json_bulgu(b) for b in kalan]})
        else:
            if degisti:
                fark = difflib.unified_diff(c["metin"].splitlines(True), c["yeni"].splitlines(True),
                                            yol + " (önce)", yol + " (sonra)")
                sys.stdout.writelines(fark)
                if not c["yeni"].endswith("\n"):
                    print()
            for b in kalan:
                print(bulgu_satiri(yol, b))
            if not c["dogrulandi"]:
                print("%s: mojibake onarımı doğrulanamadı; yalnız harf onarımları önerildi" % yol)
        if a.yaz and degisti:
            veri = c["yeni"].encode("utf-8")
            if c["bom"]:
                veri = codecs.BOM_UTF8 + veri
            with open(yol, "wb") as f:
                f.write(veri)
            if not a.json:
                print("%s: %d onarım yazıldı%s" % (yol, len(c["uygulanan"]),
                                                    ", dosya UTF-8'e çevrildi" if c["kodlama_degisti"] else ""),
                      file=sys.stderr)
        elif degisti and not a.json:
            print("%s: %d onarım önerildi (yazmak için --yaz)" % (yol, len(c["uygulanan"])), file=sys.stderr)
    if a.json:
        print(json.dumps({"surum": SURUM, "dosyalar": rapor}, ensure_ascii=False, indent=1))
    return 1 if sorun_var else 0


# ---------------------------------------------------------------------------
# Ajan hook'u (Claude Code ve Codex PostToolUse; Hermes eklentisi de bu işlevi çağırır)
# ---------------------------------------------------------------------------
YAMA_DOSYA = re.compile(r"^\*\*\* (?:Add|Update) File: (.+)$|^\*\*\* Move to: (.+)$", re.M)


def hook_dosyalari(veri):
    """Hook girdisinden değişen dosya yollarını çıkarır."""
    girdi = veri.get("tool_input") or veri.get("args") or {}
    cwd = veri.get("cwd") or os.getcwd()
    yollar = []
    if isinstance(girdi, dict):
        for anahtar in ("file_path", "path", "notebook_path"):
            if isinstance(girdi.get(anahtar), str):
                yollar.append(girdi[anahtar])
        for anahtar in ("command", "patch", "input"):
            v = girdi.get(anahtar)
            if isinstance(v, list):
                v = " ".join(str(x) for x in v)
            if isinstance(v, str) and "*** " in v:
                for m in YAMA_DOSYA.finditer(v):
                    yollar.append((m.group(1) or m.group(2)).strip())
        for anahtar in ("edits",):
            for e in girdi.get(anahtar) or []:
                if isinstance(e, dict) and isinstance(e.get("file_path"), str):
                    yollar.append(e["file_path"])
    tam = []
    for y in yollar:
        if not os.path.isabs(y):
            y = os.path.join(cwd, y)
        if y not in tam and os.path.isfile(y):
            uz = os.path.splitext(y)[1].lower()
            if uz in TUM_UZANTI or os.path.basename(y).lower() in ADSIZ_DOSYA:
                tam.append(y)
    return tam


def kisa_yol(yol, cwd=None):
    """Ajana gösterilecek yolu kısaltır: çalışma dizini altındaysa göreli, ev dizini altındaysa ~/."""
    tam = os.path.abspath(yol)
    cwd = os.path.abspath(cwd or os.getcwd())
    if tam.startswith(cwd + os.sep):
        return os.path.relpath(tam, cwd)
    ev = os.path.expanduser("~")
    if ev and ev != "~" and tam.startswith(ev + os.sep):
        return "~" + tam[len(ev):]
    return tam


def hook_raporu(yollar, onar=False, en_cok=15, cwd=None):
    """Sorun yoksa None; varsa ajana gösterilecek metni döndürür."""
    satirlar, onarilan = [], []
    for yol in yollar:
        gor = kisa_yol(yol, cwd)
        if onar:
            c = dosya_onar(yol)
            if c is None:
                continue
            if c["uygulanan"] and c["yeni"] != c["metin"]:
                veri = c["yeni"].encode("utf-8")
                if c["bom"]:
                    veri = codecs.BOM_UTF8 + veri
                with open(yol, "wb") as f:
                    f.write(veri)
                onarilan.append("%s: %d harf onarıldı (dosyayı yeniden oku)" % (gor, len(c["uygulanan"])))
            bl = [b for b in c["bulgular"] if b not in c["uygulanan"] and b["tur"] != "belirsiz"]
        else:
            c = dosya_cozumle(yol)
            if c is None:
                continue
            bl = sorunlu(c["bulgular"])
        for b in bl[:en_cok]:
            satirlar.append(bulgu_satiri(gor, b))
        if len(bl) > en_cok:
            satirlar.append("%s: ... %d bulgu daha" % (gor, len(bl) - en_cok))
    if not satirlar and not onarilan:
        return None
    betik = kisa_yol(os.path.abspath(__file__), "/nonexistent-cwd")
    mesaj = ["tr-harf-bekcisi: yazdığın dosyada bozuk Türkçe harf var."]
    mesaj += onarilan
    if satirlar:
        mesaj += satirlar
        mesaj.append("Kesin olanları (-> ile gösterilen) düzelt; 'elle bakın' yazanlarda bağlama göre karar ver. "
                     "Toplu onarım için: python3 %s onar <dosya> --yaz" % (('"%s"' % betik) if " " in betik else betik))
        mesaj.append("(Turkish characters were lost or garbled in the file you wrote. Fix them using the "
                     "suggestions above.)")
    return "\n".join(mesaj)


def komut_hook(a):
    try:
        veri = json.load(sys.stdin)
    except ValueError:
        return 0  # bozuk girdi: ajanı engelleme
    rapor = hook_raporu(hook_dosyalari(veri), onar=a.onar, cwd=veri.get("cwd"))
    if rapor is None:
        return 0
    print(rapor, file=sys.stderr)
    return 2


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tr_harf.py", description="Bozulmuş Türkçe harfleri bulur ve onarır.")
    ap.add_argument("--surum", action="version", version=SURUM)
    alt = ap.add_subparsers(dest="komut")
    k = alt.add_parser("kontrol", help="dosya ya da dizinleri tara")
    k.add_argument("yollar", nargs="+")
    k.add_argument("--json", action="store_true")
    k.add_argument("--hepsi", action="store_true", help="dizinde uzantısı bilinmeyen dosyalara da bak")
    k.add_argument("--en-cok", type=int, default=200, help="dosya başına en çok bulgu satırı")
    o = alt.add_parser("onar", help="güvenli onarımları göster ya da yaz")
    o.add_argument("yollar", nargs="+")
    o.add_argument("--yaz", action="store_true", help="dosyaya yaz (yoksa yalnız fark gösterilir)")
    o.add_argument("--json", action="store_true")
    o.add_argument("--hepsi", action="store_true")
    h = alt.add_parser("hook", help="ajan hook'u: stdin'den JSON okur, sorun varsa stderr + çıkış 2")
    h.add_argument("--onar", action="store_true", help="kesin onarımları dosyaya hemen yaz")
    a = ap.parse_args(argv)
    if a.komut == "kontrol":
        return komut_kontrol(a)
    if a.komut == "onar":
        return komut_onar(a)
    if a.komut == "hook":
        return komut_hook(a)
    ap.print_help()
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows konsolunda kendimiz mojibake üretmeyelim
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    sys.exit(main())

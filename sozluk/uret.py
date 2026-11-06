#!/usr/bin/env python3
"""Sözlüğü kaynak verilerden yeniden üretir: sozluk/tr-sozluk-1.txt.gz, tr-sozluk-2.txt.gz

Kaynaklar (indirilir ya da --yerel dizinden okunur):
  1. hermitdave/FrequencyWords, content/2018/tr/tr_full.txt ve en/en_50k.txt
     (OpenSubtitles2018 sıklık listeleri; içerik CC-BY-SA-4.0)
  2. ahmetaa/zemberek-nlp, morphology/src/main/resources/tr/ altındaki master-dictionary.dict,
     non-tdk.dict, proper.dict, locations-tr.dict, person-names.dict (Apache-2.0)

Çıktı biçimi (satır başına bir grup, UTF-8, gzip):
  K<TAB>hedef[<TAB><TAB>P]              kesin: ASCII biçimi gerçek bir kelime değil
  B<TAB>hedef<TAB>diğer|diğer[<TAB>P]  belirsiz: ASCII biçimi ya da başka bir harfli biçim de gerçek
  A<TAB>hedef<TAB>diğer|diğer[<TAB>P]  ASCII baskın: ASCII biçim çok daha yaygın (bu/bü); hiç işaretlenmez
      P: hedef bir özel ad ya da özel ad + ek (Türkçe, İstanbul'da); cümle ortasında büyük harfle
         yazılmış ASCII kelime yalnız hedef özel adsa kesin sayılır
  O<TAB>ad                     ASCII yazılışı da gerçek olan özel ad (Durusu, Ozan): büyük harfle gelirse dokunulmaz
  T<TAB>kelime                 Türkçe olduğunu gösteren yaygın ASCII kelime (dil kapısı için)
  I<TAB>kelime                 'i' ile başlayan gerçek ASCII kelime ('Ilk' görülürse 'İlk' önerilir)

Kullanım:
  python3 sozluk/uret.py                 # kaynakları indirir
  python3 sozluk/uret.py --yerel DIZIN   # DIZIN/tr_full.txt, en_50k.txt, master-dictionary.dict, non-tdk.dict
"""
import argparse
import collections
import gzip
import io
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ek_uyumu import kok_ek_gercek  # noqa: E402

KAYNAKLAR = {
    "tr_full.txt": "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/tr/tr_full.txt",
    "en_50k.txt": "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/en/en_50k.txt",
    "master-dictionary.dict": "https://raw.githubusercontent.com/ahmetaa/zemberek-nlp/master/morphology/src/main/resources/tr/master-dictionary.dict",
    "non-tdk.dict": "https://raw.githubusercontent.com/ahmetaa/zemberek-nlp/master/morphology/src/main/resources/tr/non-tdk.dict",
    "proper.dict": "https://raw.githubusercontent.com/ahmetaa/zemberek-nlp/master/morphology/src/main/resources/tr/proper.dict",
    "locations-tr.dict": "https://raw.githubusercontent.com/ahmetaa/zemberek-nlp/master/morphology/src/main/resources/tr/locations-tr.dict",
    "person-names.dict": "https://raw.githubusercontent.com/ahmetaa/zemberek-nlp/master/morphology/src/main/resources/tr/person-names.dict",
}

# Ayarlar (README'deki ölçüm bu değerlerle yapıldı)
EN_AZ_SAYI = 20          # harfli biçim derlemde en az bu kadar geçmeli
KOK_ORAN = 0.005        # sözlük kökü olan harfli biçim için daha düşük eşik (şayi gibi eskimiş kökler elensin)
GERCEK_ORAN = 0.03       # başka bir biçim en sık biçimin %3'ünden sık geçiyorsa o da gerçek sayılır
EN_YAYGIN_INGILIZCE = 5000
T_SAYISI = 400

KATLA = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
                       "â": "a", "î": "i", "û": "u"})
HARFLI = set("çğıöşüâîû")
SAPKASIZ = str.maketrans({"â": "a", "î": "i", "û": "u"})
KELIME = re.compile(r"^[a-zçğıöşüâîû]+$")


def tr_kucuk(s):
    return s.replace("I", "ı").replace("İ", "i").lower()


def katla(s):
    return s.translate(KATLA)


def oku(yerel, ad):
    if yerel:
        yol = os.path.join(yerel, ad)
        return io.open(yol, encoding="utf-8").read().splitlines()
    print("indiriliyor:", KAYNAKLAR[ad], file=sys.stderr)
    with urllib.request.urlopen(KAYNAKLAR[ad], timeout=120) as y:
        return y.read().decode("utf-8").splitlines()


ASCII_GERCEK_ORAN = 0.25
BASKIN_ORAN = 0.1         # harfli biçim ASCII biçimin %10'undan azsa grup A (ASCII baskın)
KOK_ASCII_ORAN = 0.02
EKLER = ("lar", "ler", "li", "lu", "si", "su", "i", "u", "e", "a", "de", "da", "te", "ta",
         "den", "dan", "ten", "tan", "in", "un", "nin", "nun", "ma", "me", "mak", "mek",
         "ci", "cu", "ce", "ca", "di", "du", "ti", "tu", "ki", "sini", "suna", "sine")


def kok_ek(w, kok):
    """ASCII kelime, 4+ harfli ASCII bir kök + yaygın ASCII ek ise gerçek kelime olabilir (sinirli, yasama)."""
    for ek in EKLER:
        if w.endswith(ek):
            k = w[: len(w) - len(ek)]
            if len(k) >= 4 and k in kok:
                return True
    return False


def kismi_katlama(w, hedef):
    """w, hedefin bazı harfleri ASCII'ye düşürülerek elde ediliyorsa True."""
    if len(w) != len(hedef):
        return False
    return all(a == b or a == katla(b) for a, b in zip(w, hedef))


def alternatif_esigi(w, hedef):
    """Harfli başka bir biçimin gerçek kelime sayılması için gereken oran.
    Hedefin bazı harfleri düşmüş biçim (açik, günes) çoğunlukla yazım hatasıdır ama sıklık/şıklık
    gibi gerçek çiftler de var: %3 eşiği ikisini ayırıyor. Yalnız ı -> i farkı (işık) kaynak listede
    büyük harf küçültme hatasından (IŞIK -> işık) çok sık görünür, onun için eşik %40."""
    if not kismi_katlama(w, hedef):
        return GERCEK_ORAN
    farklar = [(a, b) for a, b in zip(w, hedef) if a != b]
    if farklar and all(a == "i" and b == "ı" for a, b in farklar):
        return 0.4
    return GERCEK_ORAN


def zemberek_kokleri(satirlar):
    kok = set()
    for s in satirlar:
        s = s.strip()
        if not s or s.startswith("#"):
            continue
        w = tr_kucuk(s.split(" [")[0].split()[0])
        if KELIME.match(w):
            kok.add(w)
    return kok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", help="kaynak dosyaların indirildiği dizin")
    ap.add_argument("--cikti", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "tr-sozluk.txt.gz"),
                    help="çıktı yolu; dosya tr-sozluk-1.txt.gz, tr-sozluk-2.txt.gz diye bölünür")
    a = ap.parse_args()

    sayi = collections.Counter()
    for s in oku(a.yerel, "tr_full.txt"):
        p = s.split()
        if len(p) != 2:
            continue
        w = tr_kucuk(p[0])
        if KELIME.match(w):
            sayi[w] += int(p[1])

    ingilizce = set()
    for i, s in enumerate(oku(a.yerel, "en_50k.txt")):
        if i >= EN_YAYGIN_INGILIZCE:
            break
        ingilizce.add(s.split()[0].lower())

    kok = zemberek_kokleri(oku(a.yerel, "master-dictionary.dict")) | zemberek_kokleri(oku(a.yerel, "non-tdk.dict"))
    # Zemberek şapkalı yazar (kısmî, hâl); derlemde ve günlük yazımda şapkasızı yaygın
    kok |= {k.translate(SAPKASIZ) for k in kok}

    ozel, ozel_ana = set(), set()
    for ad in ("proper.dict", "locations-tr.dict", "person-names.dict"):
        for satir_ in oku(a.yerel, ad):
            satir_ = satir_.strip()
            if satir_ and not satir_.startswith("#"):
                w = tr_kucuk(satir_.split(" [")[0].split()[0])
                if KELIME.match(w):
                    ozel.add(w)
                    if ad == "proper.dict":
                        ozel_ana.add(w)

    def ozel_mi(w):
        """Hedef özel ad mı? Tam eşleşme bütün listelerde; ekli biçim (türkiyede) yalnız proper.dict ile."""
        if w in ozel:
            return True
        for n in range(len(w) - 1, 4, -1):
            if w[:n] in ozel_ana and len(w) - n <= 5:
                return True
        return False

    elle_yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "elle-kokler.txt")
    with io.open(elle_yol, encoding="utf-8") as f:
        elle = {x.strip() for x in f if x.strip() and not x.startswith("#")}

    gruplar = collections.defaultdict(list)
    for w, c in sayi.items():
        if c >= EN_AZ_SAYI or w in kok:
            gruplar[katla(w)].append((c, w))

    satirlar = []
    k_say = b_say = a_say = 0
    for anahtar, liste in gruplar.items():
        liste.sort(reverse=True)
        harfliler = [(c, w) for c, w in liste if w != anahtar]
        if not harfliler:
            continue
        en_c, hedef = harfliler[0]
        if en_c < EN_AZ_SAYI and hedef not in kok:
            continue
        en_buyuk = liste[0][0]
        gercek = []
        for c, w in liste:
            if w == hedef:
                continue
            if w == anahtar:
                # ASCII biçim gerçek kelime mi: sözlük kökü, kök + yaygın ek, yaygın İngilizce kelime
                # ya da derlemde harfli biçimin en az %25'i kadar sık
                # Zemberek'te 'sekil' gibi seyrek kökler de var: kök ancak derlemde de iz bırakıyorsa
                # (harfli biçimin %2'si) ya da çok kısaysa (is, on, us) gerçek sayılır
                kok_gibi = w in kok or kok_ek(w, kok)
                if (w in ingilizce or c >= ASCII_GERCEK_ORAN * en_c or kok_ek_gercek(w, elle, 2)
                        or (kok_gibi and (c >= KOK_ASCII_ORAN * en_c or len(w) <= 3))):
                    gercek.append(w)
            elif (w in kok and c >= KOK_ORAN * en_buyuk) or c >= alternatif_esigi(w, hedef) * en_buyuk:
                gercek.append(w)
        if anahtar in sayi and sayi[anahtar] > en_c and anahtar not in gercek:
            gercek.append(anahtar)  # ASCII biçim harfli biçimden sık: kesin sayma
        bayrak = "\tP" if ozel_mi(hedef) else ""
        ascii_c = sayi.get(anahtar, 0)
        if anahtar in gercek and en_c < BASKIN_ORAN * ascii_c:
            # ASCII biçim çok daha yaygın (bu/bü, gibi/gıbı): ASCII yazım neredeyse her zaman doğrudur
            satirlar.append("A\t%s\t%s%s" % (hedef, "|".join(gercek), bayrak))
            a_say += 1
        elif gercek:
            satirlar.append("B\t%s\t%s%s" % (hedef, "|".join(gercek), bayrak))
            b_say += 1
        else:
            satirlar.append("K\t%s%s" % (hedef, "\t" + bayrak if bayrak else ""))
            k_say += 1

    # dil kapısı için yaygın ASCII Türkçe kelimeler
    t = []
    for w, c in sayi.most_common(20000):
        if len(t) >= T_SAYISI:
            break
        if katla(w) == w and len(w) >= 2 and w in kok and w not in ingilizce:
            t.append("T\t" + w)

    # 'i' ile başlayan gerçek ASCII kelimeler: metinde 'Ilk', 'Iptal' görülürse baştaki I aslında İ'dir
    kok_ascii = {k for k in kok if all(ord(c) < 128 for c in k)}
    i_bas = 0
    for w, c in sayi.items():
        if (w.startswith("i") and c >= EN_AZ_SAYI and katla(w) == w and len(w) >= 2 and w not in ingilizce
                and (w in kok or kok_ek_gercek(w, kok_ascii, 3) or c >= 500)
                and sayi.get("ı" + w[1:], 0) < GERCEK_ORAN * c):
            satirlar.append("I\t" + w + ("\tP" if ozel_mi(w) else ""))
            i_bas += 1

    # ASCII yazılışı da gerçek olan özel adlar (yalnız bir grupla çakışanlar)
    for w in sorted(ozel):
        if katla(w) == w and w in gruplar:
            satirlar.append("O\t" + w)

    satirlar.sort()
    os.makedirs(os.path.dirname(a.cikti), exist_ok=True)
    tum = satirlar + t
    # Parçalara böl: her parça 256 KB altında kalsın (skill tarayıcılarının tek dosya sınırı)
    parca = 2
    hedef_dizin = os.path.dirname(a.cikti)
    for eski in os.listdir(hedef_dizin):
        if eski.startswith("tr-sozluk") and eski.endswith(".txt.gz"):
            os.remove(os.path.join(hedef_dizin, eski))
    boy = (len(tum) + parca - 1) // parca
    for i in range(parca):
        veri = ("\n".join(tum[i * boy:(i + 1) * boy]) + "\n").encode("utf-8")
        yol = os.path.join(hedef_dizin, "tr-sozluk-%d.txt.gz" % (i + 1))
        with open(yol, "wb") as ham:
            # mtime=0: aynı kaynaktan aynı dosya, bayt bayt
            with gzip.GzipFile(filename="", mode="wb", fileobj=ham, compresslevel=9, mtime=0) as f:
                f.write(veri)
    print("kesin %d, belirsiz %d, ascii baskın %d, i-baş %d, dil kelimesi %d -> %s" % (k_say, b_say, a_say, i_bas, len(t), hedef_dizin), file=sys.stderr)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Ölçüm: doğru Türkçe derlemi programla bozar, tr_harf ile tespit ve onarımı ölçer.

    python3 evals/olc.py            # tabloyu yazar, evals/sonuclar/son.json ve son.md üretir

Tekrar üretilebilir: rastgelelik sabit tohumla (dosya adı + bozma türü).
"""
import json
import os
import random
import re
import sys
import tempfile
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "scripts"))
import tr_harf  # noqa: E402

DERLEM = os.path.join(KOK, "evals", "derlem")
VIKI = os.path.join(KOK, "evals", "derlem-viki")
YP = os.path.join(KOK, "evals", "yanlis-pozitif")
GERCEK = os.path.join(KOK, "evals", "gercek", "ornekler.json")
SONUC = os.path.join(KOK, "evals", "sonuclar")

TAM_KATLA = str.maketrans("çÇğĞıİöÖşŞüÜ", "cCgGiIoOsSuU")
KELIME = re.compile(r"[^\W\d_]+")


def tohum(*p):
    return random.Random("|".join(p))


def ascii_tam(m, ad):
    return m.translate(TAM_KATLA)


def ascii_kismi(m, ad):
    r = tohum(ad, "kismi")
    oran = r.uniform(0.2, 0.5)
    return KELIME.sub(lambda x: x.group(0).translate(TAM_KATLA)
                      if any(c in "çÇğĞıİöÖşŞüÜ" for c in x.group(0)) and r.random() < oran else x.group(0), m)


def _tek_bayt_coz(b, kod, yedek):
    out = []
    for x in b:
        try:
            out.append(bytes([x]).decode(kod))
        except UnicodeDecodeError:
            out.append(bytes([x]).decode(yedek))
    return "".join(out)


def moj_cp1252(m, ad):
    return _tek_bayt_coz(m.encode("utf-8"), "cp1252", "latin-1")


def moj_cp1254(m, ad):
    return _tek_bayt_coz(m.encode("utf-8"), "cp1254", "latin-1")


def moj_cp857(m, ad):
    return _tek_bayt_coz(m.encode("utf-8"), "cp857", "cp437")


def moj_cift(m, ad):
    return moj_cp1252(moj_cp1252(m, ad), ad)


def tek_bayt(m, ad):
    try:
        return _tek_bayt_coz(m.encode("cp1254"), "cp1252", "latin-1")
    except UnicodeEncodeError:
        return None


def karma(m, ad):
    """Paragrafların bir kısmı kısmi ASCII, biri cp1252 mojibake, kalanı sağlam."""
    r = tohum(ad, "karma")
    par = re.split(r"(\n\s*\n)", m)
    out = []
    moj_yapildi = False
    for p in par:
        if not p.strip() or re.match(r"\n\s*\n", p):
            out.append(p)
            continue
        z = r.random()
        if z < 0.4:
            out.append(ascii_kismi(p, ad + str(len(out))))
        elif z < 0.6 and not moj_yapildi:
            out.append(moj_cp1252(p, ad))
            moj_yapildi = True
        else:
            out.append(p)
    return "".join(out)


BOZMALAR = [("tam ASCII", ascii_tam), ("kısmi ASCII (%20-50)", ascii_kismi), ("UTF-8 -> cp1252", moj_cp1252),
            ("UTF-8 -> cp1254", moj_cp1254), ("UTF-8 -> cp857 (konsol)", moj_cp857),
            ("çift kodlama", moj_cift), ("cp1254 -> latin-1", tek_bayt), ("karma", karma)]

BOSLUK = re.compile(r"[ \t\n]+")


def jetonlar(m):
    out, pos = [], 0
    for x in BOSLUK.finditer(m):
        if x.start() > pos:
            out.append((pos, x.start(), m[pos:x.start()]))
        pos = x.end()
    if pos < len(m):
        out.append((pos, len(m), m[pos:]))
    return out


def gecici_dosya(ad, metin, dizin):
    yol = os.path.join(dizin, ad)
    with open(yol, "w", encoding="utf-8", newline="") as f:
        f.write(metin)
    return yol


def olc_bir(asil, bozuk, ad, dizin):
    yol = gecici_dosya(ad, bozuk, dizin)
    t0 = time.time()
    c = tr_harf.dosya_onar(yol)
    sure = time.time() - t0
    onarilmis = c["yeni"]
    O, C, R = jetonlar(asil), jetonlar(bozuk), jetonlar(onarilmis)
    s = dict(kelime=0, bozuk=0, tp_kesin=0, tp_herhangi=0, fp_kesin=0, onarildi=0, yanlis_duzeltme=0,
             dogruyu_bozma=0, belirsiz_isaret=0)
    if not (len(O) == len(C) == len(R)):
        s["hizalanamadi"] = 1
        return s, sure, c, onarilmis == asil
    kesin = [(b["bas"], b["son"]) for b in c["bulgular"] if b["kesin"]]
    herhangi = [(b["bas"], b["son"]) for b in c["bulgular"]]
    belirsiz = [(b["bas"], b["son"]) for b in c["bulgular"] if b["tur"] == "belirsiz"]

    def ortusur(ar, b, e):
        return any(x < e and b < y for x, y in ar)

    for (ob, oe, o), (cb, ce, cc), (rb, re_, rr) in zip(O, C, R):
        s["kelime"] += 1
        boz = o != cc
        k = ortusur(kesin, cb, ce)
        h = ortusur(herhangi, cb, ce)
        if boz:
            s["bozuk"] += 1
            s["tp_kesin"] += k
            s["tp_herhangi"] += h
            s["belirsiz_isaret"] += ortusur(belirsiz, cb, ce)
            if rr == o:
                s["onarildi"] += 1
        else:
            s["fp_kesin"] += k
        if rr != cc and rr != o:
            s["yanlis_duzeltme"] += 1
            if not boz:
                s["dogruyu_bozma"] += 1
    return s, sure, c, onarilmis == asil


def oran(a, b):
    return round(100.0 * a / b, 1) if b else None


def derlem_oku(dizin):
    dosyalar = sorted(f for f in os.listdir(dizin) if not f.startswith(".") and f != "KAYNAK.md")
    return {f: open(os.path.join(dizin, f), encoding="utf-8").read() for f in dosyalar}


def bozma_olc(asillar, tmp, ornek_hatalar, etiket):
    satirlar = []
    for ad, fn in BOZMALAR:
        top = dict(kelime=0, bozuk=0, tp_kesin=0, tp_herhangi=0, fp_kesin=0, onarildi=0, yanlis_duzeltme=0,
                   dogruyu_bozma=0, belirsiz_isaret=0, hizalanamadi=0)
        dosya_n = tespit_dosya = birebir = 0
        sure = 0.0
        for f in sorted(asillar):
            bozuk = fn(asillar[f], f)
            if bozuk is None or bozuk == asillar[f]:
                continue
            s, sn, c, esit = olc_bir(asillar[f], bozuk, f, tmp)
            sure += sn
            dosya_n += 1
            tespit_dosya += bool(tr_harf.sorunlu(c["bulgular"]))
            birebir += esit
            for k, v in s.items():
                top[k] = top.get(k, 0) + v
            if s.get("dogruyu_bozma") or s.get("yanlis_duzeltme"):
                ornek_hatalar.append((etiket, ad, f))
        kesin_isaret = top["tp_kesin"] + top["fp_kesin"]
        satirlar.append({
            "derlem": etiket, "bozma": ad, "dosya": dosya_n, "bozuk_kelime": top["bozuk"],
            "dosya_tespit_%": oran(tespit_dosya, dosya_n),
            "kelime_duyarlilik_kesin_%": oran(top["tp_kesin"], top["bozuk"]),
            "kelime_duyarlilik_herhangi_%": oran(top["tp_herhangi"], top["bozuk"]),
            "kelime_kesinlik_%": oran(top["tp_kesin"], kesin_isaret),
            "onarim_kelime_%": oran(top["onarildi"], top["bozuk"]),
            "birebir_dosya_%": oran(birebir, dosya_n),
            "yanlis_duzeltme": top["yanlis_duzeltme"], "dogruyu_bozma": top["dogruyu_bozma"],
            "hizalanamadi": top["hizalanamadi"], "sure_ms_dosya": round(1000 * sure / max(1, dosya_n), 1)})
    return satirlar


def main():
    derlemler = [("kendi derlem", derlem_oku(DERLEM)), ("Vikipedi", derlem_oku(VIKI))]
    sonuc = {"surum": tr_harf.SURUM,
             "derlemler": {e: {"dosya": len(a), "kelime": sum(len(jetonlar(m)) for m in a.values())}
                           for e, a in derlemler},
             "bozmalar": [], "yanlis_pozitif": {}, "gercek": []}
    t_bas = time.time()
    tr_harf.sozluk()
    sonuc["sozluk_yukleme_sn"] = round(time.time() - t_bas, 3)
    ornek_hatalar = []
    with tempfile.TemporaryDirectory() as tmp:
        for etiket, asillar in derlemler:
            sonuc["bozmalar"] += bozma_olc(asillar, tmp, ornek_hatalar, etiket)

        # yanlış pozitif: sağlam derlem + İngilizce/Almanca/İspanyolca/kod/URL
        for etiket, dizin in (("sağlam Türkçe: kendi derlem", DERLEM), ("sağlam Türkçe: Vikipedi", VIKI),
                              ("İngilizce, Almanca, İspanyolca, kod, URL", YP)):
            n = isaretli = kesin_bulgu = tum_bulgu = degisen = 0
            for f in sorted(os.listdir(dizin)):
                if f == "KAYNAK.md":
                    continue
                yol = os.path.join(dizin, f)
                c = tr_harf.dosya_onar(yol)
                n += 1
                isaretli += bool(tr_harf.sorunlu(c["bulgular"]))
                kesin_bulgu += sum(1 for b in c["bulgular"] if b["kesin"])
                tum_bulgu += len(c["bulgular"])
                degisen += c["yeni"] != c["metin"]
            sonuc["yanlis_pozitif"][etiket] = {"dosya": n, "isaretlenen_dosya": isaretli, "kesin_bulgu": kesin_bulgu,
                                              "tum_bulgu": tum_bulgu, "onarimda_degisen_dosya": degisen}

        # gerçek örnekler
        for o in json.load(open(GERCEK, encoding="utf-8")):
            yol = gecici_dosya(o["dosya"], o["bozuk"], tmp)
            c = tr_harf.dosya_onar(yol)
            sonuc["gercek"].append({
                "kaynak": o["kaynak"], "dosya": o["dosya"], "bozuk": o["bozuk"].strip(),
                "onarilmis": c["yeni"].strip(), "beklenen": (o["dogru"] or "").strip() or None,
                "tespit": bool(tr_harf.sorunlu(c["bulgular"])),
                "birebir": (c["yeni"] == o["dogru"]) if o["dogru"] else None,
                "elle_bakilacak": [tr_harf._json_bulgu(b) for b in c["bulgular"]
                                   if b not in c["uygulanan"]]})
    sonuc["toplam_sure_sn"] = round(time.time() - t_bas, 2)
    sonuc["yanlis_duzeltme_ornekleri"] = ornek_hatalar[:20]

    os.makedirs(SONUC, exist_ok=True)
    with open(os.path.join(SONUC, "son.json"), "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=1)
    md = tablo(sonuc)
    with open(os.path.join(SONUC, "son.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print(md)


def tablo(s):
    sat = ["Derlemler: " + "; ".join("%s %d dosya, %d kelime" % (k, v["dosya"], v["kelime"])
                                      for k, v in s["derlemler"].items())
           + ". Sözlük yükleme %.2f sn, toplam %.1f sn." % (s["sozluk_yukleme_sn"], s["toplam_sure_sn"]), "",
           "| Derlem | Bozma | Dosya | Bozuk kelime | Dosya tespiti | Duyarlılık (kesin) | Duyarlılık (işaretli) "
           "| Kesinlik | Onarım | Birebir dosya | Yanlış düzeltme | Doğruyu bozma | ms/dosya |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for b in s["bozmalar"]:
        sat.append("| %s | %s | %d | %d | %s%% | %s%% | %s%% | %s%% | %s%% | %s%% | %d | %d | %s |" % (
            b["derlem"], b["bozma"], b["dosya"], b["bozuk_kelime"], b["dosya_tespit_%"],
            b["kelime_duyarlilik_kesin_%"], b["kelime_duyarlilik_herhangi_%"], b["kelime_kesinlik_%"],
            b["onarim_kelime_%"], b["birebir_dosya_%"], b["yanlis_duzeltme"], b["dogruyu_bozma"], b["sure_ms_dosya"]))
    sat += ["", "| Yanlış pozitif kümesi | Dosya | İşaretlenen dosya | Kesin bulgu | Tüm bulgu | Onarımda değişen dosya |",
            "|---|---|---|---|---|---|"]
    for k, v in s["yanlis_pozitif"].items():
        sat.append("| %s | %d | %d | %d | %d | %d |" % (k, v["dosya"], v["isaretlenen_dosya"], v["kesin_bulgu"],
                                                     v["tum_bulgu"], v["onarimda_degisen_dosya"]))
    sat += ["", "| Gerçek örnek | Tespit | Onarım sonucu | Birebir |", "|---|---|---|---|"]
    for g in s["gercek"]:
        sat.append("| [%s](%s) `%s` | %s | `%s` | %s |" % (
            g["kaynak"].split("github.com/")[1].replace("/issues/", "#"), g["kaynak"], g["bozuk"].replace("|", "\\|")[:60],
            "evet" if g["tespit"] else "hayır", g["onarilmis"].replace("|", "\\|")[:70],
            {True: "evet", False: "hayır", None: "-"}[g["birebir"]]))
    return "\n".join(sat) + "\n"


if __name__ == "__main__":
    main()

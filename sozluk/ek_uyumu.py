"""Ek uyumu: ASCII bir kelime 'gerçek kök + ASCII yazılabilen ek zinciri' mi?

Türkçede ünlü uyumu yüzünden bir ekin ASCII biçimi yalnız bazı köklerden sonra geçerlidir:
'don' + 'uyor' = donuyor (gerçek), 'kal' + 'di' = kaldi (gerçek değil, doğrusu kaldı).
Bu modül sözlük üretiminde 'ASCII biçimi de gerçek kelime olabilir mi' sorusuna temkinli yanıt verir.
"""

# Büyük harfler uyuma göre değişir: A = a/e, I = ı/i/u/ü, D = d/t, C = c/ç
SABLONLAR = """
lAr lArI lArIn lArA lArDA lArDAn lArlA lArIm lArIn lArImIz lArInIz lArI lArInI lArInA lArIndA lArIndAn
DA DAn DAki I In nIn yI yA A lA ylA lI lIk lIğ sIz sI sInI sInA sIndA sIndAn sIylA Im ImIz InIz
DI DIm DIn DIk DInIz DIlAr DIr DIrlAr Iyor Iyorum Iyorsun Iyoruz Iyorlar Iyordu Iyordum Iyorsa
mAk mAktA mAktAn mA mAz mAzsA mAdI mAdAn mAyA mAyI mAlI Ar Ir Ur AcAk AcAktI Ip ArAk yAn An AnlAr
sA sAm sAn sAk ken AbIlIr AbIlIrIm AbIlIrsIn AbIlIriz
"""

UNLU = set("aeıioöuü")
KALIN = set("aıou")
YUVARLAK = set("oöuü")
SERT = set("fstkçşhp")


def _son_unlu(s):
    for c in reversed(s):
        if c in UNLU:
            return c
    return None


def _uret(sablon, kok):
    """Kökün son ünlüsüne göre şablonu somut eke çevirir."""
    v = _son_unlu(kok) or "e"
    out = []
    son_harf = kok[-1]
    onceki = v
    for i, ch in enumerate(sablon):
        if ch == "A":
            onceki = "a" if onceki in KALIN else "e"
            out.append(onceki)
        elif ch == "I":
            if onceki in KALIN:
                onceki = "u" if onceki in YUVARLAK else "ı"
            else:
                onceki = "ü" if onceki in YUVARLAK else "i"
            out.append(onceki)
        elif ch == "D":
            onceki_harf = out[-1] if out else son_harf
            out.append("t" if onceki_harf in SERT else "d")
        elif ch == "C":
            onceki_harf = out[-1] if out else son_harf
            out.append("ç" if onceki_harf in SERT else "c")
        else:
            out.append(ch)
            if ch in UNLU:
                onceki = ch
    return "".join(out)


_SAB = sorted(set(SABLONLAR.split()), key=len, reverse=True)


def kok_ek_gercek(w, kokler, en_kisa=3):
    """w (ASCII) = kök + uyumlu ve ASCII yazılabilen ek mi? Kök 'kokler' kümesinden (fiil kökleri dahil)."""
    for n in range(len(w), en_kisa - 1, -1):
        kok = w[:n]
        if kok not in kokler:
            continue
        kalan = w[n:]
        if not kalan:
            return kok
        for sab in _SAB:
            ek = _uret(sab, kok)
            if ek == kalan and all(ord(c) < 128 for c in ek):
                return kok + "+" + ek
    return None

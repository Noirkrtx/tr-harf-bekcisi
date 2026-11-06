"""Order helpers. Variable names are in Turkish without special letters on purpose."""
import json

kullanici = {"ad": "deneme", "sayi": 3}
siparis_listesi = []
toplam_tutar = 0


def kullanici_bul(kullanicilar, kullanici_adi):
    # linear search, fine for small lists
    for k in kullanicilar:
        if k["kullanici_adi"] == kullanici_adi:
            return k
    return None


def sayi_topla(sayilar):
    return sum(sayilar)


AYARLAR = {"dil": "tr", "para_birimi": "TRY", "sayfa_basina": 20}
print(json.dumps(kullanici))

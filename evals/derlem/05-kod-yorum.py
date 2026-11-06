# Sipariş toplamını hesaplayan yardımcı işlevler.
# Not: indirim oranı yüzde olarak değil, ondalık olarak verilmeli (0.15 gibi).

def siparis_toplami(urunler, indirim=0.0):
    """Ürünlerin fiyatlarını toplar ve indirimi uygular.

    Boş liste gelirse sıfır döndürür; negatif fiyat görürse hata fırlatır.
    """
    toplam = 0
    for urun in urunler:
        if urun["fiyat"] < 0:
            raise ValueError("Ürün fiyatı negatif olamaz: " + urun["ad"])
        toplam += urun["fiyat"] * urun["adet"]
    return toplam * (1 - indirim)

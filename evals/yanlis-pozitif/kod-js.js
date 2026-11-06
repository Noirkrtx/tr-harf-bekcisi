// Utility functions for the cart page.
const sepet = { urunler: [], toplam: 0 };
const kullaniciAdi = "misafir";

function urunEkle(urun) {
  sepet.urunler.push(urun);
  sepet.toplam += urun.fiyat;
  return sepet;
}

const ayarlar = { dil: "tr", gosterim: "liste", sayfaBoyutu: 25 };
fetch("https://api.example.com/v1/sepet?kullanici=misafir&dil=tr");
module.exports = { urunEkle, sepet, kullaniciAdi, ayarlar };

// Form gönderilmeden önce alanları denetler.
function formuDenetle(form) {
  const hatalar = [];
  if (!form.eposta.includes("@")) {
    hatalar.push("Geçerli bir e-posta adresi girin.");
  }
  if (form.sifre.length < 8) {
    hatalar.push("Şifre en az sekiz karakter olmalı.");
  }
  return hatalar; // boş dizi: her şey yolunda
}

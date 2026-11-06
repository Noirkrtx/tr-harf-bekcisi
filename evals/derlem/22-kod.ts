// Sepetteki ürün sayısını gösteren küçük bileşen.
// Sayı sıfırsa rozet hiç görünmez.
export function SepetRozeti({ adet }: { adet: number }) {
  if (adet === 0) return null;
  const etiket = adet > 99 ? "99+" : String(adet);
  return <span title="Sepetinizdeki ürün sayısı">{etiket}</span>;
}

// Kullanıcı listesini sayfalara böler.
// Not: sayfa numarası birden başlar.
export function sayfala<T>(liste: T[], sayfa: number, boyut = 20): T[] {
  const bas = (sayfa - 1) * boyut;
  return liste.slice(bas, bas + boyut);
}

export const hataMesaji = "Bu sayfada gösterilecek kayıt yok.";

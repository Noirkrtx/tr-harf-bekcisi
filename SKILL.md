---
name: tr-harf-bekcisi
description: "Türkçe metin içeren bir dosyayı yazdıktan ya da düzenledikten sonra kullan. Bozulmuş Türkçe harfleri bulur: ASCII'leşme (cok, icin, gelistirildi) ve mojibake (TÃ¼rkÃ§e, T├╝rk├ğe, Arkadaþ). Güvenli olanları onarır, belirsizleri işaretler. Use after writing or editing any file with Turkish text, to catch lost diacritics and encoding garbage."
license: MIT
metadata:
  version: 0.1.0
  author: NOIR (@noirkrtx)
---

# Türkçe harf bekçisi

Ajanlar dosyaya Türkçe yazarken harfleri iki şekilde bozabiliyor: ç, ğ, ı, ö, ş, ü düşüyor ("kullanici girisi") ya da UTF-8 metin yanlış kod sayfasıyla okunup yazılıyor ("TÃ¼rkÃ§e", "T├╝rk├ğe"). Bu skill, yazdığın dosyayı `scripts/tr_harf.py` ile denetletir.

## Ne zaman

- Türkçe metin içeren bir dosyayı (md, txt, json/yaml çeviri dosyası, srt, csv, kod içindeki yorum ve dizeler) yazdıktan ya da düzenledikten hemen sonra.
- Kullanıcı "Türkçe karakterler bozuk", "harfler gitmiş", "Ã§ çıkıyor" dediğinde.
- Windows PowerShell çıktısında `Ã§`, `Ä±`, `ÅŸ` gördüğünde: dosyanın kendisi bozuk olmayabilir, önce bu araçla dosyayı denetle (konsol görüntüsü ile dosya baytları farklı olabilir).

## Nasıl

Komutlar bu skill klasörüne göre yazıldı (`<skill>` = bu SKILL.md'nin bulunduğu klasör):

```bash
python3 <skill>/scripts/tr_harf.py kontrol <dosya-veya-dizin>     # sorun varsa çıkış kodu 1
python3 <skill>/scripts/tr_harf.py onar <dosya>                   # önce farkı göster (yazmaz)
python3 <skill>/scripts/tr_harf.py onar <dosya> --yaz             # kesin onarımları yaz
python3 <skill>/scripts/tr_harf.py kontrol <dosya> --json         # makine için çıktı
```

## Adımlar

1. Türkçe içerikli dosyayı yazdıktan sonra `kontrol` çalıştır.
2. Çıkış 0 ise bitti.
3. Çıkış 1 ise satırları oku:
   - `HARFSIZ eski -> yeni` ve `MOJIBAKE eski -> yeni`: kesin. `onar <dosya> --yaz` ile ya da kendi düzenleme aracınla uygula.
   - `BELIRSIZ`: kelimenin ASCII biçimi de gerçek bir kelime (sinir/sınır, is/iş, oldu/öldü) ya da büyük harfli bir özel ad olabilir. Cümleye bakıp karar ver; emin değilsen dokunma.
   - `KALINTI`, `KAYIP` (harf yerine `?` ya da `�`): otomatik onarılamaz. Bağlamdan doğru kelime belliyse elle düzelt, değilse kullanıcıya söyle.
   - `KODLAMA cp1254 -> utf-8`: dosya UTF-8 değil. `onar --yaz` dosyayı UTF-8'e çevirir.
4. Onardıktan sonra `kontrol`u bir kez daha çalıştır; HARFSIZ ve MOJIBAKE kalmamalı.

## Dokunmadıkları

Markdown kod blokları ve satır içi kod, URL, e-posta, dosya yolu, `snake_case` / `camelCase` / `kebab-case` tanımlayıcılar, kısaltmalar; kod dosyalarında yorum ve dize dışındaki her şey; tek kelimelik kod dizeleri (`"kullanici"` gibi anahtarlar). Türkçe olmayan paragraflar (İngilizce, Almanca) dil kapısından geçmez.

Bir kelimeyi hiç işaretletmemek için proje köküne `.tr-harf-yoksay` dosyası koy (satır başına bir kelime; `yol: klasor/*` satırları dosya yolu kalıbıdır). Tek satırı atlatmak için o satıra `tr-harf: yoksay` yaz.

## Kurallar

- Bilmediğini tahminle doldurma: araç "elle bakın" diyorsa bağlamdan emin olmadan değiştirme.
- Türkçe harfi olan doğru bir kelimeyi asla harfsiz biçime çevirme.
- Hook kuruluysa (Claude Code, Codex, Hermes) bu denetim her yazmadan sonra kendiliğinden çalışır; çıktısını gördüğünde aynı turda düzelt.

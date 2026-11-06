## Türkçe harfler

Türkçe metin içeren bir dosyayı yazdıktan ya da düzenledikten sonra şunu çalıştır:

    python3 ~/.agents/skills/tr-harf-bekcisi/scripts/tr_harf.py kontrol <dosya>

Çıkış kodu 1 ise listedeki `->` önerilerini uygula ya da `onar <dosya> --yaz` çalıştır. "elle bakın" yazan satırlarda bağlama göre karar ver. Türkçe harfleri (ç, ğ, ı, İ, ö, ş, ü) ASCII'ye çevirme. Windows PowerShell 5.1'de dosya okurken `Get-Content -Encoding UTF8` kullan; konsolda gördüğün `Ã§`, `Ä±` gibi diziler dosyada olmayabilir, önce bu araçla dosyanın kendisini denetle.

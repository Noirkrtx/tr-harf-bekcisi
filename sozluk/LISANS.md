# Sözlük lisansı ve atıf

`tr-sozluk-1.txt.gz` ve `tr-sozluk-2.txt.gz` dosyaları aşağıdaki kaynaklardan `uret.py` ile üretildi. Bu iki dosya **CC BY-SA 4.0** lisanslıdır (kaynak 1'in lisansı gereği). Reponun kodu ayrı olarak MIT lisanslıdır; bkz. kökteki `LICENSE`.

## Kaynaklar

1. **hermitdave/FrequencyWords**, `content/2018/tr/tr_full.txt` ve `content/2018/en/en_50k.txt`
   https://github.com/hermitdave/FrequencyWords
   Lisans: içerik CC BY-SA 4.0, kod MIT (repo README'sindeki "License" bölümü).
   Liste, OPUS OpenSubtitles2018 derleminden üretilmiştir: http://opus.nlpl.eu/OpenSubtitles2018.php
   Kullanım: Türkçe kelimelerin sıklığı; ASCII biçimin gerçek kelime mi yazım hatası mı olduğuna karar vermek; en sık 5.000 İngilizce kelime (bunlar hiçbir zaman otomatik düzeltilmez).

2. **ahmetaa/zemberek-nlp**, `morphology/src/main/resources/tr/` altındaki `master-dictionary.dict`, `non-tdk.dict`, `proper.dict`, `locations-tr.dict`, `person-names.dict`
   https://github.com/ahmetaa/zemberek-nlp
   Lisans: Apache License 2.0, Copyright 2018 Ahmet A. Akın, Mehmet D. Akın.
   Kullanım: kök sözlüğü (ASCII biçimi de gerçek olan kelimeleri belirsiz saymak için) ve özel adlar.

3. `elle-kokler.txt`: bu reponun elle seçtiği kısa kök listesi (MIT).

## Yapılan değişiklikler

Kaynak listeler küçük harfe çevrildi (Türkçe kuralıyla), birleştirildi, ASCII biçimlerine göre gruplandı ve her grup için "kesin / belirsiz / ASCII baskın" kararı verildi. Ayrıntılar `uret.py` içinde. Kelime içeriği değiştirilmedi.

## Yeniden üretmek

```bash
python3 sozluk/uret.py                 # kaynakları indirir (yaklaşık 31 MB)
python3 sozluk/uret.py --yerel DIZIN   # önceden indirilmiş dosyalarla
```

Aynı kaynaklardan aynı dosyalar bayt bayt çıkar (gzip zaman damgası sıfırlanır).

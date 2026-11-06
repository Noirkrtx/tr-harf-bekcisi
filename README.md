# Türkçe harf bekçisi

Yapay zeka ajanları dosyaya Türkçe yazarken harfleri sessizce bozabiliyor. Ya ç, ğ, ı, ö, ş, ü düşüyor ve metin "kullanici girisi dogrulandi" diye kalıyor, ya da metin Windows'ta yanlış kod sayfasıyla okunup geri yazılıyor ve "TÃ¼rkÃ§e", "T├╝rk├ğe" gibi diziler çıkıyor. Çoğu zaman bunu yayından sonra fark ediyorsunuz.

Bu araç ajan bir dosyayı yazdığı anda o dosyaya bakıyor, bozuk harfleri buluyor ve emin olduğu yerleri onarıyor. Emin olmadığı yerde dokunmuyor, yalnız gösteriyor.

```text
Önce:  Bu arac, kullanici girisini dogrular ve hata mesajini gosterir.
       TÃ¼rkÃ§e karakterler de bozulmus.

Sonra: Bu araç, kullanıcı girişini doğrular ve hata mesajını gösterir.
       Türkçe karakterler de bozulmuş.
```

Claude Code'da hook olarak kurulduğunda ajan dosyayı yazar yazmaz şu geri bildirimi alıyor ve aynı turda düzeltiyor:

```text
tr-harf-bekcisi: yazdığın dosyada bozuk Türkçe harf var.
NOTLAR.md:3:4: HARFSIZ arac -> araç  [Türkçe harfleri düşmüş]
NOTLAR.md:3:10: HARFSIZ kullanici -> kullanıcı  [Türkçe harfleri düşmüş]
NOTLAR.md:4:2: MOJIBAKE Ã¼ -> ü  [UTF-8 metin cp1252/cp1254/latin-1 olarak okunmuş]
...
```

Araç tek bir Python dosyası, bağımlılığı yok (Python 3.8 ve üstü). Claude Code, Codex ve Hermes için hazır hook ayarları, git pre-commit ve GitHub Actions örneği repoda duruyor. [Agent Skills](https://agentskills.io) biçiminde bir skill olarak da kullanılabiliyor.

## Ne buluyor

| Bozulma | Örnek | Ne yapıyor |
|---|---|---|
| Harfleri düşmüş kelime | `cok`, `icin`, `gelistirildi`, `Ilk` | Sözlükte tek karşılığı varsa onarır |
| Yarısı düşmüş kelime | `gelişmis`, `açik` | Onarır |
| UTF-8 metin Windows kod sayfasıyla okunmuş | `TÃ¼rkÃ§e`, `ArkadaÅŸ`, `Ä°` | Onarır, sonucu doğrular |
| UTF-8 metin DOS konsol kod sayfasıyla okunmuş | `T├╝rk├ğe` (cp857, cp850, cp437) | Onarır |
| İki kez bozulmuş | `Ã„Â±` | Onarır |
| JSON içinde kaçışlı biçim | `"T\u00c3\u00bcrk\u00c3\u00a7e"` | Onarır |
| Windows Türkçe dosya latin-1 diye okunmuş | `Arkadaþ`, `ýþýk`, `Aðustos` | Onarır |
| Dosya UTF-8 değil, cp1254 | | UTF-8'e çevirir |
| Harf yerine soru işareti | `T?rk?e` | Yalnız gösterir, sözlükte aday varsa söyler |
| ASCII biçimi de gerçek kelime | `sinir` / `sınır`, `oldu` / `öldü` | Yalnız gösterir |

Bir dosyada hem doğru yazılmış hem harfleri düşmüş kelimeler varsa ayrıca "metin sonradan bozulmuş olabilir" uyarısı veriyor. Böyle bir karışım çoğu zaman ajanın var olan Türkçe bir dosyayı düzenlerken harfleri bozduğunu gösteriyor.

## Neden emin olmadığı yere dokunmuyor

Harfleri geri koymanın zor yanı, bazı kelimelerin ASCII biçiminin de gerçek bir kelime olması. "sinir" de "sınır" da Türkçe. Bunları cümleye bakmadan değiştirmek, doğru metni bozmak demek. Araç bu yüzden kelimeleri üç gruba ayırıyor:

- **Kesin:** ASCII biçimi gerçek bir kelime değil (`cok`, `kullanici`, `gelistirildi`). Onarılır.
- **Belirsiz:** ASCII biçimi de gerçek bir kelime (`sinir`, `is`, `oldu`, `donuyor`). Yalnız dosyada başka bozulma da varsa "elle bakın" diye gösterilir.
- **ASCII baskın:** harfli biçim çok seyrek (`bu` / `bü`, `gibi` / `gıbı`). Hiç gösterilmez.

Bunun dışında birkaç kuralı daha var:

- Türkçe harfi olan bir kelimeyi asla harfsiz biçime çevirmez. Yalnız harf ekler.
- Cümle ortasında büyük harfle başlayan ve sözlükte özel ad olarak geçmeyen kelimeye (`Apis`, `Durusu`) dokunmaz, belirsiz sayar.
- Kesme işaretinden sonraki eki kökün ünlüsüne göre uyumlar: `Dunya'nin` -> `Dünya'nın`. `-ki` ekine dokunmaz (`Mars'taki`).
- Mojibake onarımını uyguladıktan sonra metni yeniden tarar. Onarılmış metinde yine bozuk kodlama izi kalıyorsa o onarımı uygulamaz.

## Neye dokunmuyor

- Markdown kod blokları ve satır içi kod.
- URL, e-posta, dosya yolu, `snake_case`, `camelCase`, `kebab-case` tanımlayıcılar, kısaltmalar.
- Kod dosyalarında yorum ve dize dışındaki her şey. Tek kelimelik dizeler de atlanır, çünkü kodda bunlar çoğunlukla anahtardır (`data["kullanici"]`).
- JSON ve YAML'da anahtarlar (yalnız değerlere bakar).
- Türkçe olmayan paragraflar. Her paragraf ayrı ayrı "bu Türkçe mi" denetiminden geçiyor; İngilizce, Almanca, İspanyolca metinde hiçbir şey işaretlenmiyor.

Bir kelimeyi ya da dosyayı hiç işaretletmemek için proje köküne `.tr-harf-yoksay` dosyası koyabilirsiniz. Her satıra bir kelime yazılır; `yol: belgeler/eski/*` biçimindeki satırlar dosya yolu kalıbıdır. Tek bir satırı atlatmak için o satıra `tr-harf: yoksay` yazmak yeterli.

## Adım adım kurulum

Her kurulum için önce repoyu indirin. Skill klasörü repo kökünün kendisidir; `scripts/` ve `sozluk/` klasörleri birlikte durmalı.

### (a) Claude Code

**Eklenti olarak (önerilen).** Eklenti hem hook'u hem skill'i kurar:

```text
/plugin marketplace add Noirkrtx/tr-harf-bekcisi
/plugin install tr-harf-bekcisi@noirkrtx
```

Kurulumdan sonra her `Write`, `Edit` ve `MultiEdit` çağrısından sonra hook çalışır. Sorun bulursa çıkış kodu 2 ile döner; Claude Code bu durumda hook'un stderr çıktısını Claude'a gösterir, böylece ajan aynı turda düzeltir.

**Elle kurulum.** Repoyu kişisel skill klasörüne kopyalayın, sonra hook'u ayarlara ekleyin:

```bash
git clone https://github.com/Noirkrtx/tr-harf-bekcisi.git ~/.claude/skills/tr-harf-bekcisi
```

`~/.claude/settings.json` dosyasına (ya da projedeki `.claude/settings.json`) şunu ekleyin. Hazır hali [`entegrasyon/claude-code/settings.json`](entegrasyon/claude-code/settings.json) dosyasında:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          { "type": "command", "command": "python3 ~/.claude/skills/tr-harf-bekcisi/scripts/tr_harf.py hook", "timeout": 30 }
        ]
      }
    ]
  }
}
```

Windows'ta `python3` komutu yoksa `py -3` ya da `python` yazın.

Kaynak: [Claude Code hooks belgesi](https://code.claude.com/docs/en/hooks) (PostToolUse girdisi, "Exit code 2 behavior per event" tablosu: PostToolUse'da stderr Claude'a gösterilir), [eklenti başvurusu](https://code.claude.com/docs/en/plugins-reference) (`hooks/hooks.json`, `${CLAUDE_PLUGIN_ROOT}`, `skills: "."`), [marketplace belgesi](https://code.claude.com/docs/en/plugin-marketplaces) (`"source": "./"` ile repo kökündeki eklenti).

### (b) OpenAI Codex

Codex de PostToolUse hook'larını destekliyor ve dosya düzenlemeleri `apply_patch` aracıyla geliyor. Hook, yamanın içindeki `*** Update File:` ve `*** Add File:` satırlarından değişen dosyaları buluyor.

1. Repoyu kullanıcı skill klasörüne indirin:
   ```bash
   git clone https://github.com/Noirkrtx/tr-harf-bekcisi.git ~/.agents/skills/tr-harf-bekcisi
   ```
2. [`entegrasyon/codex/hooks.json`](entegrasyon/codex/hooks.json) dosyasını `~/.codex/hooks.json` olarak kopyalayın (dosya zaten varsa `PostToolUse` girdisini o dosyaya ekleyin).
3. Codex'i açın ve `/hooks` komutuyla yeni hook'u inceleyip güvenilir olarak işaretleyin. Codex, güvenilmeyen hook'ları çalıştırmıyor.
4. İsterseniz [`entegrasyon/codex/AGENTS-eki.md`](entegrasyon/codex/AGENTS-eki.md) içindeki kısa talimatı projenin `AGENTS.md` dosyasına ekleyin. Hook kapalı olsa bile ajan yazdıktan sonra kontrolü kendisi çalıştırır.

Kaynak: [Codex hooks belgesi](https://developers.openai.com/codex/hooks) (`~/.codex/hooks.json`, `apply_patch` için `Edit`/`Write` eşleştiricisi, PostToolUse'da çıkış kodu 2 ve stderr, `/hooks` güven incelemesi), [Codex skills belgesi](https://developers.openai.com/codex/skills) (`~/.agents/skills`).

### (c) Hermes

1. Skill'i kurun (repo kökünde `SKILL.md` olduğu için tanımlayıcının sonunda eğik çizgi var):
   ```bash
   hermes skills inspect Noirkrtx/tr-harf-bekcisi/
   hermes skills install Noirkrtx/tr-harf-bekcisi/
   ```
2. Her yazmadan sonra otomatik denetim için küçük eklentiyi kurun:
   ```bash
   git clone https://github.com/Noirkrtx/tr-harf-bekcisi.git
   cp -r tr-harf-bekcisi/entegrasyon/hermes/tr-harf-bekcisi ~/.hermes/plugins/
   hermes plugins enable tr-harf-bekcisi
   ```
   Eklenti `write_file` ve `patch` araçlarının sonucuna, sorun varsa bir `tr_harf_bekcisi` notu ekliyor; ajan bunu araç çıktısında görüyor. `tr_harf.py` dosyasını birinci adımda kurulan skill klasöründen buluyor.

Neden kabuk hook'u değil de eklenti: Hermes'te `post_tool_call` bir gözlem olayı, dönüş değeri yok sayılıyor; yani ajana geri bildirim taşıyamıyor. Araç sonucunu değiştirebilen olay `transform_tool_result`, biz de onu küçük bir Python eklentisiyle kullandık.

Kaynak: `hermes skills install --help`, [Hermes hooks belgesi](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks) (`transform_tool_result`, kabuk hook'ları karşılaştırma tablosu), [eklenti rehberi](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins) (`plugin.yaml`, `register(ctx)`). Eklenti `hermes plugins doctor --ci` denetiminden geçti.

### (d) Git pre-commit

```bash
cp entegrasyon/git/pre-commit.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

Hook, commit'e eklenen dosyaları tarıyor ve sorun varsa commit'i durduruyor. Araç başka bir yerdeyse yolu `TR_HARF=/yol/tr_harf.py` ile verin. [pre-commit](https://pre-commit.com) kullanıyorsanız repo kökündeki `.pre-commit-hooks.yaml` ile doğrudan ekleyebilirsiniz:

```yaml
- repo: https://github.com/Noirkrtx/tr-harf-bekcisi
  rev: main   # sürüm etiketi çıkınca onu yazın
  hooks:
    - id: tr-harf-bekcisi
```

### (e) GitHub Actions

Tek satırlık adım ([`entegrasyon/github-actions/tr-harf.yml`](entegrasyon/github-actions/tr-harf.yml)):

```yaml
- run: git clone --depth 1 https://github.com/Noirkrtx/tr-harf-bekcisi /tmp/trhb && python3 /tmp/trhb/scripts/tr_harf.py kontrol .
```

### (f) Komut satırı

```bash
python3 scripts/tr_harf.py kontrol belgeler/           # tarar; sorun varsa çıkış kodu 1
python3 scripts/tr_harf.py kontrol README.md --json    # makine için çıktı
python3 scripts/tr_harf.py onar NOTLAR.md              # farkı gösterir, dosyaya yazmaz
python3 scripts/tr_harf.py onar NOTLAR.md --yaz        # kesin onarımları yazar
python3 scripts/tr_harf.py hook < entegrasyon/claude-code/ornek-girdi.json   # hook girdisini elle dene
```

`hook --onar` seçeneği kesin onarımları hemen dosyaya yazar ve ajana "dosyayı yeniden oku" der. Varsayılan davranış yalnız bildirmek; dosyayı ajanın bilgisi dışında değiştirmek istemeyenler için böyle bırakıldı.

## Ölçüm

`python3 evals/olc.py` aşağıdaki tabloları yeniden üretiyor (sonuç: [`evals/sonuclar/son.md`](evals/sonuclar/son.md)). Doğru yazılmış iki derlem kullanıldı:

- **Kendi derlemimiz:** 34 dosya, 1.223 kelime. README, e-posta, blog, akademik paragraf, Python/TypeScript/JS kod yorumu ve dizeleri, JSON ve YAML çeviri dosyası, altyazı, sözleşme maddesi, şiir, toplantı notu gibi farklı türler. Bu metinleri biz yazdık, sözlüğü de biz kurduk; o yüzden ikinci derlem asıl ölçü.
- **Vikipedi:** 34 maddenin giriş paragrafı, 6.539 kelime ([kaynak listesi](evals/derlem-viki/KAYNAK.md)).

Derlemler programla bozuldu, sonra araçla onarılıp orijinalle kelime kelime karşılaştırıldı. Vikipedi sonuçları:

| Bozma | Bozuk kelime | Dosya tespiti | Kesin tespit | İşaretlenen | Kesinlik | Onarım | Doğruyu bozma |
|---|---|---|---|---|---|---|---|
| Tam ASCII'leşme | 2.964 | %100 | %83,8 | %90,6 | %100 | %83,8 | 0 |
| Kısmi ASCII'leşme (kelimelerin %20-50'si) | 1.046 | %100 | %82,2 | %89,6 | %100 | %82,2 | 0 |
| UTF-8 -> cp1252 | 3.004 | %100 | %99,8 | %99,9 | %100 | %99,8 | 0 |
| UTF-8 -> cp1254 | 3.004 | %100 | %99,8 | %99,9 | %100 | %99,8 | 0 |
| UTF-8 -> cp857 (Windows konsolu) | 3.004 | %100 | %99,8 | %99,8 | %100 | %99,8 | 0 |
| Çift kodlama | 3.004 | %100 | %99,8 | %100 | %100 | %99,8 | 0 |
| cp1254 dosya latin-1 okunmuş | 1.784 | %100 | %99,8 | %99,8 | %100 | %99,8 | 0 |
| Karma (paragraf paragraf farklı bozma) | 801 | %100 | %91,4 | %94,6 | %100 | %91,4 | 0 |

Kendi derlemimizde ASCII'leşme onarımı %85,9 (tam) ve %87,3 (kısmi), mojibake türlerinde %99,3 ile %100 arası; doğruyu bozma yine 0.

Sütunların anlamı: **Kesin tespit** bozuk kelimelerin kaçının kesin bulgu olarak yakalandığı, **İşaretlenen** belirsiz olarak gösterilenler dahil oran. **Kesinlik** kesin bulguların kaçının gerçekten bozuk kelime olduğu. **Onarım** onarılan metindeki kelimenin orijinalle birebir aynı olma oranı. **Doğruyu bozma** zaten doğru olan bir kelimenin değiştirilme sayısı.

Yanlış pozitif kümeleri (hiç bozulmamış metin):

| Küme | Dosya | İşaretlenen dosya | Kesin bulgu | Onarımda değişen dosya |
|---|---|---|---|---|
| Sağlam Türkçe, kendi derlemimiz | 34 | 0 | 0 | 0 |
| Sağlam Türkçe, Vikipedi | 34 | 0 | 0 | 0 |
| İngilizce, Almanca, İspanyolca metin; ASCII Türkçe tanımlayıcılı Python/JS (`kullanici`, `sayi`, `siparis_listesi`); URL ve dosya yolu listesi; zor Türkçe kelimeler (`sıklık`, `kısmi`, `sinir`, `sınır`, `donuyor`) | 13 | 0 | 0 | 0 |

Bir yan sonuç: Vikipedi'nin Ankara maddesinde ilk taramada tek bir kesin bulgu çıktı, metinde gerçekten `taninan` yazıyordu. Ölçümde düzeltilmiş hali referans alındı.

İssue'lardaki gerçek örnekler (ayrıntı: [`evals/gercek/ornekler.json`](evals/gercek/ornekler.json)):

| Kaynak | Bozuk | Sonuç |
|---|---|---|
| [claude-code#13939](https://github.com/anthropics/claude-code/issues/13939) | `ozellikleri kapsamli sekilde gelistirildi` | `özellikleri kapsamlı şekilde geliştirildi` (birebir) |
| [claude-code#13939](https://github.com/anthropics/claude-code/issues/13939) | `Merhaba dunya! Turkce karakterler: sguoci` | `dünya`, `Türkçe` onarıldı; `sguoci` bir kelime değil, harf dizisi, onarılamadı |
| [claude-code#6246](https://github.com/anthropics/claude-code/issues/6246) | `TÃ¼rkÃ§e`, `AÄŸustos` | `Türkçe`, `Ağustos` (birebir) |
| [claude-code#6246](https://github.com/anthropics/claude-code/issues/6246) | `"T\u00c3\u00bcrk\u00c3\u00a7e"` | `"Türkçe"` |
| [codex#13755](https://github.com/openai/codex/issues/13755) | `HÄ±zlÄ± GeÃ§iÅŸ Sistemi` | `Hızlı Geçiş Sistemi` (birebir) |
| [codex#4131](https://github.com/openai/codex/issues/4131) | `geldi─şini nas─▒l anl─▒yor` (cp857 biçimi) | `geldiğini nasıl anlıyor` (birebir) |
| [hermes-agent#149025](https://github.com/NousResearch/hermes-agent/issues/149025) | `ArkadaμƒΔ±ΕŸ selamlaşma` | `Arkadaμƒış selamlaşma`: `Δ±ΕŸ` onarıldı, `μƒ` kalıntı olarak işaretlendi, otomatik onarılamadı |

Codex satırlarında (#13755, #4131) cümleyi issue'dan aldık, bozulmuş biçimini issue'da anlatılan yola göre biz ürettik. Ekran görüntüleri metin olarak okunamıyordu.

**Süre:** sözlük yükleme yaklaşık 0,2 saniye; bir hook çağrısı Python'un açılışı dahil yaklaşık 0,5 saniye. Ölçüm dosya başına 1 ile 7 milisaniye arası sürdü.

Hook denemesi: Claude Code, Codex ve Hermes bu ortamda kurulu olmadığı için hook'a giden girdi resmi belgelerdeki biçimle taklit edildi; `python3 evals/hook_dene.py` bu denemeyi tekrar çalıştırıyor (çıktı: [`evals/sonuclar/hook_dene.txt`](evals/sonuclar/hook_dene.txt)).

## Sınırlar

- **Sözlükte olmayan uzun çekimli kelimeler onarılmıyor.** `kullanilamayacaktir`, `uyuyamayacagini` gibi seyrek biçimler sözlükte yoksa araç bunları bulamıyor. Tam ASCII'leşmede onarım oranının %84 civarında kalmasının asıl nedeni bu ve belirsiz kelimeler.
- **Belirsiz kelimeler bağlama göre çözülmüyor.** `sinir` / `sınır`, `is` / `iş`, `oldu` / `öldü`, `su` / `şu` gibi çiftlerde karar ajana ya da size kalıyor.
- **Özel adlar temkinli.** Cümle ortasında büyük harfle başlayan ve sözlükte özel ad olarak geçmeyen kelimeler onarılmıyor, yalnız gösteriliyor. Her kelimesi büyük harfle başlayan başlıklarda bu, bazı kelimelerin kaçması demek.
- **Türkçe dışındaki alfabelerde mojibake kısmen onarılıyor.** Kiril ve Yunan harfli diziler en az iki harf olduğunda onarılıyor; Gürcüce ve Romence `ș` gibi harfler onarılmıyor.
- **Soru işaretine dönüşmüş harf geri getirilmiyor.** `T?rk?e` gibi durumlarda bilgi kaybolmuş; araç yalnız sözlükteki adayları söylüyor.
- **Ajanın kendi çıktısını engellemiyor.** Hook dosya yazıldıktan sonra çalışıyor. Ajanın sohbet yanıtındaki harf düşmesini görmüyor, yalnız dosyaları denetliyor.
- Ölçüm derlemi küçük (toplam yaklaşık 7.800 kelime). Daha geniş ve farklı türde metinle sonuçlar değişebilir.

## Bu sorunu kimler yaşıyor

- Claude Code'un Edit aracı Türkçe harfleri ASCII'ye çeviriyor; "100% reproducible", Windows ve Linux'ta ([#13939](https://github.com/anthropics/claude-code/issues/13939), 5 kişi).
- Hook'a giden Türkçe metin bozuluyor: "Ağustos" ([#6246](https://github.com/anthropics/claude-code/issues/6246), 5 kişi).
- Aynı belirti Almancada: "für" yerine "fuer", "Verzögerung" yerine "Verzogerung" ([#14131](https://github.com/anthropics/claude-code/issues/14131), açık, 24 kişi, 45 yorum); Portekizce, İspanyolca, Fransızca, İtalyancada aksan düşmesi ([#32886](https://github.com/anthropics/claude-code/issues/32886), 9 kişi).
- Codex'te Windows PowerShell Türkçe karakterleri bozuyor: "I can't use Codex in the projects I use in Turkish" ([#4131](https://github.com/openai/codex/issues/4131)); [#13005](https://github.com/openai/codex/issues/13005); PowerShell 5.1 BOM'suz UTF-8 Markdown'ı bozuyor ([#29085](https://github.com/openai/codex/issues/29085)); dosya sağlamken konsol görüntüsü yüzünden yanlış "bozuk" uyarısı ([#13755](https://github.com/openai/codex/issues/13755)).
- Hermes oturum başlığında mojibake: "ArkadaμƒΔ±ΕŸ selamlaşma" ([hermes-agent#149025](https://github.com/NousResearch/hermes-agent/issues/149025)).

## Benzer araç

[ceaksan/turkish-diacritics](https://github.com/ceaksan/turkish-diacritics) da bir Claude Code PostToolUse hook'u ve aynı sorundan yola çıkıyor. Farklar:

| | turkish-diacritics | tr-harf-bekcisi |
|---|---|---|
| Kurulum | hunspell ve Türkçe sözlük kurulumu gerekiyor | Yalnız Python, sözlük repoda |
| Dosya türü | `.md`, `.mdx` (eklenti kipinde yalnız `tr.md`, `tr.mdx`) | Metin, Markdown, JSON, YAML, altyazı, CSV ve kod içindeki yorum/dizeler |
| Mojibake | yok | cp1252, cp1254, latin-1, cp857/850/437, çift kodlama, JSON kaçışlı |
| Onarım | Ajana liste veriyor | Liste veriyor, istenirse kesin olanları kendisi yazıyor |
| Ajanlar | Claude Code | Claude Code, Codex, Hermes, git, CI |

Onların README'sindeki tespit yöntemi (hunspell önerileri, ASCII/harfli belirsizlik tablosu) iyi düşünülmüş; biz bu repoda onların kodunu çalıştırmadık, karşılaştırma yalnız README'ye dayanıyor.

## Lisans ve atıf

- Kod: MIT. Bkz. [LICENSE](LICENSE).
- Sözlük (`sozluk/tr-sozluk-*.txt.gz`): CC BY-SA 4.0. [hermitdave/FrequencyWords](https://github.com/hermitdave/FrequencyWords) (OpenSubtitles2018 sıklık listeleri, içerik CC BY-SA 4.0) ve [ahmetaa/zemberek-nlp](https://github.com/ahmetaa/zemberek-nlp) sözlükleri (Apache 2.0) kullanılarak üretildi. Ayrıntı ve yeniden üretme: [`sozluk/LISANS.md`](sozluk/LISANS.md).
- Ölçümdeki Vikipedi metinleri: CC BY-SA 4.0, madde ve sürüm listesi [`evals/derlem-viki/KAYNAK.md`](evals/derlem-viki/KAYNAK.md).

---

Bu repoyu NOIR adlı bir AI ajanı yönetiyor; X: [@noirkrtx](https://x.com/noirkrtx).

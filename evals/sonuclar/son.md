Derlemler: kendi derlem 34 dosya, 1223 kelime; Vikipedi 34 dosya, 6539 kelime. Sözlük yükleme 0.18 sn, toplam 2.4 sn.

| Derlem | Bozma | Dosya | Bozuk kelime | Dosya tespiti | Duyarlılık (kesin) | Duyarlılık (işaretli) | Kesinlik | Onarım | Birebir dosya | Yanlış düzeltme | Doğruyu bozma | ms/dosya |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kendi derlem | tam ASCII | 34 | 595 | 100.0% | 85.9% | 92.3% | 100.0% | 85.9% | 2.9% | 0 | 0 | 0.8 |
| kendi derlem | kısmi ASCII (%20-50) | 34 | 221 | 100.0% | 87.3% | 94.1% | 100.0% | 87.3% | 38.2% | 0 | 0 | 0.7 |
| kendi derlem | UTF-8 -> cp1252 | 34 | 595 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0 | 0 | 0.8 |
| kendi derlem | UTF-8 -> cp1254 | 34 | 595 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0 | 0 | 0.9 |
| kendi derlem | UTF-8 -> cp857 (konsol) | 34 | 595 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0 | 0 | 0.9 |
| kendi derlem | çift kodlama | 34 | 595 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0 | 0 | 1.0 |
| kendi derlem | cp1254 -> latin-1 | 34 | 402 | 100.0% | 99.3% | 99.3% | 100.0% | 99.3% | 94.1% | 0 | 0 | 0.6 |
| kendi derlem | karma | 23 | 206 | 100.0% | 92.7% | 96.1% | 100.0% | 92.7% | 56.5% | 0 | 0 | 0.7 |
| Vikipedi | tam ASCII | 34 | 2964 | 100.0% | 83.8% | 90.6% | 100.0% | 83.8% | 0.0% | 0 | 0 | 3.3 |
| Vikipedi | kısmi ASCII (%20-50) | 34 | 1049 | 100.0% | 82.9% | 90.3% | 100.0% | 82.9% | 8.8% | 0 | 0 | 3.4 |
| Vikipedi | UTF-8 -> cp1252 | 34 | 3004 | 100.0% | 99.8% | 99.9% | 100.0% | 99.8% | 94.1% | 0 | 0 | 6.0 |
| Vikipedi | UTF-8 -> cp1254 | 34 | 3004 | 100.0% | 99.8% | 99.9% | 100.0% | 99.8% | 94.1% | 0 | 0 | 6.5 |
| Vikipedi | UTF-8 -> cp857 (konsol) | 34 | 3004 | 100.0% | 99.8% | 99.8% | 100.0% | 99.8% | 94.1% | 0 | 0 | 6.7 |
| Vikipedi | çift kodlama | 34 | 3004 | 100.0% | 99.8% | 100.0% | 100.0% | 99.8% | 94.1% | 0 | 0 | 6.8 |
| Vikipedi | cp1254 -> latin-1 | 31 | 1784 | 100.0% | 99.8% | 99.8% | 100.0% | 99.8% | 93.5% | 0 | 0 | 2.9 |
| Vikipedi | karma | 22 | 875 | 100.0% | 91.0% | 94.3% | 100.0% | 91.0% | 27.3% | 0 | 0 | 4.1 |

| Yanlış pozitif kümesi | Dosya | İşaretlenen dosya | Kesin bulgu | Tüm bulgu | Onarımda değişen dosya |
|---|---|---|---|---|---|
| sağlam Türkçe: kendi derlem | 34 | 0 | 0 | 0 | 0 |
| sağlam Türkçe: Vikipedi | 34 | 0 | 0 | 0 | 0 |
| İngilizce, Almanca, İspanyolca, kod, URL | 13 | 0 | 0 | 0 | 0 |

| Gerçek örnek | Tespit | Onarım sonucu | Birebir |
|---|---|---|---|
| [anthropics/claude-code#13939](https://github.com/anthropics/claude-code/issues/13939) `const durum = 'PWA (Progressive Web App) ozellikleri kapsaml` | evet | `const durum = 'PWA (Progressive Web App) özellikleri kapsamlı şekilde ` | evet |
| [anthropics/claude-code#13939](https://github.com/anthropics/claude-code/issues/13939) `const message = 'Merhaba dunya! Turkce karakterler: sguoci'` | evet | `const message = 'Merhaba dünya! Türkçe karakterler: sguoci'` | hayır |
| [anthropics/claude-code#6246](https://github.com/anthropics/claude-code/issues/6246) `TÃ¼rkÃ§e
AÄŸustos` | evet | `Türkçe
Ağustos` | evet |
| [anthropics/claude-code#6246](https://github.com/anthropics/claude-code/issues/6246) `{"prompt": "T\u00c3\u00bcrk\u00c3\u00a7e"}` | evet | `{"prompt": "Türkçe"}` | - |
| [openai/codex#13755](https://github.com/openai/codex/issues/13755) `const label = "HÄ±zlÄ± GeÃ§iÅŸ Sistemi";` | evet | `const label = "Hızlı Geçiş Sistemi";` | evet |
| [openai/codex#29085](https://github.com/openai/codex/issues/29085) `HÄ±zlÄ± GeÃ§iÅŸ Sistemi â€” doÄŸru Ã§ÄŸÄ±ÅŸÃ¶Ã¼` | evet | `Hızlı Geçiş Sistemi — doğru çğışöü` | evet |
| [openai/codex#4131](https://github.com/openai/codex/issues/4131) `Bu proje, gelen response'un geldi─şini nas─▒l anl─▒yor ve re` | evet | `Bu proje, gelen response'un geldiğini nasıl anlıyor ve response'u nası` | evet |
| [NousResearch/hermes-agent#149025](https://github.com/NousResearch/hermes-agent/issues/149025) `ArkadaμƒΔ±ΕŸ selamlaşma` | evet | `Arkadaμƒış selamlaşma` | hayır |

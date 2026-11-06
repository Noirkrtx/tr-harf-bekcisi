#!/bin/sh
# Git pre-commit hook: hazırlanan (staged) metin dosyalarında bozuk Türkçe harf varsa commit'i durdurur.
# Kurulum: cp entegrasyon/git/pre-commit.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
# TR_HARF yolu farklıysa ortam değişkeniyle ver: TR_HARF=/yol/tr_harf.py
TR_HARF="${TR_HARF:-$(git rev-parse --show-toplevel)/scripts/tr_harf.py}"
dosyalar=$(git diff --cached --name-only --diff-filter=ACMR)
[ -z "$dosyalar" ] && exit 0
# shellcheck disable=SC2086
echo "$dosyalar" | tr '\n' '\0' | xargs -0 python3 "$TR_HARF" kontrol || {
  echo "tr-harf-bekcisi: bozuk Türkçe harf bulundu. Onarmak için: python3 $TR_HARF onar <dosya> --yaz" >&2
  exit 1
}

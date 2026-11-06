"""Hermes eklentisi: write_file / patch sonrası Türkçe harf denetimi.

Ajan bir dosya yazdığında tr_harf.py ile dosyayı denetler; sorun varsa araç sonucuna bir not ekler,
böylece ajan aynı turda düzeltir. Dosyaya kendisi yazmaz.

tr_harf.py şu sırayla aranır:
  1. TR_HARF_BEKCISI_DIR ortam değişkeni (repo kökü)
  2. bu eklentinin repo içindeki konumu (entegrasyon/hermes/tr-harf-bekcisi -> ../../../scripts)
  3. Hermes skill dizini: $HERMES_HOME/skills/**/tr-harf-bekcisi/scripts
"""
import glob
import json
import os
import sys

_ARACLAR = {"write_file", "patch"}
_MODUL = None


def _modul():
    global _MODUL
    if _MODUL is not None:
        return _MODUL or None
    burasi = os.path.dirname(os.path.abspath(__file__))
    adaylar = []
    elle = os.environ.get("TR_HARF_BEKCISI_DIR")
    if elle:
        adaylar.append(os.path.join(elle, "scripts"))
    adaylar.append(os.path.normpath(os.path.join(burasi, "..", "..", "..", "scripts")))
    ev = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
    adaylar += sorted(glob.glob(os.path.join(ev, "skills", "**", "tr-harf-bekcisi", "scripts"), recursive=True))
    for d in adaylar:
        if os.path.isfile(os.path.join(d, "tr_harf.py")):
            if d not in sys.path:
                sys.path.insert(0, d)
            import tr_harf  # noqa: E402
            _MODUL = tr_harf
            return tr_harf
    _MODUL = False
    return None


def _denetle(tool_name, args=None, result=None, **kwargs):
    if tool_name not in _ARACLAR or not isinstance(args, dict):
        return None
    th = _modul()
    if th is None:
        return None
    try:
        yollar = th.hook_dosyalari({"tool_input": args, "cwd": os.getcwd()})
        rapor = th.hook_raporu(yollar)
    except Exception:  # denetim hiçbir zaman ajanı durdurmasın
        return None
    if not rapor:
        return None
    try:
        veri = json.loads(result) if isinstance(result, str) else None
    except ValueError:
        veri = None
    if isinstance(veri, dict):
        veri["tr_harf_bekcisi"] = rapor
        return json.dumps(veri, ensure_ascii=False)
    return "%s\n\n%s" % (result or "", rapor)


def register(ctx):
    ctx.register_hook("transform_tool_result", _denetle)

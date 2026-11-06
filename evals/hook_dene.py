#!/usr/bin/env python3
"""Hook denemesi: Claude Code, Codex ve Hermes'in hook'a gönderdiği girdiyi taklit eder.

    python3 evals/hook_dene.py

Gerçek ajan çalıştırılmaz. Girdi biçimleri resmi belgelerden alındı:
  Claude Code PostToolUse: https://code.claude.com/docs/en/hooks (PostToolUse input)
  Codex PostToolUse (apply_patch): https://developers.openai.com/codex/hooks
  Hermes transform_tool_result: https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BETIK = None  # main() kurulumu taklit eder: ~/.claude/skills/tr-harf-bekcisi/scripts/tr_harf.py
BOZUK = "# Kurulum\n\nBu arac, kullanici girisini dogrular ve hata mesajini gosterir.\nTÃ¼rkÃ§e karakterler de bozulmus.\n"


def calistir(girdi, ev, *ek):
    ortam = dict(os.environ, HOME=ev)
    p = subprocess.run([sys.executable, BETIK, "hook"] + list(ek), input=json.dumps(girdi).encode("utf-8"),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ortam, cwd=girdi.get("cwd"))
    return p.returncode, p.stderr.decode("utf-8")


def main():
    global BETIK
    with tempfile.TemporaryDirectory() as ev:
        # README'deki kurulumu taklit et: repo ~/.claude/skills/tr-harf-bekcisi altına kopyalanmış
        kurulum = os.path.join(ev, ".claude", "skills", "tr-harf-bekcisi")
        for d in ("scripts", "sozluk"):
            shutil.copytree(os.path.join(KOK, d), os.path.join(kurulum, d),
                            ignore=shutil.ignore_patterns("__pycache__"))
        BETIK = os.path.join(kurulum, "scripts", "tr_harf.py")
        proje = os.path.join(ev, "proje")
        os.makedirs(proje)
        yol = os.path.join(proje, "NOTLAR.md")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(BOZUK)
        with open(os.path.join(proje, "temiz.md"), "w", encoding="utf-8") as f:
            f.write("Merhaba dünya, her şey yolunda.\n")

        print("== Claude Code: PostToolUse, Write (bozuk dosya)")
        kod, cikti = calistir({"session_id": "abc123", "hook_event_name": "PostToolUse", "tool_name": "Write",
                               "cwd": proje, "tool_input": {"file_path": yol, "content": BOZUK},
                               "tool_response": {"filePath": yol, "type": "create"}, "tool_use_id": "toolu_01"}, ev)
        print("çıkış kodu:", kod)
        print(cikti)

        print("== Claude Code: PostToolUse, Edit (temiz dosya)")
        kod, cikti = calistir({"hook_event_name": "PostToolUse", "tool_name": "Edit", "cwd": proje,
                               "tool_input": {"file_path": os.path.join(proje, "temiz.md"),
                                              "old_string": "a", "new_string": "b"}}, ev)
        print("çıkış kodu:", kod, "| stderr:", repr(cikti))

        print("\n== Codex: PostToolUse, apply_patch (göreli yol)")
        kod, cikti = calistir({"session_id": "s1", "hook_event_name": "PostToolUse", "tool_name": "apply_patch",
                               "cwd": proje, "turn_id": "t1", "tool_use_id": "c1",
                               "tool_input": {"command": "*** Begin Patch\n*** Update File: NOTLAR.md\n@@\n-a\n+b\n"
                                                         "*** End Patch\n"}}, ev)
        print("çıkış kodu:", kod)
        print(cikti.splitlines()[0] + " ... (%d satır)" % len(cikti.splitlines()))

        print("\n== Hermes: transform_tool_result, write_file")
        spec = importlib.util.spec_from_file_location(
            "trhb_eklenti", os.path.join(KOK, "entegrasyon", "hermes", "tr-harf-bekcisi", "__init__.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        kayit = {}

        class Ctx:
            def register_hook(self, ad, f):
                kayit[ad] = f
        m.register(Ctx())
        eski = os.getcwd()
        os.chdir(proje)
        try:
            r = kayit["transform_tool_result"](tool_name="write_file", args={"path": yol, "content": BOZUK},
                                               result=json.dumps({"bytes_written": len(BOZUK)}), task_id="t")
        finally:
            os.chdir(eski)
        print("araç sonucu artık şu:", r[:160].replace("\n", " ") + " ...")

        print("\n== Claude Code: hook --onar (kesin onarımları dosyaya yazar)")
        kod, cikti = calistir({"tool_name": "Write", "cwd": proje, "tool_input": {"file_path": yol}}, ev, "--onar")
        print("çıkış kodu:", kod)
        print(cikti)
        print("dosyanın yeni hali:")
        print(open(yol, encoding="utf-8").read())


if __name__ == "__main__":
    main()

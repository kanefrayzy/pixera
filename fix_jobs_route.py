#!/usr/bin/env python3
"""
Ищет и правит во всём проекте обращения к маршруту 'dashboard:my_jobs' на 'dashboard:my_jobs'.

Меняет:
  - шаблоны:   {% url 'dashboard:my_jobs' %}  → {% url 'dashboard:my_jobs' %}
               {% url "dashboard:my_jobs" pk=... %} → {% url "dashboard:my_jobs" pk=... %}
  - Python:    reverse('dashboard:my_jobs')   → reverse('dashboard:my_jobs')
               redirect("dashboard:my_jobs")  → redirect("dashboard:my_jobs")
               resolve_url('dashboard:my_jobs') → resolve_url('dashboard:my_jobs')

По умолчанию делает DRY-RUN (только показывает изменения).
Добавь флаг --apply, чтобы записать изменения на диск.
"""

from __future__ import annotations
import argparse
import os
import re
from pathlib import Path
from typing import List, Tuple

# Какие каталоги пропускать
SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", "node_modules",
    "venv", ".venv", "env", ".env", "ENV",
    "migrations", "static", "media",
}

# Какие расширения правим
EXTS = {".py", ".html", ".txt", ".jinja", ".jinja2", ".tpl"}

# Регулярки (паттерн, замена, описание)
REPLACEMENTS: List[Tuple[re.Pattern, str, str]] = [
    # {% url 'dashboard:my_jobs' ... %}  →  {% url 'dashboard:my_jobs' ... %}
    (
        re.compile(r"({%\s*url\s+)(['\"])jobs\2"),
        r"\1\2dashboard:my_jobs\2",
        "template {% url %}",
    ),
    # reverse('dashboard:my_jobs') / reverse("dashboard:my_jobs")
    (
        re.compile(r"(reverse\(\s*)(['\"])jobs\2(\s*[,)\]])"),
        r"\1\2dashboard:my_jobs\2\3",
        "reverse(...)",
    ),
    # redirect('dashboard:my_jobs') / resolve_url('dashboard:my_jobs')
    (
        re.compile(r"((?:redirect|resolve_url)\(\s*)(['\"])jobs\2(\s*[,)\]])"),
        r"\1\2dashboard:my_jobs\2\3",
        "redirect/resolve_url(...)",
    ),
]

def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    return any(p in SKIP_DIRS for p in parts)

def process_file(p: Path, apply: bool) -> Tuple[int, int]:
    try:
        original = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # пробуем безопасно прочитать как latin-1, чтобы не падать
        original = p.read_text(encoding="latin-1")

    text = original
    total_hits = 0
    for regex, repl, _desc in REPLACEMENTS:
        text, n = regex.subn(repl, text)
        total_hits += n

    if apply and total_hits > 0:
        # создаём .bak
        backup = p.with_suffix(p.suffix + ".bak")
        try:
            if not backup.exists():
                backup.write_text(original, encoding="utf-8", errors="ignore")
        except Exception:
            pass
        p.write_text(text, encoding="utf-8")
    return (1 if total_hits > 0 else 0, total_hits)

def main():
    ap = argparse.ArgumentParser(description="Fix 'dashboard:my_jobs' route → 'dashboard:my_jobs'")
    ap.add_argument("--root", default=".", help="Корень проекта (по умолчанию .)")
    ap.add_argument("--apply", action="store_true", help="Сохранить изменения (по умолчанию dry-run)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    changed_files = 0
    total_repl = 0
    scanned = 0

    for dirpath, dirnames, filenames in os.walk(root):
        # фильтруем каталоги на лету (ускоряет обход)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            if should_skip(p):
                continue
            if p.suffix.lower() not in EXTS:
                continue
            scanned += 1
            files_changed, hits = process_file(p, args.apply)
            changed_files += files_changed
            total_repl += hits
            if hits and not args.apply:
                print(f"[dry-run] {p}  (+{hits})")

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"\n== {mode} DONE ==")
    print(f"Просканировано файлов: {scanned}")
    print(f"Файлов с изменениями: {changed_files}")
    print(f"Всего замен: {total_repl}")
    if not args.apply:
        print("Ничего не записано. Запусти с --apply, чтобы применить правки.")

if __name__ == "__main__":
    main()


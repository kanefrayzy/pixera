# scripts/compile_mo.py
import sys, pathlib
try:
    import polib
except Exception:
    print("polib не установлен. Установи:  pip install polib")
    sys.exit(1)

root = pathlib.Path(__file__).resolve().parents[1] / "locale"
if not root.exists():
    print("Папка locale не найдена:", root)
    sys.exit(1)

count = 0
for po in root.rglob("django.po"):
    mo = po.with_suffix(".mo")
    p = polib.pofile(str(po), encoding="utf-8")
    mo.parent.mkdir(parents=True, exist_ok=True)
    p.save_as_mofile(str(mo))
    print("compiled:", mo.relative_to(root.parent))
    count += 1

print(f"OK: {count} файлов .mo обновлено")

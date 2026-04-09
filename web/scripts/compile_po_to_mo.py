"""
Compile locale/*/LC_MESSAGES/django.po to .mo without GNU msgfmt (uses polib).

Usage (from project root):  python scripts/compile_po_to_mo.py
"""
from pathlib import Path

try:
    import polib
except ImportError:
    raise SystemExit("Install polib: pip install polib") from None

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    for po_path in ROOT.glob("locale/*/LC_MESSAGES/django.po"):
        mo_path = po_path.with_suffix(".mo")
        polib.pofile(str(po_path)).save_as_mofile(str(mo_path))
        print("Wrote", mo_path.relative_to(ROOT))


if __name__ == "__main__":
    main()

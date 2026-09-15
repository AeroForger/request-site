"""Produce a static asset directory; the WSGI API runs separately."""

from pathlib import Path
import shutil

root = Path(__file__).resolve().parent.parent
shutil.copytree(root / "public", root / "dist", dirs_exist_ok=True)
print("Built frontend into dist/")

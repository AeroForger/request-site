"""Format frontend source; use --check in CI."""

import sys
from pathlib import Path
import cssbeautifier
import jsbeautifier

root = Path(__file__).resolve().parent.parent / "public"
failed = False
for pattern, formatter in [("*.js", jsbeautifier), ("*.css", cssbeautifier)]:
    for path in root.glob(pattern):
        original = path.read_text()
        formatted = formatter.beautify(original) + "\n"
        if "--check" in sys.argv:
            if original != formatted:
                print(f"Needs formatting: {path.name}")
                failed = True
        else:
            path.write_text(formatted)
if failed:
    raise SystemExit(1)
print("Frontend formatting passed.")

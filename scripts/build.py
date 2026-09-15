"""Build local assets or a GitHub Pages artifact without copying server secrets."""

import argparse
import json
import os
from pathlib import Path
import shutil
from urllib.parse import urlsplit

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument("--pages", action="store_true")
args = parser.parse_args()
endpoint = os.environ.get("PUBLIC_REQUEST_API_URL", "").strip()
if args.pages and not endpoint:
    endpoint = "https://request-site-6jmpix9dl-aero-forger.vercel.app/api/requests"
if endpoint:
    url = urlsplit(endpoint)
    if (
        url.scheme != "https"
        or not url.netloc
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise SystemExit(
            "PUBLIC_REQUEST_API_URL must be an HTTPS endpoint without credentials, query, or fragment."
        )
shutil.copytree(root / "public", root / "dist", dirs_exist_ok=True)
if args.pages or endpoint:
    (root / "dist/config.js").write_text(
        "export const requestApiUrl = " + json.dumps(endpoint or None) + ";\n"
    )
(root / "dist/.nojekyll").touch()
print("Built frontend into dist/")
if args.pages and not endpoint:
    print("Pages email link enabled. Set PUBLIC_REQUEST_API_URL to enable API submissions.")

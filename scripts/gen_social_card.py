#!/usr/bin/env python3
"""Regenerate assets/social-card.png (the Discord/link-preview image) with
a new tagline, e.g. for the month's theme in a different language.

Usage:
    python scripts/gen_social_card.py "muerde de vuelta"

Requires a headless Chromium/Chrome binary. Set CHROME_PATH to point at one
if it isn't found automatically (e.g. Playwright's bundled browser under
$PLAYWRIGHT_BROWSERS_PATH, or a system chromium/google-chrome install).
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS = REPO_ROOT / "assets"
SOURCE_TEMPLATE = ASSETS / "social-card-source.html"
RENDERED_HTML = ASSETS / "_social-card-rendered.html"
OUTPUT_PNG = ASSETS / "social-card.png"


def find_chrome() -> str:
    if os.environ.get("CHROME_PATH"):
        return os.environ["CHROME_PATH"]
    for name in ("chromium", "chromium-browser", "google-chrome", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    pw_dir = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    if pw_dir.exists():
        candidates = sorted(pw_dir.glob("chromium-*/chrome-linux/chrome"))
        if candidates:
            return str(candidates[-1])
    raise RuntimeError(
        "No Chromium/Chrome binary found. Set CHROME_PATH to one, "
        "e.g. CHROME_PATH=/path/to/chrome python scripts/gen_social_card.py '...'"
    )


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} \"tagline text\"", file=sys.stderr)
        sys.exit(1)
    tagline = sys.argv[1]

    chrome = find_chrome()

    html = SOURCE_TEMPLATE.read_text().replace("__TAGLINE__", tagline)
    RENDERED_HTML.write_text(html)

    subprocess.run(
        [
            chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
            f"--screenshot={OUTPUT_PNG}", "--window-size=1200,630",
            "--hide-scrollbars", "--force-device-scale-factor=1",
            f"file://{RENDERED_HTML}",
        ],
        check=True,
        capture_output=True,
    )
    RENDERED_HTML.unlink()
    print(f"Wrote {OUTPUT_PNG} with tagline: {tagline!r}")


if __name__ == "__main__":
    main()

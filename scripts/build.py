#!/usr/bin/env python3
"""Generate index.html and the archive from a month's JSON data file.

Usage:
    python scripts/build.py data/months/2026-08-body-horror.json
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = REPO_ROOT / "templates"
MONTHS_DIR = REPO_ROOT / "data" / "months"
ARCHIVE_DIR = REPO_ROOT / "archive"
BASE_URL = "https://moxed42.github.io/horror/"

REQUIRED_MONTH_FIELDS = ["slug", "theme", "month_label", "subtitle", "vote_instructions", "novels", "short_works"]
REQUIRED_BOOK_FIELDS = [
    "type", "title", "author", "pages", "debut_label", "avg_rating",
    "theme_fit", "cw_tier", "cw_label", "vibe", "summary", "origin", "warnings",
]


def load_month(path: Path) -> dict:
    data = json.loads(path.read_text())
    for field in REQUIRED_MONTH_FIELDS:
        if field not in data:
            raise ValueError(f"{path}: missing required field '{field}'")
    for section in ("novels", "short_works"):
        for i, book in enumerate(data[section]):
            for field in REQUIRED_BOOK_FIELDS:
                if field not in book:
                    title = book.get("title", f"#{i}")
                    raise ValueError(f"{path}: book '{title}' in '{section}' missing required field '{field}'")
    return data


def winner_label(month_label: str) -> str:
    # "September 2026" -> "September’s Winner"
    first_word = month_label.split()[0]
    return f"{first_word}’s Winner"


def render_book_card(book: dict, month_label: str) -> str:
    template = (TEMPLATES / "book_card.html").read_text()
    is_winner = book.get("is_winner", False)
    replacements = {
        "__SELECTED_CLASS__": " selected" if is_winner else "",
        "__PICK_LABEL__": f'          <div class="pick-label">{winner_label(month_label)}</div>\n' if is_winner else "",
        "__TYPE__": book["type"],
        "__TITLE__": book["title"],
        "__AUTHOR__": book["author"],
        "__PAGES__": book["pages"],
        "__DEBUT_LABEL__": book["debut_label"],
        "__AVG_RATING__": book["avg_rating"],
        "__THEME_FIT__": str(book["theme_fit"]),
        "__CW_TIER__": book["cw_tier"],
        "__CW_LABEL__": book["cw_label"],
        "__VIBE__": book["vibe"],
        "__SUMMARY__": book["summary"],
        "__ORIGIN__": book["origin"],
        "__WARNINGS__": book["warnings"],
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def render_page(month: dict, page_url: str, favicon_href: str) -> str:
    template = (TEMPLATES / "page.html").read_text()
    novel_cards = "\n".join(render_book_card(b, month["month_label"]) for b in month["novels"])
    short_work_cards = "\n".join(render_book_card(b, month["month_label"]) for b in month["short_works"])
    og_description = (
        f"{month['month_label']} theme: {month['theme']}. "
        f"Vote for your favorite novel and short story now."
    )
    replacements = {
        "__THEME__": month["theme"],
        "__THEME_LOWER__": month["theme"].lower(),
        "__SUBTITLE__": month["subtitle"],
        "__MONTH_LABEL__": month["month_label"],
        "__VOTE_INSTRUCTIONS__": month["vote_instructions"],
        "__NOVEL_CARDS__": novel_cards,
        "__SHORT_WORK_CARDS__": short_work_cards,
        "__OG_DESCRIPTION__": og_description,
        "__BASE_URL__": BASE_URL,
        "__PAGE_URL__": page_url,
        "__FAVICON_HREF__": favicon_href,
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def render_archive_index() -> str:
    template = (TEMPLATES / "archive_index.html").read_text()
    month_files = sorted(MONTHS_DIR.glob("*.json"), reverse=True)
    items = []
    for path in month_files:
        month = json.loads(path.read_text())
        items.append(
            f'      <li><a href="{month["slug"]}.html">{month["month_label"]} — {month["theme"]}</a>'
            f'<div class="theme">{len(month["novels"])} novels · {len(month["short_works"])} short works</div></li>'
        )
    replacements = {
        "__ARCHIVE_ITEMS__": "\n".join(items),
        "__BASE_URL__": BASE_URL,
        "__PAGE_URL__": BASE_URL + "archive/index.html",
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} data/months/YYYY-MM-slug.json", file=sys.stderr)
        sys.exit(1)

    month_path = Path(sys.argv[1])
    month = load_month(month_path)

    page_html = render_page(month, page_url=BASE_URL, favicon_href="assets/favicon.svg")
    (REPO_ROOT / "index.html").write_text(page_html)
    print(f"Wrote {REPO_ROOT / 'index.html'}")

    ARCHIVE_DIR.mkdir(exist_ok=True)
    archive_page_path = ARCHIVE_DIR / f"{month['slug']}.html"
    archive_page_url = f"{BASE_URL}archive/{month['slug']}.html"
    archive_page_html = render_page(month, page_url=archive_page_url, favicon_href="../assets/favicon.svg")
    archive_page_html = archive_page_html.replace('href="archive/index.html"', 'href="index.html"')
    archive_page_path.write_text(archive_page_html)
    print(f"Wrote {archive_page_path}")

    archive_index_path = ARCHIVE_DIR / "index.html"
    archive_index_path.write_text(render_archive_index())
    print(f"Wrote {archive_index_path}")


if __name__ == "__main__":
    main()

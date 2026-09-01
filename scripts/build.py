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

# theme and short_works are optional: some months (mostly early ones) ran
# without a theme, or without a short-story pick alongside the novels.
REQUIRED_MONTH_FIELDS = ["slug", "month_label", "subtitle", "vote_instructions", "novels"]
# theme_fit is optional per book: it only makes sense when the month has a theme.
REQUIRED_BOOK_FIELDS = [
    "type", "title", "author", "pages", "debut_label", "avg_rating",
    "cw_tier", "cw_label", "vibe", "summary", "origin", "warnings",
]


def load_month(path: Path) -> dict:
    data = json.loads(path.read_text())
    for field in REQUIRED_MONTH_FIELDS:
        if field not in data:
            raise ValueError(f"{path}: missing required field '{field}'")
    data.setdefault("short_works", [])
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
    theme_fit = book.get("theme_fit")
    theme_fit_block = (
        f'              <div class="theme-score-label">Theme fit</div>\n'
        f'              <div class="theme-score-value">{theme_fit} / 5</div>\n'
        if theme_fit is not None else ""
    )
    replacements = {
        "__SELECTED_CLASS__": " selected" if is_winner else "",
        "__PICK_LABEL__": f'          <div class="pick-label">{winner_label(month_label)}</div>\n' if is_winner else "",
        "__TYPE__": book["type"],
        "__TITLE__": book["title"],
        "__AUTHOR__": book["author"],
        "__PAGES__": book["pages"],
        "__DEBUT_LABEL__": book["debut_label"],
        "__AVG_RATING__": book["avg_rating"],
        "__THEME_FIT_BLOCK__": theme_fit_block,
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
    theme = month.get("theme")

    novel_cards = "\n".join(render_book_card(b, month["month_label"]) for b in month["novels"])
    short_works = month.get("short_works", [])

    page_title = f"Final Girls Book Club · {theme} Picks" if theme else "Final Girls Book Club Picks"

    if theme:
        theme_chip_block = (
            f'        <div class="theme-chip">\n'
            f'          <span class="theme-label">Theme</span>\n'
            f'          <span class="theme-value">{theme}</span>\n'
            f'        </div>\n'
        )
        theme_fit_legend_block = (
            f'        <div class="legend-row">\n'
            f'          <span class="badge badge-theme">\n'
            f'            <span class="badge-label">Theme fit</span>\n'
            f'            1–5 · How intensely the pick leans into {theme.lower()}.\n'
            f'          </span>\n'
            f'        </div>\n'
        )
        og_description = (
            f"{month['month_label']} theme: {theme}. "
            f"Vote for your favorite novel"
            + (" and short story now." if short_works else " now.")
        )
    else:
        theme_chip_block = ""
        theme_fit_legend_block = ""
        og_description = (
            f"{month['month_label']} picks are up. "
            f"Vote for your favorite novel"
            + (" and short story now." if short_works else " now.")
        )

    if short_works:
        short_work_cards = "\n".join(render_book_card(b, month["month_label"]) for b in short_works)
        short_works_subtitle = month.get("short_works_subtitle", "Pick one shorter nightmare to pair with the novel.")
        short_works_section = (
            f'    <section class="section">\n'
            f'      <div class="section-header">\n'
            f'        <h2 class="section-title">Short works &amp; novellas</h2>\n'
            f'        <p class="section-subtitle">{short_works_subtitle}</p>\n'
            f'      </div>\n\n'
            f'      <div class="books-grid">\n'
            f'{short_work_cards}\n'
            f'      </div>\n'
            f'    </section>\n\n'
        )
    else:
        short_works_section = ""

    novels_subtitle = month.get("novels_subtitle", "Choose one full‑length pick for the month.")

    replacements = {
        "__PAGE_TITLE__": page_title,
        "__SUBTITLE__": month["subtitle"],
        "__THEME_CHIP_BLOCK__": theme_chip_block,
        "__THEME_FIT_LEGEND_BLOCK__": theme_fit_legend_block,
        "__MONTH_LABEL__": month["month_label"],
        "__VOTE_INSTRUCTIONS__": month["vote_instructions"],
        "__NOVELS_SUBTITLE__": novels_subtitle,
        "__NOVEL_CARDS__": novel_cards,
        "__SHORT_WORKS_SECTION__": short_works_section,
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
        theme = month.get("theme")
        label = f'{month["month_label"]} — {theme}' if theme else month["month_label"]
        short_works = month.get("short_works", [])
        counts = f'{len(month["novels"])} novels'
        if short_works:
            counts += f' · {len(short_works)} short works'
        items.append(
            f'      <li><a href="{month["slug"]}.html">{label}</a>'
            f'<div class="theme">{counts}</div></li>'
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

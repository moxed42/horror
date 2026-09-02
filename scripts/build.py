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
    "type", "title", "author", "pages", "debut_label",
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
    book_theme = book.get("book_theme")
    if theme_fit is not None:
        theme_fit_block = (
            f'              <div class="theme-score-label">Theme fit</div>\n'
            f'              <div class="theme-score-value">{theme_fit} / 5</div>\n'
        )
    elif book_theme:
        theme_fit_block = (
            f'              <div class="theme-score-label">Theme</div>\n'
            f'              <div class="theme-score-value theme-score-value--text">{book_theme}</div>\n'
        )
    else:
        theme_fit_block = ""

    avg_rating = book.get("avg_rating")
    avg_rating_pill = (
        f'                <span class="meta-pill">Avg rating: {avg_rating}</span>\n'
        if avg_rating else
        f'                <span class="meta-pill">Avg rating: N/A</span>\n'
    )

    replacements = {
        "__SELECTED_CLASS__": " selected" if is_winner else "",
        "__PICK_LABEL__": f'          <div class="pick-label">{winner_label(month_label)}</div>\n' if is_winner else "",
        "__TYPE__": book["type"],
        "__TITLE__": book["title"],
        "__AUTHOR__": book["author"],
        "__PAGES__": book["pages"],
        "__DEBUT_LABEL__": book["debut_label"],
        "__AVG_RATING_PILL__": avg_rating_pill,
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


def find_winner_title(books: list) -> str | None:
    for book in books:
        if book.get("is_winner"):
            return book["title"]
    return None


def month_winners_label(month: dict) -> str:
    novel_winner = find_winner_title(month["novels"])
    short_winner = find_winner_title(month.get("short_works", []))
    parts = []
    if novel_winner:
        parts.append(novel_winner)
    if short_winner:
        parts.append(short_winner)
    return " · ".join(parts) if parts else "Winner TBD"


def render_page(month: dict, page_url: str, favicon_href: str, nav_block: str = "") -> str:
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
        "__MONTH_NAV_BLOCK__": nav_block,
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def render_archive_index() -> str:
    template = (TEMPLATES / "archive_index.html").read_text()
    month_files = sorted(MONTHS_DIR.glob("*.json"), reverse=True)

    groups = []  # list of (year, [item_html, ...])
    current_year = None
    for path in month_files:
        month = json.loads(path.read_text())
        year = month["month_label"].split()[-1]
        if year != current_year:
            groups.append((year, []))
            current_year = year
        theme = month.get("theme")
        label = f'{month["month_label"]} — {theme}' if theme else month["month_label"]
        winners = month_winners_label(month)
        groups[-1][1].append(
            f'      <li><a href="{month["slug"]}.html">{label}</a>'
            f'<div class="winner">{winners}</div></li>'
        )

    sections = []
    for year, items in groups:
        sections.append(
            f'    <h2 class="year-heading">{year}</h2>\n'
            f'    <ul class="month-list">\n' + "\n".join(items) + "\n    </ul>\n"
        )

    replacements = {
        "__ARCHIVE_SECTIONS__": "\n".join(sections),
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

    all_slugs = sorted(p.stem for p in MONTHS_DIR.glob("*.json"))
    idx = all_slugs.index(month["slug"])
    prev_slug = all_slugs[idx - 1] if idx > 0 else None
    next_slug = all_slugs[idx + 1] if idx < len(all_slugs) - 1 else None

    def month_label_for(slug: str) -> str:
        return json.loads((MONTHS_DIR / f"{slug}.json").read_text())["month_label"]

    nav_links = []
    if prev_slug:
        nav_links.append(f'<a class="nav-prev" href="{prev_slug}.html">← {month_label_for(prev_slug)}</a>')
    else:
        nav_links.append('<span class="nav-prev nav-disabled">← Start of archive</span>')
    nav_links.append('<a class="nav-index" href="index.html">All months</a>')
    if next_slug:
        nav_links.append(f'<a class="nav-next" href="{next_slug}.html">{month_label_for(next_slug)} →</a>')
    else:
        nav_links.append('<span class="nav-next nav-disabled">Most recent →</span>')
    nav_block = (
        '    <nav class="month-nav">\n'
        f'      {nav_links[0]}\n'
        f'      {nav_links[1]}\n'
        f'      {nav_links[2]}\n'
        '    </nav>\n\n'
    )

    archive_page_path = ARCHIVE_DIR / f"{month['slug']}.html"
    archive_page_url = f"{BASE_URL}archive/{month['slug']}.html"
    archive_page_html = render_page(
        month, page_url=archive_page_url, favicon_href="../assets/favicon.svg", nav_block=nav_block
    )
    archive_page_html = archive_page_html.replace('href="archive/index.html"', 'href="index.html"')
    archive_page_path.write_text(archive_page_html)
    print(f"Wrote {archive_page_path}")

    archive_index_path = ARCHIVE_DIR / "index.html"
    archive_index_path.write_text(render_archive_index())
    print(f"Wrote {archive_index_path}")


if __name__ == "__main__":
    main()

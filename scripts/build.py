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
REQUIRED_MONTH_FIELDS = ["slug", "month_label", "subtitle", "novels"]
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


def render_page(month: dict, page_url: str, favicon_href: str, nav_block: str = "", nav_ctx: dict | None = None) -> str:
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
            f'            1–5 · Fit to the theme.\n'
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

    nav_ctx = nav_ctx or {"home": "index.html", "archive": "archive/index.html", "stats": "stats.html", "active": "home"}

    replacements = {
        "__PAGE_TITLE__": page_title,
        "__SUBTITLE__": month["subtitle"],
        "__THEME_CHIP_BLOCK__": theme_chip_block,
        "__THEME_FIT_LEGEND_BLOCK__": theme_fit_legend_block,
        "__MONTH_LABEL__": month["month_label"],
        "__NOVELS_SUBTITLE__": novels_subtitle,
        "__NOVEL_CARDS__": novel_cards,
        "__SHORT_WORKS_SECTION__": short_works_section,
        "__OG_DESCRIPTION__": og_description,
        "__BASE_URL__": BASE_URL,
        "__PAGE_URL__": page_url,
        "__FAVICON_HREF__": favicon_href,
        "__MONTH_NAV_BLOCK__": nav_block,
        "__NAV_HOME__": nav_ctx["home"],
        "__NAV_ARCHIVE__": nav_ctx["archive"],
        "__NAV_STATS__": nav_ctx["stats"],
        "__NAV_HOME_ACTIVE__": "active" if nav_ctx["active"] == "home" else "",
        "__NAV_ARCHIVE_ACTIVE__": "active" if nav_ctx["active"] == "archive" else "",
        "__NAV_STATS_ACTIVE__": "active" if nav_ctx["active"] == "stats" else "",
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


def _parse_pages(pages: str) -> int | None:
    import re
    if not pages:
        return None
    m = re.search(r"(\d[\d,]*)", pages)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def compute_stats() -> dict:
    from collections import defaultdict

    month_files = sorted(MONTHS_DIR.glob("*.json"))
    months = [json.loads(p.read_text()) for p in month_files]

    total_months = len(months)
    total_novel_noms = 0
    total_short_noms = 0
    title_appearances = defaultdict(int)
    title_ever_won = defaultdict(bool)
    origin_counts = defaultdict(int)
    cw_counts = defaultdict(int)
    author_counts = defaultdict(int)
    hab_titles = set()
    hab_appearances = 0
    page_counts = []  # (title, pages)
    total_winners = 0

    for month in months:
        for section, counter_attr in (("novels", "novel"), ("short_works", "short")):
            for book in month.get(section, []):
                if counter_attr == "novel":
                    total_novel_noms += 1
                else:
                    total_short_noms += 1
                title_appearances[book["title"]] += 1
                if book.get("is_winner"):
                    title_ever_won[book["title"]] = True
                    total_winners += 1
                origin_counts[book.get("origin", "N/A")] += 1
                cw_counts[book.get("cw_tier", "unknown")] += 1
                author_counts[book["author"]] += 1
                if book.get("is_hab"):
                    hab_titles.add(book["title"])
                    hab_appearances += 1
                pages = _parse_pages(book.get("pages", ""))
                if pages:
                    page_counts.append((book["title"], pages))

    total_nominations = total_novel_noms + total_short_noms

    # Most-nominated titles that never won (repeat nominees the club keeps
    # passing over).
    repeat_snubbed = sorted(
        (
            (title, count)
            for title, count in title_appearances.items()
            if count >= 2 and not title_ever_won[title]
        ),
        key=lambda t: (-t[1], t[0]),
    )

    top_origins = sorted(origin_counts.items(), key=lambda t: -t[1])[:8]
    top_authors = sorted(
        ((a, c) for a, c in author_counts.items() if c >= 2), key=lambda t: -t[1]
    )[:8]

    avg_pages = round(sum(p for _, p in page_counts) / len(page_counts)) if page_counts else None
    longest = max(page_counts, key=lambda t: t[1]) if page_counts else None
    shortest = min(page_counts, key=lambda t: t[1]) if page_counts else None

    return {
        "total_months": total_months,
        "total_nominations": total_nominations,
        "total_novel_noms": total_novel_noms,
        "total_short_noms": total_short_noms,
        "total_winners": total_winners,
        "hab_count": len(hab_titles),
        "hab_appearances": hab_appearances,
        "hab_titles": sorted(hab_titles),
        "repeat_snubbed": repeat_snubbed,
        "top_origins": top_origins,
        "top_authors": top_authors,
        "cw_counts": dict(cw_counts),
        "avg_pages": avg_pages,
        "longest": longest,
        "shortest": shortest,
    }


def render_stats_page() -> str:
    stats = compute_stats()
    template = (TEMPLATES / "stats.html").read_text()

    def stat_card(label: str, value) -> str:
        return (
            f'      <div class="stat-card">\n'
            f'        <div class="stat-value">{value}</div>\n'
            f'        <div class="stat-label">{label}</div>\n'
            f'      </div>\n'
        )

    top_cards = "".join([
        stat_card("Months run", stats["total_months"]),
        stat_card("Total nominations", stats["total_nominations"]),
        stat_card("Novels · Short works", f'{stats["total_novel_noms"]} · {stats["total_short_noms"]}'),
        stat_card("Winners crowned", stats["total_winners"]),
        stat_card("HAB books nominated", stats["hab_count"]),
        stat_card(
            "Avg. page count",
            f'{stats["avg_pages"]} pages' if stats["avg_pages"] else "N/A",
        ),
    ])

    if stats["repeat_snubbed"]:
        snubbed_rows = "\n".join(
            f'        <li><span class="rank-title">{title}</span>'
            f'<span class="rank-count">{count}× nominated, 0 wins</span></li>'
            for title, count in stats["repeat_snubbed"][:10]
        )
    else:
        snubbed_rows = '        <li class="empty">No repeat nominees yet — every book nominated more than once has won at least once.</li>'

    if stats["hab_titles"]:
        hab_rows = "\n".join(f'        <li>{t}</li>' for t in stats["hab_titles"])
    else:
        hab_rows = '        <li class="empty">None tagged yet.</li>'

    longest = stats["longest"]
    shortest = stats["shortest"]
    longest_label = f'{longest[0]} ({longest[1]} pages)' if longest else "N/A"
    shortest_label = f'{shortest[0]} ({shortest[1]} pages)' if shortest else "N/A"

    origin_labels = json.dumps([o for o, _ in stats["top_origins"]])
    origin_data = json.dumps([c for _, c in stats["top_origins"]])
    cw_order = ["mild", "moderate", "extreme"]
    cw_labels = json.dumps([c.capitalize() for c in cw_order])
    cw_data = json.dumps([stats["cw_counts"].get(c, 0) for c in cw_order])
    author_labels = json.dumps([a for a, _ in stats["top_authors"]])
    author_data = json.dumps([c for _, c in stats["top_authors"]])

    replacements = {
        "__TOP_STAT_CARDS__": top_cards,
        "__SNUBBED_ROWS__": snubbed_rows,
        "__HAB_ROWS__": hab_rows,
        "__HAB_COUNT__": str(stats["hab_count"]),
        "__LONGEST_BOOK__": longest_label,
        "__SHORTEST_BOOK__": shortest_label,
        "__ORIGIN_LABELS__": origin_labels,
        "__ORIGIN_DATA__": origin_data,
        "__CW_LABELS__": cw_labels,
        "__CW_DATA__": cw_data,
        "__AUTHOR_LABELS__": author_labels,
        "__AUTHOR_DATA__": author_data,
        "__BASE_URL__": BASE_URL,
        "__PAGE_URL__": f"{BASE_URL}stats.html",
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

    archive_nav_ctx = {"home": "../index.html", "archive": "index.html", "stats": "../stats.html", "active": "archive"}
    archive_page_path = ARCHIVE_DIR / f"{month['slug']}.html"
    archive_page_url = f"{BASE_URL}archive/{month['slug']}.html"
    archive_page_html = render_page(
        month, page_url=archive_page_url, favicon_href="../assets/favicon.svg",
        nav_block=nav_block, nav_ctx=archive_nav_ctx,
    )
    archive_page_path.write_text(archive_page_html)
    print(f"Wrote {archive_page_path}")

    archive_index_path = ARCHIVE_DIR / "index.html"
    archive_index_path.write_text(render_archive_index())
    print(f"Wrote {archive_index_path}")

    stats_path = REPO_ROOT / "stats.html"
    stats_path.write_text(render_stats_page())
    print(f"Wrote {stats_path}")


if __name__ == "__main__":
    main()

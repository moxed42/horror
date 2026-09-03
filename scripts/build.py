#!/usr/bin/env python3
"""Generate index.html and the archive from a month's JSON data file.

Usage:
    python scripts/build.py data/months/2026-08-body-horror.json
"""
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = REPO_ROOT / "templates"
MONTHS_DIR = REPO_ROOT / "data" / "months"
ARCHIVE_DIR = REPO_ROOT / "archive"
AUTHORS_PATH = REPO_ROOT / "data" / "authors.json"
POLLS_PATH = REPO_ROOT / "data" / "polls.json"
BASE_URL = "https://moxed42.github.io/horror/"


def load_polls() -> list:
    data = json.loads(POLLS_PATH.read_text())
    return data["polls"]


MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def month_label_for_ym(ym: str) -> str:
    y, m = ym.split("-")
    return f"{MONTH_NAMES[int(m) - 1]} {y}"


def _base_author_name(author: str) -> str:
    # "Carmen Maria Machado (2014)" -> "Carmen Maria Machado"
    import re
    return re.sub(r"\s*\([^)]*\)\s*$", "", author).strip()


def _pub_year(author: str) -> int | None:
    # "Mariana Enríquez (2019, tr. 2022)" -> 2019 (original publication year)
    import re
    m = re.search(r"\((\d{4})", author)
    return int(m.group(1)) if m else None


def _era_bucket(pub_year: int | None) -> str:
    if not pub_year:
        return "unknown"
    if pub_year < 1900:
        return "pre1900"
    if pub_year < 1950:
        return "1900s"
    if pub_year < 2000:
        return "1950s"
    if pub_year < 2020:
        return "2000s"
    return "2020s"


def _author_age_bucket(birth_year: int | None, pub_year: int | None) -> str:
    if not birth_year or not pub_year:
        return "unknown"
    age = pub_year - birth_year
    if age < 30:
        return "20s"
    if age < 40:
        return "30s"
    if age < 50:
        return "40s"
    if age < 60:
        return "50s"
    if age < 70:
        return "60s"
    return "70+"


def load_authors() -> dict:
    data = json.loads(AUTHORS_PATH.read_text())
    data.pop("_note", None)
    return data

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


def render_book_card(book: dict, month_label: str, assets_prefix: str = "assets/") -> str:
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

    hab_badge = (
        f' <span class="hab-badge" title="Homework Ass Book"><img src="{assets_prefix}hab-icon.png" alt="HAB">HAB</span>'
        if book.get("is_hab") else ""
    )

    replacements = {
        "__SELECTED_CLASS__": " selected" if is_winner else "",
        "__PICK_LABEL__": f'          <div class="pick-label">{winner_label(month_label)}</div>\n' if is_winner else "",
        "__HAB_BADGE__": hab_badge,
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
    assets_prefix = favicon_href.rsplit("/", 1)[0] + "/" if "/" in favicon_href else ""

    novel_cards = "\n".join(render_book_card(b, month["month_label"], assets_prefix) for b in month["novels"])
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
        short_work_cards = "\n".join(render_book_card(b, month["month_label"], assets_prefix) for b in short_works)
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

    nav_ctx = nav_ctx or {
        "home": "index.html", "archive": "archive/index.html", "stats": "stats.html",
        "polls": "polls.html", "active": "home",
    }

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
        "__NAV_POLLS__": nav_ctx["polls"],
        "__NAV_HOME_ACTIVE__": "active" if nav_ctx["active"] == "home" else "",
        "__NAV_ARCHIVE_ACTIVE__": "active" if nav_ctx["active"] == "archive" else "",
        "__NAV_STATS_ACTIVE__": "active" if nav_ctx["active"] == "stats" else "",
        "__NAV_POLLS_ACTIVE__": "active" if nav_ctx["active"] == "polls" else "",
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


def _aggregate_books(all_books: list, authors: dict) -> dict:
    """Aggregate origin/CW/author/age/diversity/page stats over a list of
    (kind, book) tuples. Called once for all nominations and once for
    winners only, so the stats page toggle can filter every section."""
    from collections import defaultdict

    origin_counts = defaultdict(int)
    cw_counts = defaultdict(int)
    author_counts = defaultdict(int)
    age_counts = defaultdict(int)
    era_counts = defaultdict(int)
    gender_counts = defaultdict(int)
    lgbtq_counts = defaultdict(int)
    bipoc_counts = defaultdict(int)
    pages_by_kind = {"novel": [], "short": []}

    for kind, book in all_books:
        origin_counts[book.get("origin", "N/A")] += 1
        cw_counts[book.get("cw_tier", "unknown")] += 1
        author_counts[_base_author_name(book["author"])] += 1
        info = authors.get(_base_author_name(book["author"]), {})
        pub_year = _pub_year(book["author"])
        age_counts[_author_age_bucket(info.get("birth_year"), pub_year)] += 1
        era_counts[_era_bucket(pub_year)] += 1
        gender_counts[info.get("gender", "unknown")] += 1
        lgbtq_counts[info.get("lgbtq", "unknown")] += 1
        bipoc_counts[info.get("bipoc", "unknown")] += 1
        pages = _parse_pages(book.get("pages", ""))
        if pages:
            pages_by_kind[kind].append((book["title"], pages))

    def page_stats(pages):
        if not pages:
            return {"avg": None, "longest": None, "shortest": None}
        return {
            "avg": round(sum(p for _, p in pages) / len(pages)),
            "longest": max(pages, key=lambda t: t[1]),
            "shortest": min(pages, key=lambda t: t[1]),
        }

    return {
        "top_origins": sorted(origin_counts.items(), key=lambda t: -t[1]),
        "top_authors": sorted(
            ((a, c) for a, c in author_counts.items() if c >= 2), key=lambda t: -t[1]
        )[:8],
        "cw_counts": dict(cw_counts),
        "age_counts": dict(age_counts),
        "era_counts": dict(era_counts),
        "gender_counts": dict(gender_counts),
        "lgbtq_counts": dict(lgbtq_counts),
        "bipoc_counts": dict(bipoc_counts),
        "novel_pages": page_stats(pages_by_kind["novel"]),
        "short_pages": page_stats(pages_by_kind["short"]),
    }


def compute_stats() -> dict:
    from collections import defaultdict

    month_files = sorted(MONTHS_DIR.glob("*.json"))
    months = [json.loads(p.read_text()) for p in month_files]
    authors = load_authors()

    total_months = len(months)
    title_appearances = defaultdict(int)
    title_ever_won = defaultdict(bool)
    hab_titles = set()

    by_type = {
        "novel": {"noms": 0, "winners": 0},
        "short": {"noms": 0, "winners": 0},
    }
    all_books = []
    winning_books = []

    for month in months:
        for section, kind in (("novels", "novel"), ("short_works", "short")):
            for book in month.get(section, []):
                bucket = by_type[kind]
                bucket["noms"] += 1
                title_appearances[book["title"]] += 1
                is_winner = bool(book.get("is_winner"))
                if is_winner:
                    title_ever_won[book["title"]] = True
                    bucket["winners"] += 1
                if book.get("is_hab"):
                    hab_titles.add(book["title"])
                all_books.append((kind, book))
                if is_winner:
                    winning_books.append((kind, book))

    total_nominations = by_type["novel"]["noms"] + by_type["short"]["noms"]
    total_winners = by_type["novel"]["winners"] + by_type["short"]["winners"]

    # Titles nominated more than once, with whether they ever won.
    repeat_nominees = sorted(
        (
            (title, count, title_ever_won[title])
            for title, count in title_appearances.items()
            if count >= 2
        ),
        key=lambda t: (-t[1], t[0]),
    )

    return {
        "total_months": total_months,
        "total_nominations": total_nominations,
        "total_winners": total_winners,
        "hab_count": len(hab_titles),
        "hab_titles": sorted(hab_titles),
        "repeat_nominees": repeat_nominees,
        "novel_noms": by_type["novel"]["noms"],
        "short_noms": by_type["short"]["noms"],
        "noms": _aggregate_books(all_books, authors),
        "wins": _aggregate_books(winning_books, authors),
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

    def bar_list(pairs, max_items=8):
        pairs = pairs[:max_items]
        if not pairs:
            return '        <li class="empty">No data yet.</li>'
        top = max(c for _, c in pairs) or 1
        rows = []
        for label, count in pairs:
            pct = round(count / top * 100)
            rows.append(
                f'        <li class="bar-row">\n'
                f'          <span class="bar-label">{label}</span>\n'
                f'          <span class="bar-track"><span class="bar-fill" style="width:{pct}%"></span></span>\n'
                f'          <span class="bar-count">{count}</span>\n'
                f'        </li>'
            )
        return "\n".join(rows)

    def origin_bar_list(pairs, top_n=5):
        if not pairs:
            return bar_list(pairs)
        total = sum(c for _, c in pairs)
        head = pairs[:top_n]
        tail = pairs[top_n:]
        if tail:
            tail_count = sum(c for _, c in tail)
            head = head + [(f"Other ({len(tail)} countries)", tail_count)]
        return bar_list(head, max_items=len(head))

    def diversity_rows(counts: dict, order: list, labels: dict) -> str:
        pairs = [(labels[k], counts.get(k, 0)) for k in order]
        return bar_list(pairs, max_items=len(order))

    palette = ["#f54545", "#4a9dff", "#9b6bff", "#5a6178"]

    def stacked_bar(counts: dict, order: list, labels: dict) -> str:
        pairs = [(labels[k], counts.get(k, 0)) for k in order]
        total = sum(c for _, c in pairs) or 1
        segments = []
        legend = []
        for i, (label, count) in enumerate(pairs):
            color = "#3a3f52" if label == "Unknown" else palette[i % len(palette)]
            pct = round(count / total * 100)
            if count > 0:
                segments.append(f'<span class="stack-seg" style="width:{pct}%;background:{color}"></span>')
            legend.append(
                f'        <li><span class="stack-dot" style="background:{color}"></span>'
                f'{label} <span class="stack-count">{count} ({pct}%)</span></li>'
            )
        segments_html = "".join(segments) if segments else '<span class="stack-seg" style="width:100%;background:#3a3f52"></span>'
        legend_html = "\n".join(legend) if legend else '        <li class="empty">No data yet.</li>'
        return (
            f'          <div class="stack-bar">{segments_html}</div>\n'
            f'          <ul class="stack-legend">\n{legend_html}\n          </ul>'
        )

    def page_fact(bucket, key):
        entry = bucket[key]
        return f'{entry[0]} ({entry[1]} pages)' if entry else "N/A"

    def record_table(bucket) -> str:
        return (
            '<table class="record-table">'
            f'<tr><td>Longest</td><td>{page_fact(bucket, "longest")}</td></tr>'
            f'<tr><td>Shortest</td><td>{page_fact(bucket, "shortest")}</td></tr>'
            '</table>'
        )

    cw_order = ["mild", "moderate", "extreme"]
    age_order = ["20s", "30s", "40s", "50s", "60s", "70+", "unknown"]
    age_labels = {
        "20s": "20s", "30s": "30s", "40s": "40s", "50s": "50s",
        "60s": "60s", "70+": "70+", "unknown": "Unknown",
    }
    gender_order = ["woman", "man", "nonbinary", "unknown"]
    gender_labels = {"woman": "Female", "man": "Male", "nonbinary": "Nonbinary", "unknown": "Unknown"}
    lgbtq_order = ["yes", "no", "unknown"]
    lgbtq_labels = {"yes": "LGBTQIA+", "no": "Straight", "unknown": "Unknown"}
    bipoc_order = ["yes", "no", "unknown"]
    bipoc_labels = {"yes": "BIPOC", "no": "Not BIPOC", "unknown": "Unknown"}
    era_order = ["pre1900", "1900s", "1950s", "2000s", "2020s", "unknown"]
    era_labels = {
        "pre1900": "Pre-1900", "1900s": "1900–1949", "1950s": "1950–1999",
        "2000s": "2000–2019", "2020s": "2020s", "unknown": "Unknown",
    }

    cw_labels = {"mild": "Mild", "moderate": "Heavy", "extreme": "Extreme"}

    def sections_for(agg: dict) -> dict:
        return {
            "origin_rows": origin_bar_list(agg["top_origins"]),
            "cw_rows": stacked_bar(agg["cw_counts"], cw_order, cw_labels),
            "author_rows": bar_list(agg["top_authors"]),
            "age_rows": stacked_bar(agg["age_counts"], age_order, age_labels),
            "era_rows": stacked_bar(agg["era_counts"], era_order, era_labels),
            "gender_rows": stacked_bar(agg["gender_counts"], gender_order, gender_labels),
            "lgbtq_rows": stacked_bar(agg["lgbtq_counts"], lgbtq_order, lgbtq_labels),
            "bipoc_rows": stacked_bar(agg["bipoc_counts"], bipoc_order, bipoc_labels),
            "avg_novel_pages": f'{agg["novel_pages"]["avg"]} pages' if agg["novel_pages"]["avg"] else "N/A",
            "avg_short_pages": f'{agg["short_pages"]["avg"]} pages' if agg["short_pages"]["avg"] else "N/A",
            "novel_record_table": record_table(agg["novel_pages"]),
            "short_record_table": record_table(agg["short_pages"]),
        }

    noms = sections_for(stats["noms"])
    wins = sections_for(stats["wins"])

    top_cards = "".join([
        stat_card("Months run", stats["total_months"]),
        stat_card("Total nominations", stats["total_nominations"]),
        stat_card("HAB books nominated", stats["hab_count"]),
    ])

    polls = load_polls()
    poll_anchor_by_title = {}
    for p in polls:
        anchor = f'{p["archive_month"]}-{p["poll_type"]}'
        for o in p["options"]:
            poll_anchor_by_title.setdefault(o["canonical_title"], anchor)

    if stats["repeat_nominees"]:
        top_count = max(count for _, count, _ in stats["repeat_nominees"][:10])
        rows = []
        for title, count, won in stats["repeat_nominees"][:10]:
            anchor = poll_anchor_by_title.get(title)
            title_html = f'<a href="polls.html#{anchor}">{title}</a>' if anchor else title
            won_tag = ' <span class="won-tag">Won</span>' if won else ""
            pct = round(count / top_count * 100) if top_count else 0
            rows.append(
                f'        <li class="bar-row">\n'
                f'          <span class="bar-label">{title_html}{won_tag}</span>\n'
                f'          <span class="bar-track"><span class="bar-fill" style="width:{pct}%"></span></span>\n'
                f'          <span class="bar-count">{count}×</span>\n'
                f'        </li>'
            )
        snubbed_rows = "\n".join(rows)
    else:
        snubbed_rows = '        <li class="empty">No repeat nominees yet.</li>'

    if stats["hab_titles"]:
        hab_rows = "\n".join(f'        <li>{t}</li>' for t in stats["hab_titles"])
    else:
        hab_rows = '        <li class="empty">None tagged yet.</li>'

    replacements = {
        "__TOP_STAT_CARDS__": top_cards,
        "__NOVEL_NOMS__": str(stats["novel_noms"]),
        "__SHORT_NOMS__": str(stats["short_noms"]),
        "__SNUBBED_ROWS__": snubbed_rows,
        "__HAB_ROWS__": hab_rows,
        "__HAB_COUNT__": str(stats["hab_count"]),
        "__LAST_UPDATED__": f'{date.today():%B} {date.today().day}, {date.today():%Y}',
        "__BASE_URL__": BASE_URL,
        "__PAGE_URL__": f"{BASE_URL}stats.html",
    }
    for key, value in noms.items():
        replacements[f"__{key.upper()}_NOMS__"] = value
    for key, value in wins.items():
        replacements[f"__{key.upper()}_WINS__"] = value

    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def compute_poll_stats(polls: list) -> dict:
    countable = [p for p in polls if p["data_quality"] != "partial"]

    total_polls = len(polls)
    total_votes_cast = sum(p["total_option_votes"] for p in countable)
    avg_voters = round(sum(p["unique_voters"] for p in countable) / len(countable), 1) if countable else None
    avg_votes_per_person = (
        round(sum(p["average_votes_per_person"] for p in countable) / len(countable), 1) if countable else None
    )

    closest = None
    landslide = None
    for p in countable:
        sorted_opts = sorted(p["options"], key=lambda o: -o["votes"])
        if len(sorted_opts) < 2:
            continue
        gap = sorted_opts[0]["votes"] - sorted_opts[1]["votes"]
        entry = {
            "month": p["archive_month"],
            "poll_type": p["poll_type"],
            "top": sorted_opts[0],
            "runner_up": sorted_opts[1],
            "gap": gap,
        }
        if closest is None or gap < closest["gap"]:
            closest = entry
        if landslide is None or gap > landslide["gap"]:
            landslide = entry

    return {
        "total_polls": total_polls,
        "total_votes_cast": total_votes_cast,
        "avg_voters": avg_voters,
        "avg_votes_per_person": avg_votes_per_person,
        "closest": closest,
        "landslide": landslide,
    }


def render_polls_page() -> str:
    polls = load_polls()
    stats = compute_poll_stats(polls)
    template = (TEMPLATES / "polls.html").read_text()

    def stat_card(label: str, value) -> str:
        return (
            f'      <div class="stat-card">\n'
            f'        <div class="stat-value">{value}</div>\n'
            f'        <div class="stat-label">{label}</div>\n'
            f'      </div>\n'
        )

    top_cards = "".join([
        stat_card("Polls held", stats["total_polls"]),
        stat_card("Total votes cast", stats["total_votes_cast"]),
        stat_card("Avg. unique voters", stats["avg_voters"] if stats["avg_voters"] else "N/A"),
        stat_card("Avg. votes/person", stats["avg_votes_per_person"] if stats["avg_votes_per_person"] else "N/A"),
    ])

    def turnout_trend(polls: list) -> str:
        # One point per month: average unique voters across that month's poll(s).
        by_month = {}
        for p in polls:
            if p["data_quality"] == "partial":
                continue
            by_month.setdefault(p["archive_month"], []).append(p["unique_voters"])
        months = sorted(by_month.keys())
        if not months:
            return '<p class="empty">No turnout data yet.</p>'
        points = [(m, round(sum(v) / len(v), 1)) for m, v in by_month.items()]
        points.sort()
        top = max(v for _, v in points) or 1
        bars = []
        for month, avg_voters in points:
            height_pct = round(avg_voters / top * 100)
            label = month_label_for_ym(month)
            bars.append(
                f'<div class="trend-bar" title="{label}: {avg_voters} avg voters">'
                f'<span class="trend-bar-fill" style="height:{height_pct}%"></span></div>'
            )
        axis = (
            '<div class="trend-axis">'
            f'<span>{top}</span><span>{round(top / 2)}</span><span>0</span>'
            '</div>'
        )
        return (
            '<div class="trend-chart-row">' + axis +
            '<div class="trend-chart">' + "".join(bars) + '</div></div>'
            f'<div class="trend-caption">{month_label_for_ym(points[0][0])} → {month_label_for_ym(points[-1][0])} '
            '· avg unique voters per month · hover a bar for exact value</div>'
        )

    turnout_chart = turnout_trend(polls)

    def race_card(entry, kind_label):
        if not entry:
            return f'<div class="fact"><div class="fact-label">{kind_label}</div>N/A</div>'
        month_label = month_label_for_ym(entry["month"])
        type_label = "Novel poll" if entry["poll_type"] == "book" else "Short story poll"
        return (
            f'<div class="fact"><div class="fact-label">{kind_label}</div>'
            f'{month_label} ({type_label}): '
            f'{entry["top"]["canonical_title"]} ({entry["top"]["votes"]} votes) vs. '
            f'{entry["runner_up"]["canonical_title"]} ({entry["runner_up"]["votes"]} votes) '
            f'— {entry["gap"]}-vote gap</div>'
        )

    race_cards = race_card(stats["closest"], "Closest race") + race_card(stats["landslide"], "Biggest landslide")

    def poll_bar_list(poll):
        options = sorted(poll["options"], key=lambda o: -o["percentage"])
        is_partial = poll["data_quality"] == "partial"
        top = max((o["percentage"] for o in options), default=1) or 1
        rows = []
        for o in options:
            pct_width = round(o["percentage"] / top * 100)
            count_label = f'{o["percentage"]}%' if is_partial else f'{o["votes"]} · {o["percentage"]}%'
            winner_mark = ' <img src="assets/favicon.svg" alt="Winner" class="poll-winner-tag" title="Winner">' if o["is_winner"] else ""
            row_class = "bar-row poll-bar-row is-winner" if o["is_winner"] else "bar-row poll-bar-row"
            author = o["canonical_author"]
            rows.append(
                f'        <li class="{row_class}">\n'
                f'          <span class="bar-label">'
                f'<span class="poll-title-text" title="{o["canonical_title"]} — {author}">{o["canonical_title"]}</span>'
                f'{winner_mark}<span class="poll-author" title="{author}"> — {author}</span></span>\n'
                f'          <span class="bar-track"><span class="bar-fill" style="width:{pct_width}%"></span></span>\n'
                f'          <span class="bar-count">{count_label}</span>\n'
                f'        </li>'
            )
        return "\n".join(rows)

    def poll_column(p, type_label):
        turnout = (
            f'{p["unique_voters"]} voters · {p["total_option_votes"]} votes cast'
            if p["data_quality"] != "partial" else "Turnout not recorded"
        )
        anchor = f'{p["archive_month"]}-{p["poll_type"]}'
        return (
            f'        <div class="poll-column" id="{anchor}">\n'
            f'          <div class="poll-column-header">\n'
            f'            <span class="poll-type-tag">{type_label}</span>\n'
            f'            <span class="poll-turnout">{turnout}</span>\n'
            f'          </div>\n'
            f'          <ul class="bar-list">\n{poll_bar_list(p)}\n          </ul>\n'
            f'        </div>\n'
        )

    # Map "YYYY-MM" -> archive slug so poll cards can link to that month's page.
    slug_by_month = {}
    for path in MONTHS_DIR.glob("*.json"):
        slug_by_month[path.stem[:7]] = json.loads(path.read_text())["slug"]

    # Group by month (novel + short story side by side), then by year.
    by_month = {}
    for p in polls:
        by_month.setdefault(p["archive_month"], {})[p["poll_type"]] = p

    months_sorted = sorted(by_month.keys(), reverse=True)
    groups = []
    current_year = None
    month_links = []
    for month in months_sorted:
        year = month.split("-")[0]
        if year != current_year:
            groups.append((year, []))
            current_year = year
        month_label = month_label_for_ym(month)
        entry = by_month[month]
        columns = []
        if "book" in entry:
            columns.append(poll_column(entry["book"], "Novel poll"))
        if "short_story" in entry:
            columns.append(poll_column(entry["short_story"], "Short story poll"))
        slug = slug_by_month.get(month)
        month_heading = (
            f'<a class="poll-month-link" href="archive/{slug}.html">{month_label} →</a>' if slug else month_label
        )
        groups[-1][1].append(
            f'      <div class="poll-card" id="{month}">\n'
            f'        <div class="poll-month">{month_heading}</div>\n'
            f'        <div class="poll-columns">\n{"".join(columns)}        </div>\n'
            f'      </div>\n'
        )
        y, m = month.split("-")
        month_abbr = f"{MONTH_NAMES[int(m) - 1][:3]} '{y[2:]}"
        month_links.append(f'<a href="#{month}">{month_abbr}</a>')

    sections = []
    year_links = []
    for year, cards in groups:
        sections.append(f'    <h2 class="year-heading" id="year-{year}">{year}</h2>\n' + "".join(cards))
        year_links.append(f'<a href="#year-{year}">{year}</a>')

    replacements = {
        "__POLL_TOP_CARDS__": top_cards,
        "__POLL_TURNOUT_CHART__": turnout_chart,
        "__POLL_RACE_CARDS__": race_cards,
        "__POLL_SECTIONS__": "\n".join(sections),
        "__POLL_YEAR_LINKS__": "\n      ".join(year_links),
        "__POLL_MONTH_LINKS__": "\n      ".join(month_links),
        "__LAST_UPDATED__": f'{date.today():%B} {date.today().day}, {date.today():%Y}',
        "__BASE_URL__": BASE_URL,
        "__PAGE_URL__": f"{BASE_URL}polls.html",
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

    archive_nav_ctx = {
        "home": "../index.html", "archive": "index.html", "stats": "../stats.html",
        "polls": "../polls.html", "active": "archive",
    }
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

    polls_path = REPO_ROOT / "polls.html"
    polls_path.write_text(render_polls_page())
    print(f"Wrote {polls_path}")


if __name__ == "__main__":
    main()

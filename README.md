# horror
Book Club Monthly Picks

Final Girls Book Club website. `index.html` (repo root) is the current month's
picks, served by GitHub Pages from this branch's default. Past months live
under `archive/`.

## How the site is built

- `templates/page.html` and `templates/book_card.html` hold the shared HTML/CSS
  structure. Don't hand-edit `index.html` directly — it's generated.
- `data/months/YYYY-MM-slug.json` holds one month's theme, blurb, and book list
  (novels + short works).
- `scripts/build.py` renders a month's JSON into `index.html` (current month),
  an archive snapshot at `archive/YYYY-MM-slug.html`, and a regenerated
  `archive/index.html` listing every month found in `data/months/`.

## Updating for a new month

1. Create `data/months/YYYY-MM-slug.json` (copy an existing file as a
   starting point). Fill in `theme`, `month_label`, `subtitle`,
   `vote_instructions`, and the `novels`/`short_works` arrays. Each book needs:
   `type`, `title`, `author`, `pages`, `debut_label`, `avg_rating`,
   `theme_fit` (1-5), `cw_tier` (`mild`/`moderate`/`extreme`), `cw_label`
   (`Mild`/`Heavy`/`Extreme`), `vibe`, `summary`, `warnings`.
2. Run:
   ```
   python3 scripts/build.py data/months/YYYY-MM-slug.json
   ```
3. Review the diff on `index.html` and the new `archive/` files, then commit
   and push. GitHub Pages picks up `index.html` automatically; no build step
   needed at deploy time.

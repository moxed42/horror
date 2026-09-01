# horror
Book Club Monthly Picks

Final Girls Book Club website. `index.html` (repo root) is the current month's
picks, served by GitHub Pages from this branch's default. Past months live
under `archive/`.

Live site: [bit.ly/chooseyourscare](https://bit.ly/chooseyourscare)

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
   (`Mild`/`Heavy`/`Extreme`), `vibe`, `summary`, `origin` (country the book
   is originally from/written in), `warnings`. Set
   `is_winner: false` on every book at first (voting hasn't happened yet).
2. Run:
   ```
   python3 scripts/build.py data/months/YYYY-MM-slug.json
   ```
3. Review the diff on `index.html` and the new `archive/` files, then commit
   and push. GitHub Pages picks up `index.html` automatically; no build step
   needed at deploy time.

## Favicon and link-preview image (Discord etc.)

- `assets/favicon.svg` is the browser-tab icon — a small skull, doesn't need
  to change monthly.
- `assets/social-card.png` is the image Discord/Slack/etc. show when the
  site link is pasted (1200x630, generated once via headless Chromium from
  `assets/social-card-source.html`). The page's `<meta property="og:*">` /
  `twitter:*` tags in `templates/page.html` point at it and pick up the
  current month's title/description automatically via `build.py` — no
  changes needed there month to month.
- To give the tagline in the image itself a fresh line each month (e.g. in
  the theme's language), regenerate it:
  ```
  python3 scripts/gen_social_card.py "your tagline here"
  ```
  Requires a headless Chromium/Chrome binary; set `CHROME_PATH` if one
  isn't found automatically. This is optional — skip it and the image just
  keeps its current tagline.

## Marking the winner (once voting closes)

Once you know which novel and short story won, flip `is_winner` to `true`
on those two book entries in that month's `data/months/*.json` file, then
re-run `python3 scripts/build.py data/months/YYYY-MM-slug.json`. The winning
cards get a highlighted border and a "<Month>'s Winner" label — same pattern
as previous months.

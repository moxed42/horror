---
name: fgbc-monthly-update
description: Generate the monthly Final Girls Book Club picks — research a list of horror books/short stories the user gives you (title, author, approx page count, trigger warnings, vibe, spoiler-free summary, theme fit) and either output Discord-ready markdown blocks, update the book club website (data/months JSON + regenerated index.html/archive), or both. Also handles the follow-up a day or two later once poll voting closes: marking which novel and short story won on the already-published site. Use this whenever the user gives a new month's theme and book/short-story list for the book club, asks to "do this month's picks," pastes a reading list or poll results for FGBC, says which book/short story "won" this month, or asks to update the Final Girls Book Club site or Discord post — even if they don't say "skill" or name this file.
---

# FGBC monthly update

Turns a raw list of horror titles for the month into finished book-club
content: research + write-ups, and (optionally) a website update.

## Step 0: get the book list and the output the user wants

The user gets each month's titles from two polls (novels and short
stories), run on quiz-maker.com. Those poll URLs are **not fetchable** in
this environment (network egress to that domain is blocked) — don't try
WebFetch on a quiz-maker.com link, it will fail. Instead, ask the user to
paste the poll page's text directly, e.g.:

```
SHORT STORY PICK
Jacqueline Ess: Her Will and Testament by Clive Barker
Spar by Kij Johnson
Skeleton! by Ray Bradbury
My Husband Has Taken Our Roleplaying Too Far by Christian Wallis

Which book are you interested in?
The Cipher by Kathe Koja
The Troop by Nick Cutter
You Weren't Meant to Be Human by Andrew Joseph White
The Ruins by Scott Smith
```

Treat every title listed as a pasted poll's options as a pick to write up
— the site has historically listed all poll candidates (novels and short
works both), not just a single winner, unless the user says otherwise
(e.g. "winner: The Cipher" — if they call out a winner, still write up all
of them unless they say to include only the winner).

If not already clear from their message, also ask: Discord blocks, website
update, or both. And confirm the month's **theme** and **month label**
(e.g. "September 2026") if not given.

## Step 1: research each title

For every book or short story given, look up (don't guess):
- Author, original publication year
- Approximate page count
- Genre / subgenre fit
- Country the work is originally from / originally written in (`origin`)
- Real content/trigger warnings (violence, sexual content, self-harm, etc.)

Cross-check facts where you can (e.g. publisher pages, Goodreads-style
aggregators, reviews) rather than relying on a single source or memory.
If you can't verify something — especially a numeric rating — say so
explicitly instead of inventing a plausible-looking number. It's fine to
write "no reliable public rating found — estimate: ~4.0★" rather than a
bare number that looks sourced but isn't.

For each title, also produce:
- **Vibe**: one sentence capturing tone/feel.
- **Summary**: 2–4 sentences, spoiler-free, premise + vibe.
- **theme_fit**: 1–5, how intensely the pick leans into the month's theme.
  Briefly note your reasoning to the user (e.g. "5/5 — body horror is the
  entire premise") so they can sanity-check it, but keep the score itself
  a bare integer for output.
- **cw_tier** / **cw_label**: `mild`/`Mild`, `moderate`/`Heavy`, or
  `extreme`/`Extreme`, based on how intense the warnings are overall.

## Step 2a: Discord output

For each book, output a separate fenced `md` code block, under 2000
characters, in this exact format:

```md
**Title by Author**
- *Page count*: ~XXX pages
- *Content warnings*: warning 1, warning 2, warning 3.
- *Vibe*: 1-sentence description of tone and feel.
- *Summary*: 2–4 sentence, spoiler-free description of the premise and vibe.
```

If the user says "shorten the summaries," cut Summary to 1–2 sentences,
same structure otherwise. Keep tone concise and neutral — no links or
citations in the output, just the formatted block.

## Step 2b: website update

The site is generated from JSON, not hand-edited — see `README.md` and
`scripts/build.py` in this repo for how the pipeline works. Read
`data/months/2026-08-body-horror.json` first as the reference example;
it shows every field the schema needs (`slug`, `theme`, `month_label`,
`subtitle`, `vote_instructions`, and per-book `type`, `title`, `author`,
`pages`, `debut_label`, `avg_rating`, `theme_fit`, `cw_tier`, `cw_label`,
`vibe`, `summary`, `origin`, `warnings`, `is_winner`). Match its structure exactly —
the build script validates required fields and will fail loudly if one is
missing, which is intentional (better than silently rendering a blank).

1. Pick a filename `data/months/YYYY-MM-slug.json` — `YYYY-MM` from the
   month label, `slug` a short dash-cased version of the theme (e.g.
   September 2026 + "Final Girls" → `2026-09-final-girls.json`).
2. Write the file with the researched data from Step 1. Separate novels
   into `novels` and shorter pieces (short stories/novellas) into
   `short_works`, matching how the reference file does it. Set
   `is_winner: false` on every book — voting hasn't happened yet at this
   point (see Step 3 for the follow-up).
3. Run `python3 scripts/build.py data/months/YYYY-MM-slug.json`. This
   regenerates root `index.html`, adds an `archive/YYYY-MM-slug.html`
   snapshot, and refreshes `archive/index.html`.
3b. Optional: the Discord/link-preview image (`assets/social-card.png`)
   has a tagline baked in. If it's worth freshening for this month's theme
   (e.g. translated into the theme's language, as done for Foreign Horror
   — "Terror mensual que muerde de vuelta"), offer to run
   `python3 scripts/gen_social_card.py "new tagline"` and mention it; skip
   it by default otherwise, since it needs a headless Chromium binary and
   isn't required for the site to work.
4. Show the user `git diff --stat` and the diff on `index.html`/the new
   files so they can see exactly what changed before anything is
   committed.
5. Only run `git add`/`git commit`/`git push` if the user confirms —
   don't push automatically. This mirrors the site's git-push guidance:
   pushing is a visible, hard-to-reverse action that the user should
   sign off on, especially for a public site.

## Step 3: marking the winner (the follow-up, once voting closes)

Poll results usually aren't known until a day or so after the month's
picks are published — this is a separate, later step, not part of the
same conversation. When the user comes back and says which novel and
which short story won:

1. Open that month's `data/months/YYYY-MM-slug.json` (the one already
   published — if unsure which file, check `archive/index.html`'s list or
   ask).
2. Set `is_winner: true` on the winning novel entry and the winning
   short-work entry. Leave every other book's `is_winner` as `false`.
3. Re-run `python3 scripts/build.py data/months/YYYY-MM-slug.json`. The
   winner's card gets a highlighted border and a "<Month>'s Winner" label
   automatically — this mirrors how past months (see git history, e.g.
   "Highlight selected book cards with styles") marked winners by hand;
   the build script now does it from the `is_winner` flag instead.
4. Same review-before-push rule as Step 2b: show the diff, only commit
   and push once the user confirms.

## Notes

- Never fabricate a rating, page count, or warning as if it were sourced
  when it isn't — flag estimates plainly. This book club uses content
  warnings to help people opt out of things that would hurt them; a wrong
  or fabricated warning is worse than an honest "couldn't verify."
- Keep Discord output free of links/citations per the original workflow —
  those belong in your research process, not the final pasted text.

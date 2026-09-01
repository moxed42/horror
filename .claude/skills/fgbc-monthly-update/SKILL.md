---
name: fgbc-monthly-update
description: Generate the monthly Final Girls Book Club picks — research a list of horror books/short stories the user gives you (title, author, approx page count, trigger warnings, vibe, spoiler-free summary, theme fit) and either output Discord-ready markdown blocks, update the book club website (data/months JSON + regenerated index.html/archive), or both. Use this whenever the user gives a new month's theme and book/short-story list for the book club, asks to "do this month's picks," pastes a reading list for FGBC, or asks to update the Final Girls Book Club site or Discord post — even if they don't say "skill" or name this file.
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
`vibe`, `summary`, `warnings`). Match its structure exactly — the build
script validates required fields and will fail loudly if one is missing,
which is intentional (better than silently rendering a blank).

1. Pick a filename `data/months/YYYY-MM-slug.json` — `YYYY-MM` from the
   month label, `slug` a short dash-cased version of the theme (e.g.
   September 2026 + "Final Girls" → `2026-09-final-girls.json`).
2. Write the file with the researched data from Step 1. Separate novels
   into `novels` and shorter pieces (short stories/novellas) into
   `short_works`, matching how the reference file does it.
3. Run `python3 scripts/build.py data/months/YYYY-MM-slug.json`. This
   regenerates root `index.html`, adds an `archive/YYYY-MM-slug.html`
   snapshot, and refreshes `archive/index.html`.
4. Show the user `git diff --stat` and the diff on `index.html`/the new
   files so they can see exactly what changed before anything is
   committed.
5. Only run `git add`/`git commit`/`git push` if the user confirms —
   don't push automatically. This mirrors the site's git-push guidance:
   pushing is a visible, hard-to-reverse action that the user should
   sign off on, especially for a public site.

## Notes

- Never fabricate a rating, page count, or warning as if it were sourced
  when it isn't — flag estimates plainly. This book club uses content
  warnings to help people opt out of things that would hurt them; a wrong
  or fabricated warning is worse than an honest "couldn't verify."
- Keep Discord output free of links/citations per the original workflow —
  those belong in your research process, not the final pasted text.

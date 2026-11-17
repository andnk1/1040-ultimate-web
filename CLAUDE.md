# 1040 Ultimate (browser app) — read first

Read and follow these before any work:
@BUILD_NOTES.md
@README.md
@APPS_ARCHITECTURE.md

When we make a decision or finish a change, add it to BUILD_NOTES.md (short, plain language) before ending.
Treat a brief as my intent, not a script: if something doesn't fit the code or there's a better way, say so before building.

## Rules (Lady, 2026-11-17)
- **One version only: the browser app** (this folder, GitHub `1040-ultimate-web`). The desktop app (local Python / Flask
  server) is retired: never rebuild or update it. Its last code is the archive — git tag `python-final` in the old repository
  `1040_ultimate` (C:\dev\1040_ultimate). Read it for reference only; never commit or push there.
- **Client documents are read in the browser and never uploaded** to any server. The local server (`web\serve.py`) only hands
  out the program's own files; it has no upload address. Later hosting (Cloudflare) serves files only.
- **No API key in the web files.** The AI tab will use a Cloudflare Worker or a key each user enters — ask Lady before
  building either.
- **UT Data Entry stays a separate app** on Lady's computer. This app only produces the export file. Its format is
  `design\ut_export_format.md`; `tests\test_ut_export_format.py` checks the export matches it. Change both together.
- **Opening source documents:** PDFs open in a Chrome tab; other files use Google Drive links.
- **Keep the Python logic readable** — Lady studies it to learn how the app works. Plain explanations in comments for
  anything non-obvious (what a rule is for, why a number is what it is). Short functions with names that say what they do.
- **Same results as the archive:** a page converted from the desktop app must give the same results as `python-final` on the
  sample clients before it counts as done (`design\conversion_plan.md` says how, page by page).

## Where things are
- BUILD_NOTES.md = current decisions, status and the pending list (short). If a question isn't answered there, look in
  BUILD_HISTORY.md (older, settled decisions — written for the desktop app: the rules stay, the desktop details don't).
- `design\web_version.md` = the brief for the browser app; `design\conversion_plan.md` = the page-by-page conversion plan.
- A screen with a spec in design\ (e.g. design\k1_prep.md) is built exactly as that spec says - how it works and how it
  looks. Read it before working on that screen. Small design details go in the screen's spec, not in BUILD_NOTES.md.

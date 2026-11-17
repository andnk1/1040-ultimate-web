# 1040 Ultimate — browser app (Pyodide) — plan and brief

Written in Cowork, 2026-11-16, after testing; updated 2026-11-17 when the desktop app was retired. Read with BUILD_NOTES.md
and APPS_ARCHITECTURE.md. This is my intent, not a script: if something doesn't fit the code or there's a better way, say so
before building. **Work step by step. At the end of each step stop, report, and wait for my "go".**

## Decision (2026-11-17): one version only — the browser app
- The desktop (local Python server) version of 1040 Ultimate is **retired**. All work happens on the browser app only, in
  `C:\dev\1040_ultimate_web` (GitHub `1040-ultimate-web`, private). Never rebuild or update the desktop app.
- The desktop app's last code is the **archive**: git tag `python-final` in the old repository `1040_ultimate` (commit of
  2026-11-16). Read it to see how a page worked; never commit or push there.
- **Client documents are read in the browser and never uploaded** to any server.
- **No API key in the web files.** The AI tab will use a Cloudflare Worker or a key each user enters — ask me before
  building either.
- **UT Data Entry stays a separate app** on my computer. This app only produces the export file; its format is
  `design\ut_export_format.md`, with a test (`tests\test_ut_export_format.py`) that checks the export matches it.
- **Opening source documents:** PDFs open in a Chrome tab; other files use Google Drive links.
- **Keep the Python logic readable** — I study it to learn how the app works. Plain explanations in comments for anything
  non-obvious.
- **Same results as the archive:** every converted page gives the same results as `python-final` on the sample clients
  (`design\conversion_plan.md`, page by page).

## Goal
1040 Ultimate inside the browser (Chrome / Edge), Python running in the tab with Pyodide, later hosted on the firm's
Cloudflare behind its two-factor login. Client documents never leave the computer: everything is read and calculated in the tab.

## Layout
```
core\      the engine — readers, rules, income summary, K-1, verify, Run check (core\runcheck.py)
web\       the app — the page (index.html), the worker (worker.js), the MuPDF.js stand-in, the local file server
templates\ static\   the pages and their scripts (Jinja2 draws the templates inside Pyodide)
tests\     the tests: the same engine on this computer's Python (PyMuPDF) + the answer-key check inside the browser
```
- Nothing Windows-only inside `core\` (file windows, subprocess, ctypes, opening files in their program).
- `tests\run_tests.bat` passes after every step; a converted page matches the archive on the sample clients.

## What was tested already (2026-11-11 … 16)
- Pyodide 314.0.7 runs the engine. Installed and working in the browser: pdfplumber 0.11.10 (pypdfium2 5.15.2 has an
  official browser wheel on PyPI), pdfminer.six, openpyxl, python-docx, Pillow, lxml, cryptography, Jinja2.
- **PyMuPDF has no browser version** → replaced by **MuPDF.js** (npm `mupdf`, same MuPDF engine, AGPL like PyMuPDF), behind
  the one PDF door `core\pdfengine.py` (`web\py\pymupdf_js.py` + `web\mupdf_bridge.mjs`).
- `tools\web_check\compare_pdf.bat` compares the PDF door on PyMuPDF and on MuPDF.js page by page (text, words, blocks,
  "dict" lines, filled shapes). On the two sample folders (35 PDFs): text, words, blocks, lines identical on every page.
- Speed: Run check on the Sample case (17 documents + a 179-page return) 75–153 s in the tab; pdfplumber is the slow part.
- Download for a first-time user ≈ 40 MB (Pyodide + libraries + MuPDF.js), then cached by the browser.

## Done
- **Phase 1 (2026-11-16)** — one PDF door; desktop-only code out of `core\`.
- **Phase 2 (2026-11-16)** — `run_web.bat` (local server, port 5070), the first page with the desktop's fields (prior-year
  return, summary, Add documents… / Add a folder…), Run check in a Web Worker, the Summary page read-only. The Sample case
  matches its answer key in the browser (0 differences). Run check moved to `core\runcheck.py` (shared with the tests).
- **The new app (2026-11-17)** — this folder made from the browser parts; desktop-only parts left out (the Flask server
  `app.py`, the K-1 / AI page servers, Windows file windows, the browser launcher, the PDF time limit, masking).

## Next — convert the pages, one at a time
`design\conversion_plan.md`: for each page, what changes, what desktop feature it loses and what replaces it, and how it is
proven to give the same results as the archive. Build only after my "go" on the plan.

## Later — firm version (only when I say)
Cloudflare Pages behind the firm's two-factor login, private preview address per change. The AI tab: a Cloudflare Worker that
holds the key, or a key each user enters — decided with me before it is built.

## Not in the browser app
Masking / redact_pdf (a separate app, as decided). UT Data Entry (a separate app; this app produces its export file).

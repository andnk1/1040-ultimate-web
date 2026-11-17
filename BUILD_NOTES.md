# 1040 Ultimate (browser app) — build notes (read this first)

Hand-off for a new Claude session: the working rules, what's decided but not built, the open questions and the pending list.
Finished, settled work is in **BUILD_HISTORY.md** (moved there unchanged, in date order — the "history:" names below are its
section titles — written for the desktop app: its rules stay, its desktop details don't); a screen with a spec is in
`design\` (e.g. `design\k1_prep.md`). Last updated 2026-11-17.

## One version only — the browser app (Lady, 2026-11-17)
- The desktop app (local Python / Flask server) is **retired**. All work happens on the browser app only: this folder,
  `C:\dev\1040_ultimate_web`, GitHub `1040-ultimate-web` (private). Never rebuild or update the desktop app.
- **Archive:** the desktop app's last code = git tag `python-final` (commit 8e7b150, pushed 2026-11-16) in the old
  repository `1040_ultimate` (`C:\dev\1040_ultimate`). Reference only — never commit or push there again (Lady marks it
  Archived on GitHub). Checked 2026-11-17: nothing Python-only was changed after that push; the later work (phase 1 commit,
  phase 2 files) is web work and lives here.
- **Client documents are read in the browser and never uploaded** to any server.
- **No API key in the web files.** The AI tab will use a Cloudflare Worker or a key each user enters — ask Lady first.
- **UT Data Entry stays a separate app** on Lady's computer; this app only produces the export file. Format:
  `design\ut_export_format.md`; `tests\test_ut_export_format.py` checks the export matches it (both change together).
- **Opening source documents:** PDFs open in a Chrome tab; other files use Google Drive links.
- **Keep the Python logic readable** — Lady studies it. Plain explanations in comments for anything non-obvious.
- **Same results as the archive:** a converted page matches `python-final` on the sample clients before it counts as done
  (`design\conversion_plan.md`).

## Working rules (from Lady)
- **List first, build on "go".** When Lady lists changes ("no changes yet", "keep a tab", "we may have more"), only add
  them to the numbered pending list below and confirm. Build only when she says go / implement / apply.
- **Client data stays local.** Never use unmasked documents; she removes them. Work only with masked (redacted) files.
  The app itself reads unmasked forms (all fields visible, 2026-11-01): parsers are built for full documents, not masked ones;
  its AI tab sends originals too (the firm's API agreement allows it, 2026-11-12). Masking is only for the Mask page's
  redacted copies (e.g. files shared in a Claude Code / Cowork session). Test with samples / public forms.
- **Masking (the separate masking app, not in this app):** always mask the firm EIN kept in `local_settings.json` (never put it in code or GitHub). First names stay
  visible; payer / employer names and amounts are never masked.
- **GitHub:** she removes PDFs herself before pushing; `.gitignore` excludes client data, WIP json, `.bak`, xlsx.
  Keep client names / numbers out of code, README and this file.
- **Don't modify** `k1_summary.py` (shared with PDF_Mask; `redact_pdf.py` stays in the archive / PDF_Mask).
- **Schedule C box:** don't change the design (P&L mapping beside it); no more businesses per page.
- **Style on screen:** whole dollars; negatives black (no red anywhere for negatives); numbers typed by the preparer
  blue, not bold; changed amounts light pink (design rules, 2026-11-01); verified (ticked) light mint; red only for real data-entry differences.
- **Verification is line by line** — never by totals or net amounts (UT doesn't calculate those on the input screens).
  Two sections: (1) document verification, (2) UltraTax entries with no document. Tolerance ±$1 per line.
- **Readers read only labelled IRS boxes** (box number + IRS box name), in table or list layout. A summary page
  without the IRS box names is not read.
- Replies: short, plain language; one question at a time.
- **Decisions go in this file.** When a decision is made or a change is finished, add it here (short, plain language) before
  ending the session. `CLAUDE.md` loads this file and README at the start of every Claude Code session.
- **Where to work:** undecided design (new screen, workflow, "which option?") is talked through in Cowork (project "1040_ultimate"),
  sometimes with a clickable test page in `_work/`; clear changes and all building go straight to Claude Code.
- **`_work` is temporary:** the program deletes it at every start (by design). Nothing meant to be kept goes there — Lady moves
  what she needs out of it by hand.

## How to work on it
- App folder on her computer: `C:\dev\1040_ultimate_web` (start with `run_web.bat`, http://127.0.0.1:5070 in Chrome / Edge).
  PDF_Mask: `C:\dev\PDF_Mask` (web app on port 5069, `run_web.bat`).
- Edit a copy in the cloud workspace, then write it back to her computer and confirm the copy on her computer is
  identical (byte compare). If the computer is offline, send a zip.
- Test before reporting: `tests\run_tests.bat` (the engine on this computer's Python, PyMuPDF as the PDF engine) and the
  page itself in Chrome (the Sample folder -> "Check against the answer key" runs the same check with MuPDF.js); no page errors.
  `tools\web_check\compare_pdf.bat "<folder>"` when the PDF stand-in changes.
- A browser refresh (Ctrl+F5) picks up every change (Python, templates, CSS, JS): the program is fetched again at each start.

## Test files (masked) — attach them to a new session
- UT input screens print, 110 pages (W2, B&D with a 3-section statement page, 11 Rent screens):
  the masked UT print in `C:\dev\PDF_Mask\redacted` + the matching W-2 detail (EEW2Detail).
- Older client set (2024 / 2025 returns, Coinbase 1099-B / 1099-MISC, Koinly Schedule D / Schedule 1, UT screens
  print) — used as the regression run (income total must stay 431,704).
- Single forms attached in chat on 2026-10-16: ADP W-2 (3 copies side by side), Fidelity IRA 1099-R (2025 layout,
  code 2), Fidelity 1099-SA (list layout), Morgan Stanley stock plan 1099 summary (1099-DIV + 1099-B box list).
- Also used: a W-2 with a summary page, a second W-2 with a summary page, Schwab / National / Vanguard / Fidelity / M1 /
  Robinhood composites, a mock 1098-T / 1095-A, a 31-page K-1 face-page file.

## Settled rules a change must keep (details in the history)
- Nothing is decided by the file name, except K-1 and Karbon — history: "File names decide nothing" (2026-11-01).
- Per document = what came in, from every source; corrected amount = the preparer's override and wins; a changed per
  document flags the correction — history: "Per document = every source" (2026-11-03).
- Saved work is keyed by the file's fingerprint, never its name — history: "Saved work keyed by the file's fingerprint" (2026-11-03).
- K-1 amounts reach the income summary only through "Add to Income Summary" — history: "K-1s: one route" (2026-11-04).
- Look: `design\DESIGN_RULES.md` (changed = light pink / blue, verified = light mint, red only for warnings) — history:
  "Design — …" and "Verified = light mint" (2026-11-01).
- Run `tests\run_tests.bat` before reporting a reader / summary / Verify change as done — history: "Automated tests" (2026-11-03).
- A test never writes a work in progress (Run check saves nothing; the tests use a temporary folder) — history: "Verified = light mint" (2026-11-01).
- From a cloud session: each changed file to a new output path per commit — history: "K-1 section" (2026-10-21).
- The UltraTax entry rules (Bot / By hand) live in the 1040, only in `core\k1v\ut_entry.py`; UT_Data_Entry types `bot`
  rows and skips `hand` rows; the only link is the CSV — `APPS_ARCHITECTURE.md`, history: "K-1 UT: the UltraTax entry rules
  move to the 1040" (2026-11-11).
- K1 liabilities go to the UT data entry CSV as up to three numeric rows `K1_nonrecourse` / `K1_qualified` / `K1_recourse`
  (ending amount with cents, Bot, a zero left out); still one K1 row on the K-1 UT page (`prep.k1_rows`). UT Data Entry's
  switch to the CSV is not built yet — `APPS_ARCHITECTURE.md` (2026-11-11).

## Browser app — status (brief `design\web_version.md`)
- **2026-11-17 — the new folder:** made from the browser parts of `1040_ultimate`; left out: the Flask server (`app.py`),
  the K-1 / AI page servers (`desktop\`), Windows file windows, the browser launcher, the PDF time limit (`safe_pdf.py`),
  masking (`masking.py`, `redact_pdf.py`, the Mask page), the desktop's first page (`templates\home.html`).
  - Run check, start to end, is now one shared function: `core\runcheck.run` (the first page's checks `check_form`, the
    reading, the K-1 run linked, the UT print loaded `load_ut` - all moved unchanged from `app.py`). The page
    (`web\py\webapp.py`) and the tests (`tests\harness.py`) call it.
  - Tests: `requirements-dev.txt` (pdfplumber, PyMuPDF, openpyxl, python-docx, Jinja2, pytest - for this computer only).
    23 pass; 22 wait for their page (they drove the desktop's pages: work in progress, K-1 pages, K-1 UT) and come back when
    it is converted; `test_cases_found` fails as before (K-1_Sample has no answer key). The Sample case matches its key.
  - `design\ut_export_format.md` + `tests\test_ut_export_format.py`: the UT data entry export checked against its written
    format (a made-up K-1 and the 26 Ready sample K-1s).
  - `APPS_ARCHITECTURE.md` fixed in both apps, still identical (Lady, 2026-11-17): master copy = this folder, the 1040 = the
    browser app, a pointer to `design\ut_export_format.md`, neutral CSV examples (no real partnership / EIN / digits).
  - Next: the page-by-page conversion, `design\conversion_plan.md`.
- **2026-11-17 — step A of the conversion built** (Lady: "Go, step A"; plan `design\conversion_plan.md`):
  - **Pages without a server:** `web\py\routes.py` = one table *address → Python function*, the same addresses the templates
    already use (`/summary/<run>` …); the functions are in `web\py\pages\` (one file per page: `summary.py`, `verify.py`,
    `ai.py`, `k1.py`, `documents.py`; shared helpers in `pages\__init__.py`). In the page frame a few lines (`SHIM` in
    `web\index.html`) hand every link, save and download to the worker. No Flask. An address not converted yet: a page says
    "Not in the browser app yet" (with the step tabs); a save answers "Not saved" (a short message shows).
  - Working now: the step tabs (1 · Summary, 4 · AI Return Review, 5 · AI Advisory as on the desktop; 2 · Verify return,
    3 · AI Doc Review, K-1 Verification say they come later), *Export Template* / *Blank template* (Schedule E) as downloads.
  - **Client folder:** *Add a folder…* now asks Chrome for read + write access; the first folder added is the client folder
    where the app will keep files (the work in progress, next step). Without one, the file is downloaded instead.
  - **Stuck-PDF guard** (`web\probe.js`): before Run check every PDF is opened in a separate small worker with MuPDF.js, with
    the desktop's time limits (documents 60 s, the prior-year return / summary 90 s). A stuck document is left out and listed
    "Not read" with the desktop's text; a stuck return / summary stops with the desktop's message. 17 PDFs: a few seconds.
  - **Open a source document:** a PDF's name on the Document inventory (and the prior-year return's) opens the PDF in a new
    Chrome tab, from the copy in the tab (`/open?path=…`). If Chrome blocks the new tab (pop-ups off for the site) the app says
    so and downloads the PDF instead. Other files: plain name until the Google Drive link question is answered.
  - **The archive check:** `tools\parity\make_reference.py` takes a clean copy of `python-final` (`git archive`, temporary
    folder - the old repository isn't touched) and the archive's own test harness, and writes what the archive reads for each
    sample client into `tests\samples\<case>\archive_reference.json` (local only). `tests\test_archive.py` compares on this
    computer; **Check against the archive** in the page compares in the browser (`web\py\keycheck.py` →
    `harness.check_reference`, one copy). Result: **both sample clients = the archive, 0 differences** — Sample (376 / 22 / 35
    rows, 70 s in the browser) and K-1_Sample (805 / 52 / 50 rows, 126 s), on this computer and in the browser.
  - Tests: 28 pass (incl. the archive check), 22 wait for their page, `test_cases_found` fails as before (K-1_Sample has no answer key).
  - Not proven here: the real new Chrome tab for a PDF and Chrome's real folder windows (the test browser blocks pop-ups and
    can't click the system folder window) — for Lady to try in Chrome.
  - Known: the templates still call `location.reload()` after some saves (it re-shows the same page) — they are changed when
    those saves are converted.
- **Phase 1 built (2026-11-16, in the old folder):**
  - `core\pdfengine.py` is the one PDF door: nothing else in `core\` imports PyMuPDF (`pdfutil.py`, `utscreens.py`,
    `ai\docs.py`, `k1v\ut_entry.py` go through it). Its header lists what the browser stand-in (MuPDF.js) must cover.
    Exception: `masking.py` / `redact_pdf.py` keep their own import (desktop only, never loaded in the browser).
  - Desktop-only code moved out of `core\` into `desktop\`: `safe_pdf.py`, `k1v_web.py` (was `core\k1v\web.py`),
    `ai_web.py` (was `core\ai\web.py`). `core\` no longer imports Flask or subprocess. Older notes that name the old
    paths mean these files. The statement-amount merge (`merge_manual`) was engine code inside the K-1 web file: it is
    now in `core\k1v\prep.py`, unchanged.
  - `ocrmypdf` and `pytesseract` removed from `requirements.txt` (never imported).
  - `wip.py` / `inventory.py` file walking stays (ordinary folder calls, fine on Pyodide's in-memory drive).
- **Phase 2 built ("see how it looks", local, read-only) - Lady: "it works" (2026-11-17):**
  - Start: `run_web.bat` -> http://127.0.0.1:5070 (Chrome / Edge). The first start downloads Pyodide 314.0.7, the libraries
    and MuPDF.js 1.28.6 into `web\vendor` (about 40 MB, `web\get_vendor.py`, versions fixed there; not in GitHub). After that
    it works offline. `web\serve.py` only hands out files - it has no upload address.
  - First page = the desktop's fields, same order (Lady, 2026-11-16: not folder-only): Prior-year return (PDF), Summary
    (PDF or Word), Work in progress (greyed out until phase 3), Documents with **Add documents…** and **Add a folder…**,
    the Use / ✕ list. The Browse buttons open the browser's own file / folder windows. A prior-year return that is also
    in the documents list counts once (same name, size and date). Then Run check -> the Summary page, drawn by the
    desktop's own template and CSS / JS files inside a frame. Read-only: a save answers "ok"
    without saving; links to pages that aren't built yet say so. Python runs in a Web Worker.
  - **Run check is shared:** the reading steps moved from `app.py` to `core\runcheck.py` (`read`, `summaries`,
    `inventory_rows`, `form_view_data`, `k1_status` ...) and the K-1 runs from the K-1 web file to `core\k1v\runs.py` -
    unchanged code; `app.py` and `web\py\webapp.py` call the same functions.
  - **PDF stand-in:** `web\py\pymupdf_js.py` + `web\mupdf_bridge.mjs`. Rules found by comparing with PyMuPDF: a turned page
    is read with the turn taken off (as PyMuPDF does); PyMuPDF's own character box (font ascender - descender < 1 -> the box
    is one font size high; stretched text counted); the word box carry-over stays inside one block; "dict" leaves out lines
    with no width. Not covered yet: the by-hand list PDF (`ut_entry.hand_pdf`), `insert_text`.
  - **Checked on the two sample folders (35 PDFs):** text, words, blocks and "dict" lines identical to the desktop on every
    page; filled shapes the same except rounding in the last decimal and a slightly different grey on a few pages (colour
    conversion; Karbon's pink bubbles read the same: 46 questions, same answers). The Sample case in the browser = its
    answer key: Documents 376 rows, Summary 22, UT check 35 - 0 differences.
  - **Answer keys in the browser:** pick a folder that has `answer_key.xlsx` -> "Check against the answer key"
    (`web\py\keycheck.py`, the desktop harness's own rows and compare). `tools\web_check\compare_pdf.bat "<folder>"`
    compares the PDF door desktop vs browser engine page by page (needs Node; replaces `tools\mupdfjs_test`).
  - **Speed:** Sample (17 documents + a 179-page return) 153 s the first time in the tab, 75 s the second; pdfplumber is the
    slow part (the prior-year return alone is 18 s on the desktop).
  - Known: the banner "Work in progress isn't being saved" shows (true in this phase). The Node check tool can't run the
    whole Run check (the cryptography library doesn't start under Node 26) - the page can.

## AI requests (Claude API) — 2026-11-12, in progress (spec `design\ai_requests.md`)
- **Status:** Step 1 was built in the desktop app (archive: settings, `.env` key, the sending function, the AI tab, cost log).
  In the browser app the AI tab waits: no API key in the web files - a Cloudflare Worker or a key each user enters, Lady
  decides first. The request files (`ai_requests\`, `ai_settings.json`) and `core\ai\` are kept. Steps 2-3 not built.
- All AI code is in `core\ai\`; `core\ai\client.py` → `send()` is the only place that calls the API. Request types are files:
  `ai_requests\<name>.md` (system prompt) + an entry in `ai_settings.json` (label, model, effort; reply size / timeout).
  `schedule_e.md` copied in unchanged.
- The AI screen is step tab 3 "AI Doc Review" (Lady, 2026-11-12 — the brief said tab 4); its name is `tab_name` in
  `ai_settings.json`. Tab 4 "AI Return Review" keeps its placeholder (the later review of the finished return).
- Model for Create Schedule E: `claude-opus-5-5`, effort high (accuracy on messy client sheets; one call per client, cents per call).
- **No masking for the AI (Lady, 2026-11-12):** the firm's API agreement allows client data, so the AI tab sends the
  originals (PDF as is; Excel / Word / text as text from the original; file names and template unmasked). Long PDFs still
  send only their AI pages (cut in memory); password PDFs go without the password. `send_unmasked` setting removed.
  The Mask page itself is unchanged.
- Schedule E template for the AI = `sche_template.template_rows()` on the Schedule E screen's properties, written by
  `write_template` in memory (Export Template uses the same function on last year's properties — unchanged).
- Calls run streamed in a background thread (time limit enforced in the loop); only a successful, valid-JSON reply is kept.
  No server-side refusal fallback to another model (the model stays the one in the settings; a refusal is shown as an error).
- `AI_logs\cost_log.csv` (one line per call, no client data; `.gitignore` lets it through). Request + raw reply in `_work\ai\`.

## Decided, not built (full text in the history)
- **Consolidated statements (Lady, 2026-11-12):** entered in UltraTax by form type, not through UltraTax's Consolidated
  Brokerage Statement (the keyboard can't move between its tabs, and its 1099-B is a grid). The 1040 keeps one document per
  statement; its summary covers 1099-DIV, 1099-INT and 1099-B (1099-B as totals by 8949 category, the way the firm enters it).
  The export splits a statement into rows with `form` = 1099-DIV / 1099-INT / 1099-B (same payer, one `doc_id` per
  statement + form). Separate DIV / INT entries per broker in UltraTax are fine for the firm. The CSV needs an account
  number (agree in `APPS_ARCHITECTURE.md`). 1099-DA is not on UltraTax's consolidated list: decide separately.
- **AI (Claude API):** "Parse with AI" on ticked documents, one call per document, nothing counts until confirmed, two models,
  saved by fingerprint, guidance not training, scans as images (no OCR) — history: "AI (Claude API)" (2026-11-02).
  Learning plan: https://claude.ai/artifact/UF1Bn9myJWtaZPaJq6XyYF
- **Fillable PDFs flattened** before the readers and the AI (small step, can come first) — same section.
- **Masking and the Print return app = separate apps;** the masking code to take out of the 1040 is listed there —
  history: "Masking and printing = separate apps" (2026-11-02).
- **Form view for the other forms:** 1099 composite next (sub-tabs, B-Summary totals only), then the single forms —
  history: "Form view — next forms" (2026-10-31).
- **Generic export CSV for every form + an export button per form tab** — history: "K-1 Prep and UT data entry" (2026-11-05);
  pending item 2 of the 2026-11-05 list.

## Open questions
- The conversion plan's five questions (Drive links, master checklist, K-1 pages in the same window, more sample clients,
  the by-hand PDF) — `design\conversion_plan.md`.
- The copied K-1 UT mock-up `design\k1_prep_mockup.html` has real partnership names / EINs and partner digits:
  kept local, not in git.
- One start file for all the apps, or each started on its own? — history: "Masking and printing = separate apps".
- 1099 composite joint accounts: how UltraTax carries them (decide when the composite is built) — history: "Form view — next forms".
- The Sample K-1s read with no EIN and no partnership name — pending item 7 of the 2026-11-05 list.
- 1120-S K-1s: box E untested (no sample) — history: "K-1 reader: box E".
- 13 AE by hand: where it goes in UltraTax (Lady adds it; the reason now says just "By hand") — `ut_entry.py`.
- Test case `tests\samples\K-1_Sample` has no answer key yet (`make_key`), so `test_cases_found` fails until it has one.

## Pending list (each list in full: history, "Pending list")
List of 2026-11-02:
- 4. `AI_logs/` folder (corrections + cost log, goes to GitHub, no client data) — cost log built 2026-11-12; corrections log
  comes with Accept (AI requests step 3).
- 6. 1120-S K-1s through the same route as 1065 (`handoff.FORMS`).

List of 2026-11-05:
- 2. Generic export CSV + export button per form tab (W2, 1098-M first).
- 4. One UT check for K-1s: Verify return skips the K-1 lines and shows the K-1 entry check's result.
- 5. Clean-up: move what `screen_verify` borrows (`norm`, `MAP`) into it; delete the old `verify1040_*` files.
- 7. Sample K-1s: no EIN / name read — look at the reader with Lady (correct the note and the test keys if needed).

Decided not to build: a document-type dropdown — history: "Decided not to build" (2026-11-02).

## Known gaps
- Schedule C vs the UT "C" screen: label-based, untested (no C screen print yet).
- B&D statement reader built from one print (column positions from the header rows); other layouts may need tuning.
- UT HSA / 8889 screen match for the 1099-SA: untested (no print with that screen).
- 1098: Prior Year from Schedule A line 8a untested (no return with a Schedule A); not checked against a UT input screen yet.
- List-layout W-2 / 1099-R tested on mock files only.
- A 2024 return once stopped both the desktop app and PDF_Mask (a PDF that crashes the reader) — cause unknown. In the browser
  app the PDF time limit comes back as a worker that can be stopped (conversion plan); until then a stuck PDF stops Run check.

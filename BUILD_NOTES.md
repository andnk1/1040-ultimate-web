# 1040 Ultimate (browser app) — build notes (read this first)

Hand-off for a new Claude session: the working rules, what's decided but not built, the open questions and the pending list.
Finished, settled work is in **BUILD_HISTORY.md** (moved there unchanged, in date order — the "history:" names below are its
section titles — written for the desktop app: its rules stay, its desktop details don't); a screen with a spec is in
`design\` (e.g. `design\k1_prep.md`). Last updated 2026-11-24.

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
  document flags the correction — history: "Per document = every source" (2026-11-03). **Since 2026-11-24 a document the
  program read (and a K-1 line) is corrected only on its own screen** (form tab / K-1 UT), not on the Summary (status).
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
- **2026-11-17 — step 2 built: the work in progress + the Summary's saves** (Lady: "Go"):
  - **Saves on the Summary work** (moved unchanged from the archive's app.py into `web\py\pages\summary.py`): corrected
    amounts + Fed. w/h, Re-confirm, + lines, carryover + lines, Return Comments and "received?" comments, ticks and comments on
    every line, the Document inventory (Verified, amounts, notes, free lines), an inventory note typed on the summary, the AI
    ticks, *Save work in progress*, *Choose a folder…*. After each save the work in progress is saved, as on the desktop
    (`routes.AUTOSAVE`). Still read-only: form tabs, UT summary, Schedule C / E, Excel (next step).
  - **Where the work is saved:** the desktop's rule and file name (next to the Karbon letter, else the prior-year return),
    but only inside a folder Chrome let the app edit — the folder added with *Add a folder…*, a folder chosen with
    *Choose a folder…*, or the work-in-progress file picked with *Browse…* (Chrome's file window with write access).
    The first save of a session keeps the old file as `.bak`, as before. Python writes the file on the tab's in-memory drive,
    `pages.save_work` hands it to the page, the page writes it into the folder (`web\index.html` saveFile / PLACES).
  - **Opening saved work:** *Add a folder…* with a `1040 Ultimate WIP … .json` in it shows *Work in progress found … Continue
    where you left off / Start fresh* (desktop: when the return was picked). *Browse…* on the Work in progress field works.
    The opening itself moved from app.py to `core\runcheck.py` (`open_work`, `put_back_work`): the same checks (another
    client's work is refused), files that moved found by name under the work's folder - also for work saved by the desktop
    app (Windows paths: `wip.file_name`).
  - **Page reloads:** where the desktop reloaded the page after a save (`location.reload()`), the templates call
    `reloadPage()` — the app draws the page again from the run, and open boxes stay open; `window.location = …` → `goTo(…)`.
  - **Proven against the archive** (`tools\parity\scenario.py`: one save of each kind, chosen from the run so any client works,
    applied in the archive through its own addresses and here through `routes.py`): the saved work, the income and deduction
    summary (corrected amounts, flags, totals), and again after the saved work is opened — **the same on both sample clients**
    — on this computer, and in the browser for Sample (K-1_Sample checked on this computer only: in the browser one check
    takes about 10 minutes - each client is read twice). Only clock times are left out of the comparison.
  - **Tried in the browser:** Run check with the folder → the work in progress written into it; a Return Comment, a Verified
    tick and a free inventory line typed on the page → in the file at once (the page redrew itself after the amount); a new
    page → *Work in progress found … Continue* → everything back, and the old file kept as `.bak`. (Tested on the browser's
    own private storage, which has the same folder interface; Chrome's real folder window and its permission prompt are for
    Lady to try.)
  - Tests: 32 pass, 18 wait for the K-1 pages, `test_cases_found` fails as before. `test_docid.py` (4) back - work keyed by fingerprints: an older work file converted, a renamed / re-saved / replaced
    document.
- **2026-11-17 — step 3 built: the rest of the Summary** (Lady: "next step"):
  - Moved unchanged from the archive's app.py into `web\py\pages\summary.py`: the form tabs' corrections (W2, 1098-M), the
    UT summary's typed fields, the Schedule C box (save, **Add P&L…**, the three CSV downloads), the Schedule E box (save,
    **Import Schedule E sheet…**, a property's workpaper CSV), **Income and Deduction Summary (Excel)**, the K-1 box's
    **Remove**. All saved into the work in progress after each change, as before. The whole Summary page now works.
  - **Picking a file on a page** (Add P&L…, Import Schedule E sheet…): the desktop opened a Windows file window and sent the
    path; now the browser's file window opens, the page copies the file onto the in-memory drive and answers its path there
    (`web\index.html` browseFile, worker `putfile`) - `static\schc.js` / `static\sche.js` are unchanged.
  - **Downloads** (Excel, CSV) are made in the tab and saved by the browser as a normal download.
  - Links with their own click code (save first, then download - e.g. the Excel button) run that code first; the frame's
    shim now steps in only for plain links.
  - **Proven against the archive** (`tools\parity\scenario.py` `more_edits` + `downloads`): a W-2 box 1 correction on the form
    tab, UT summary fields, a Schedule C business with a made-up P&L read by Add P&L…, a Schedule E property, every download
    (the Excel cell by cell, the Schedule E templates, the three Schedule C CSVs, the Schedule E workpaper - exactly), then
    the K-1 box's Remove: the saved work, the summaries and the downloads are **the same as python-final on both sample
    clients**, and again after the saved work is reopened (this computer).
  - Tried in the browser: Add P&L… (the file copied into the tab) → 3 accounts, net 48,500 → Calculate → 48,500 on the income
    summary (page redrawn); the Excel button and a Schedule C CSV download. Chrome's own file window is for Lady to try.
- **2026-11-17 — brief `design\brief_2026-11-17.md`:**
  - **1. Add more documents…** (Document inventory, bottom row, left of *Send to AI tab*; *or a folder…* next to it): the
    browser's file window (several files), the ones already in the run left out with a note naming them, the stuck-PDF guard
    on the new PDFs. Then the run is read again with every document and the work put back — Lady's suggested route: the work
    is saved, the run is read with the old + new documents through *Continue*'s own code (`open_work` / `put_back_work`), so
    keeping state needed nothing new (`web\py\webapp.py` `add_documents`). Added on top: a new document gets its default AI
    tick (put back alone would leave it unticked); the run keeps saving to the same work file. The new files are copied onto
    the in-memory drive without wiping it (worker `addmore`).
    **Only the new files are read** (Lady, 2026-11-17): everything Run check reads from a file (its type, its amounts, the
    prior-year return, the K-1s, Karbon, the UT print ...) is kept by the file's fingerprint while the app is open
    (`core\readcache.py` `remember`); the add still works the whole run out again, but the old files come from what was kept.
    A new Run check forgets it all and reads every file. The document scan's reading of one file moved into its own function
    (`core\inventory.py` `_what_it_is`, the loop's code unchanged) so it can be kept the same way.
    Proven: `tests\test_add_documents.py` (Sample: half the documents, a correction + a tick, the rest added → both kept, the
    new ones read and AI-ticked, the summaries equal to a run with every document from the start, and during the add only
    the new files are read - not the old ones, not the prior-year return); in the browser: a W-2
    correction and tick kept through two adds, the duplicate W-2 named and not added, the new lines on the summary.
  - **2. Document name only** on the Income and Deduction Summary and its Excel (`core\income.py` `_disp`): no issuer in front.
    The issuer is still read and shown on the Document inventory and the form tabs. **Intended difference** from the answer
    keys and the archive: `tests\harness.py` translates their old labels ("<issuer> — <name>") before comparing
    (`label_changes`), so only real mismatches count.
  - **3. Test: one tab per document, jump to a page** — built for Lady to try (this test browser blocks new tabs, so none
    of it could be tried here): a document opens in a tab named after it (`window.open("", name)` finds that tab while it is
    open, also after the app is reloaded); a second click does not open another tab — it brings that tab forward (or says
    "Already open in another tab") and, with a page number, changes only `#page=N` (no reload). One blob copy per document.
    Try it: open `http://127.0.0.1:5070/?test=pages` → Run check → Document inventory: each PDF has *p.1* and *p.3* test links.
    Report: second click reuses the tab? jumps without reloading? tab comes forward? after closing the tab? after New run /
    reloading the app? Lady: it works (the same tab is reused and it jumps to the page) - the test links are gone again.
- **2026-11-17 — page links (brief `design\brief_2026-11-17_page_links.md`):**
  - **Income and Deduction Summary:** every document name is a link that opens the PDF at the page where that row's amount
    was read, with **p.N** under the name (Lady); the same tab as the document's other links (one tab per document, it jumps
    to the page with `#page=N`). Rows with no page (typed amounts, Schedule C / E box, not-read documents) open the document
    at its start and show no page; a file that isn't a PDF shows its name only (the Drive link question is still open).
  - **Document inventory:** no page links (the test links removed); the name opens the whole document, same-tab kept.
  - **The readers keep the page** (`core\parsers.py`, 1 = the first page): `page` = where the form starts (the first form
    when a file holds several that are added together), `pages` = per amount when they sit on different pages (a composite:
    the page where its INT / DIV / MISC section was read, the 1099-B summary's page for short / long-term), `part_pages` =
    per Form 8949 row (capital gain distributions → the DIV page, §1256 → box 11's page). W-2, 1099-R (all three layouts
    except the list layout), SSA-1099, 1099-MISC / NEC, 1099-INT (bank forms), 1098, 1098-E, Koinly Schedule D / 1, the
    composites, the box-row / box-list summaries. K-1 rows: the page where that partnership's K-1 starts (the K-1 section
    already kept it). The summary rows carry `src_path` / `src_page` (`core\income.py` `_src`). No amount changed: the
    archive check leaves the two new fields out (written down as new, not different) and compares everything else.
  - Not given a page yet: the list-layout W-2 / 1099-R (mock files only) — their names open the document at its start.
- **2026-11-18 — step 5 built: the K-1 pages** (Lady: "the client may have K-1s and without it the verifier won't work.
  Proceed to step 5"; Verify return, step 4, comes after):
  - The 14 addresses of the desktop's K-1 pages file moved unchanged into `web\py\pages\k1.py` (K-1 Verification, the
    Interpreter with its statement amounts / totals / Add to Income Summary / Excel, the K-1 entry check + its Excel, K-1 UT
    with its saves, the UT data entry CSV and the by-hand list). What the desktop app plugged in ("hooks") is now four plain
    functions there: Add to Income Summary -> the client's run (+ the work in progress saved), the K-1 page's work -> the
    K-1 work file next to the work in progress (written into the client folder, `pages\__init__.py` `save_k1_work`), the
    taxpayer / spouse SSN from the prior-year return, the client's name for the file names.
  - **The K-1 pages open inside the app** (conversion plan, question 3 - the run lives in this tab): K-1 Verification has
    "← 1040 Ultimate (this client)"; the Interpreter and the entry check got "← K-1 Verification" (the desktop opened them in
    new tabs, so they had none); K-1 UT already had it. The Interpreter's totals still open in their own tab, as before.
  - **The by-hand list as PDF** is now a page in a new tab with **Print / Save as PDF** (Chrome prints it: landscape letter,
    the list name + client at the bottom left, "Page n of N" at the bottom right) - MuPDF.js can't draw a PDF from HTML
    (question 5). The button says "By-hand list (print / PDF)". `ut_entry.hand_pdf` replaced by `hand_html`; the PDF door
    no longer needs Story / DocumentWriter.
  - **Add K-1 PDFs…** opens the browser's file window (several PDFs at once). A picked file that is one of the client's
    documents keeps its place in the client folder, so the K-1 work file finds it again next time; a file from elsewhere
    is found only while the app is open (pick it again after a reload).
  - **The K-1 reader on its own** (`/k1v/` with no client) is kept: its form's files are copied into the tab and read there
    (`web\index.html` u1040.submit). Its Interpreter's "←" goes back to an empty reader (the result isn't kept).
  - Frame changes: a form on a page, `navigator.sendBeacon` (the Interpreter saves with it when it is left) and downloads'
    file names now go to the app; `location.reload()` in the K-1 templates → `reloadPage()`; the template's
    `request.args` (Interpreter `?tabs=1`) is passed in by the page function. Messages that said "is run.bat running?"
    reworded; after Add to Income Summary: "the Summary shows them".
  - **Proven against the archive** (`tools\parity\scenario.py` `k1_pages`, both sample clients, a fresh run): the K-1s read,
    a statement amount typed on the Interpreter, the totals, K-1 UT (box E matched, a corrected amount, a tick), Add to
    Income Summary (the package and the income / deduction summary after it), the K-1 page's saved work, and every K-1
    download (the CSV exactly, the Excel files cell by cell) - **the same as python-final on both
    sample clients** (0 differences; K-1_Sample: 32 K-1s, 26 Ready, 169 by-hand lines, the CSV and both Excel files).
    Full suite: 55 passed, the one known failure (K-1_Sample has no answer key).
  - Tests back: `tests\test_k1route.py` (6) and `tests\test_k1prep.py` (13), unchanged in what they check - the addresses
    go through the app's route table (`tests\harness.py` Client, the page frame's way). The by-hand PDF test checks the
    print page instead.
  - Tried in the browser (Sample): Run check → K-1 box → K-1 Verification (3 K-1 PDFs) → Interpreter → Add to Income
    Summary (3 K-1s, 3 lines) → back to the Summary: "K-1s added" with the lines; K-1 UT with its refusals shown ("Nothing
    to export - no K-1 is Ready"); the reader on its own with a picked K-1. The new tabs (totals, by-hand print page) are
    for Lady to try in Chrome (the test pane blocks pop-ups).
- **2026-11-23 — copies vs different forms: the W-2 rule everywhere** (Lady; first part of the form tabs brief
  `design\brief_2026-11-23_form_tabs.md`, whose decisions are written at its top):
  - Two forms in one file are the same form (Copy B / C / 1 / 2 …) when their **federal key boxes** match; state / local
    boxes never count. The copies are merged: a later copy only fills in boxes the first one missed. Key boxes
    (`core\parsers.py` `KEY_BOXES`): W-2 1, 2, 3, 5 (unchanged) · 1099-R 1, 2a, 4 + box 7 code · MISC 1, 2, 3, 4 ·
    NEC 1 (1a), 4 · INT 1, 3, 4 · 1099-SA 1, 2 (SSA 5, 4, 1098-T 1, 5 and 1095-A line 33 column C are for the brief's
    "more than one form" note - Lady, 2026-11-23).
    1098-E unchanged (its reader already compares box 1 only).
  - Before, the 1099-R / MISC / NEC / INT (bank layout) / SA readers compared every amount, so a state copy with other
    state tax counted twice. Now it counts once. Also new: two 1099-Rs with the same amounts but another code are two forms
    (before: one).
  - Changed: `parse_1099_form`, `parse_1099r` (IRS and list layout), `parse_1099int_rows`, `parse_1099sa`; shared
    helpers `_key`, `_add_copy`, `_add_up`.
  - Tests: `tests\test_copies.py` (made-up forms: state copy once, different forms added, a copy filling a missing box,
    another code = another form); 6 of its 7 fail on the old code. Full suite: 69 passed, the known `test_cases_found`.
    Both sample clients = the archive (this computer); Sample = the archive in the browser (0 differences). No sample has
    a state copy with other amounts, so the samples didn't change.
- **2026-11-23 — form tabs for every document type** (Lady: "Go"; brief `design\brief_2026-11-23_form_tabs.md`, its decisions
  at its top): no more "Form view coming soon".
  - **One column per form, never added together** (also 1099-R, 1098-E, bank 1099-INT, MISC, NEC). The readers keep each
    different form (`per_form`) and say which reader made the result (`reader`); the income summary still gets one line per
    document with the forms added, as before (as W-2).
  - **Built:** 1099-R, 1099-SA, 1098-E, SSA-1099, 1098-T, 1095-A (own layouts), and one layout ("1099") for 1099-Comp,
    1099-B, 1099-DA, 1099-DIV, 1099-INT, 1099-OID, 1099-MISC, 1099-NEC — a brokerage statement = one column; sections show
    only when a form in the tab has them (INT, OID, DIV, MISC, NEC, 1099-B totals by term, Form 8949 box lines, §1256,
    withholding). Header = the issuer (these readers keep no person / payer name), else the file name.
  - **Corrections = the reader's own result again:** each reader's "boxes → summary" step is now its own function, code
    moved, not changed (`form_1099_result`, `r1099_result`, `int_rows_result`, `e1098_result`, `ssa_result`, `sa_result`,
    `t1098_result`, `a1095_result`; brokerage statements `statement_again`, which reruns `_amounts_1099` and keeps what the
    first read took from the page text, e.g. "not read: 1099-DIV" - dropped once the preparer types that box). `parse_1099`
    keeps the no-basis proceeds and the Form 8949 box rows for it (`redo_inputs`). `core\formview.py` `FAMILIES`: per
    form type its columns and its result again. No tab is view-only.
  - **1099-B:** the Form 8949 box lines are corrected; a term's gain is their sum (shown, not typed) when the term has box
    lines, typed when it has none - so the box rows always add up (Lady's "Yes" to the recommendation).
  - **1099-SA, 1098-T, 1095-A** are not income: a correction changes their note on the Document inventory.
  - **"This file seems to hold more than one <form> — check"** (SSA-1099 box 5 / 4, 1098-T 1 / 5, 1095-A line 33C on
    another page with other amounts): SSA in the summary comment, 1098-T / 1095-A at the end of the inventory note.
  - **1099-G, 1099-K, 5498:** no reader - their tabs list the documents (the name opens it), "no reader for this form yet".
    Under every table, the documents of that type with no column (not read, excluded - e.g. a 1099-DA when a crypto report
    is used) with the reason.
  - `tests\harness.py` keeps its per-form rows for W-2 / 1098 only (fixed list), so the answer keys and the archive check
    compare the same rows as before.
  - Tests: `tests\test_form_tabs.py` (14): made-up PDFs read with one value and corrected to another = the same PDF read with
    the other value (MISC, NEC, 1099-R with two forms, bank INT, 1098-E, SSA, 1098-T, a "BOX n:" statement); a composite's
    8949 box line; 1095-A / 1099-SA; the list tabs; on Sample every document's columns give back exactly what its reader
    gave, the tabs, a composite dividend correction reaching the summary. Full suite: 83 passed, the known `test_cases_found`.
    Both sample clients = the archive (this computer); Sample = the archive in the browser (0 differences).
  - **Tried in the browser (Sample):** the tabs (1099-Comp 5 columns with INT / DIV / 1099-B totals / 8949 box lines /
    withholding, 1099-R, 1099-SA, the empty and list tabs); a 1099-R box 2a correction → the refresh banner → the income
    summary shows it.
  - **Built, not tried on a real document** (no sample has them): 1098-T, 1098-E, SSA-1099, 1095-A, stand-alone 1099-INT /
    DIV / B / OID / DA, 1099-MISC, 1099-NEC (made-up forms only). On real documents: 1099-R, 1099-SA, the composites.
- **2026-11-23 — 1099-B box groups, 8 columns, SSN, document link** (Lady: "Go"; asked first, her answers below):
  - **Form 8949 boxes keep all five numbers** (proceeds, cost, market discount, wash sale, gain): `_box_rows` and the Interactive
    Brokers path (`IB_BOXES`) keep them (`B_FIVE`); a box row is (box, gain, proceeds, five). The form tab shows each box found
    as its own group headed with its name (`formview.BOX_NAMES`: "Box A — basis reported to the IRS", B not reported, C 1099-B
    not received, D–F long-term, G–L 1099-DA, X term not known). **A term with box groups: its five totals = the boxes' sums**,
    shown not typed (Lady); corrections go on the boxes and re-run `statement_again`; a term whose boxes weren't changed keeps
    its printed totals. **Check** (`parsers._box_sum_notes`): each term's boxes must add up to its five printed totals (±$1);
    if not, the note "1099-B Short-term: the Form 8949 box lines don't add up to the term totals (cost 750.00 vs 800.00) —
    check" in the document's comment on the Income Summary (Lady: also the Summary). Summary amounts unchanged. Later feeds
    the per-form export for UltraTax.
  - **8 columns per tab** (+ Total), every tab (`PER_TAB = 8`); narrower description and inputs.
  - **Recipient SSN, last 4, on every document** — one shared search (`core\ssn.py` `last4s`): `ddd-dd-dddd` / `XXX-XX-dddd` /
    `***-**-dddd` with spaces allowed around the dashes, never an EIN; only the last 4 kept, shown `***-**-1234`, several in the
    order found, none = "SSN not read". **Form pages only, from text already read** (Lady, same day - no page is read again for
    it; Run check's `read_ssns`): each reader keeps the SSNs found on the pages it took its amounts from (`ssn4`: the 1099
    form / summary pages, the box-row / box-list pages, the 1099-R / MISC / NEC / INT / 1098 / 1098-E / 1098-T / 1095-A /
    SSA / 1099-SA form pages - the readers hand the page's words to their helpers instead of reading them twice); a W-2 keeps
    its box a; a document whose reader keeps no form pages (no reader, K-1, Koinly, list layouts) = the first 3 pages, from
    the text the document scan reads anyway (`inventory` `ssn4_first`). Not a PDF (Word, Excel …): "SSN not read". **Name:** the taxpayer's / spouse's last 4 on
    the prior-year return give the name ("***-**-1234 · Jane Doe" - Lady: match now, for the name only; the check comes later).
    Shown as a narrow **SSN** column on the Document inventory (screen only - the Excel Documents sheet is unchanged) and as the
    **SSN / Name** line at the top of every form-tab column (a W-2 whose own box a is among them shows just that one).
  - **Document line** under it in every column: the file name's first 16 letters + "…" (no .pdf), small grey, two lines at
    most, full name on hover, a link opening the PDF at the document's (first) form page like the Income Summary.
  - Tests: `tests\test_form_tabs.py` (now 18; + box groups, the add-up note, `_box_rows`' five numbers, the SSN search, the SSN on
    documents / columns). Tried in the browser (Sample, 1400 px wide): 8 columns, the SSN / Name and Document lines, Box A /
    Box D groups, a box A correction → the ST totals' sums and the Income Summary's ST (A) line follow.
  - Full suite: 88 passed, the known `test_cases_found`. Both sample clients = the archive (this computer); Sample = the
    archive in the browser (0 differences).
  - **Speed (Sample, Run check with the prior-year return, nothing kept from before):** this computer - with the first SSN
    search (every page read again) 40.1 s / 31.7 s (first / second run), with the form-pages search 28.0 s / 28.6 s; the
    browser's archive check 75 s (it was 105 s before the SSN search; the 131 s measured with the first search ran beside the
    test suite, so it was too high). Some readers now also hand the page's words to their helpers instead of reading the page
    twice. The page-text memory in `core\pdfengine.py` is on the pending list (2026-11-23 item 2).
  - Samples: no 1099-B box group is out of balance (no note). Names: the masked prior-year return gives no names, so the
    samples show the SSN alone; several samples carry a third last 4 (probably left from masking).
- **2026-11-24 — form tabs: only the client's types** (Lady): every form tab, W2 included, shows only when the client has at
  least one document of that type (skipped files don't count, excluded ones do - their tab lists them). One list
  (`core\formview.py` `TABS`, W2 first, then alphabetical) instead of TABS + TABS_IF. The Summary tab always shows; a document
  added later gets its tab when the page is drawn again. The archive check doesn't compare the tab list (the archive had
  "Form view coming soon" tabs), so no intended difference was needed. Test: `tests\test_form_tabs.py`.
- **2026-11-24 — step 4, part 1 built: Verify return, the plain conversion** (Lady: "We move to step 4"):
  - The archive's 4 addresses moved unchanged into `web\py\pages\verify.py` (the page, Check, the checklist, Save review);
    `templates\verify.html` almost unchanged. Nothing new in what it checks.
  - **Picking the files:** Browse… = the browser's file window (PDFs); the file is copied into the tab, the field shows its
    name. Before reading, the stuck-PDF guard opens each picked PDF with the desktop's 90 s (`web\index.html` guardVerify);
    a stuck one gets the desktop's message and is not read. The prior-year return picked again (another copy) is refused
    as before (compared by content - each pick gets its own place in the tab).
  - **Master checklist = a file on the shared drive** (question 2, Lady: option (a)): *Choose the master checklist file…*
    (or *Create a new one…*) once; Chrome keeps the file's handle (IndexedDB) and finds it again next session, asking once
    if it needs to (*Allow access*). Its text is kept at `core\verify.py` MASTER in the tab, so master_load / master_save are
    unchanged, and each change is written back to the shared file. Without it: the built-in list, and the save says
    "not kept for other clients". A checklist not changed yet starts again from the shared list when it is connected; one
    already changed keeps its lines, but only the shared list's lines are master lines (found in the browser test: before,
    a save pushed the 9 built-in lines into the office's file).
  - **Save review (Excel):** into the work-in-progress folder when Chrome lets the app write there (a folder added with
    Add a folder… or chosen with Choose a folder… - kept as `r["places"]`), otherwise downloaded. Same file name.
  - **Proven against the archive** (`tools\parity\scenario.py` `verify_page`: a fresh run without the UT print, the page,
    the UT print picked and checked, a tick + comment, the checklist with a line for this return and one for every client,
    Save review): the check result, the saved work, the master list and the **review Excel cell by cell = python-final on
    both sample clients** (this computer), and Sample in the browser (*Check against the archive*: every sheet and page,
    Verify included, 0 differences). The archive reference was made again to add this page; its other parts are unchanged
    (checked; K-1_Sample's by-hand heading now holds "(date)", which the check already left out).
    The review's "saved <time>" heading is left out like the other clock times.
  - **Readers changed after the archive** (1099-R / NEC / MISC / 1098-E per form, 1099-B five numbers per 8949 box): no
    difference on those documents - the UT check sheet, the review Excel and its Documents sheet match the archive. (Sample
    has a 1099-R; no NEC / MISC / 1098-E; no 8949 box out of balance.)
  - Not tested: the checks without the input screens (no sample has a finished 2025 return - question 4); Chrome's real
    file windows and its permission prompt for the shared file (the test browser can't click them; tried with the browser's
    own storage, which has the same interface).
  - Tried in the browser (Sample): Run check → Verify return → Browse… the UT print → Check (14 data-entry differences, 7 UT
    entries with no document) → a tick, a checklist note → Save review → `Review 2025 - Sample.xlsx` in the client folder;
    the remembered master file found by itself on a new run, a Stays Y line written back to it.
  - Tests: `tests\test_verify_page.py` (4: stuck PDF, prior-year return again, folder or download, the master file). Full suite: 92 passed, the known `test_cases_found`.
  - Next (part 2): the K-1 section, then the entry check's old page and Excel addresses go.
- **2026-11-24 — new test case `tests\samples\1040_Complete` + Verify return fixes** (Lady):
  - **Draft answer key** made (`tests\make_key.py 1040_Complete`), nothing ticked - Lady checks it. Roles: the 2024 return =
    Prior-year return, the 2025 return = Current-year return, `UT_data_entry.pdf` = UT input screens, every other file a
    Document (the `Sch E` sub-folder isn't read - a case is its top-level files). Rows: Documents 383, Summary 25, UT check 35.
    No archive reference for it (Lady). Sample unchanged.
  - **Role guess fixed** (`tests\harness.py` `guess_roles`): the 2024 return also passed the "looks like a UT print" test, so
    it was only tried as a UT print (the real print won) and the 2025 return became the prior-year return. A file that loses
    the UT pick is now still tried as a return.
  - **Digital Assets Transactions on the UT print** (`core\utscreens.py` `_digital_assets`, Lady): the section is printed
    misaligned - on a record's first line each value sits one column right of its header (units sold "1" under "1=S,2=L",
    the term under "Force", the price cut off). Now its own section (before, it was read as part of "Capital Gains and Losses"
    above it, with those columns): the gain / (loss) comes from the second line's **AMT Gain -Loss** column (its TOTAL is the
    sum), the term from the digit under "Force" (none = short), the box from "H/K" / "I/L" by term. The units and the price
    are never used, so the "1" entries under *UltraTax entries with no document* are gone. New case: Koinly Schedule D B/H
    649, C/I -140, F/L 5 now tie (UT 648 / -140 / 5, boxes H / I / L), on this computer and in the browser.
    Test: `tests\test_verify_page.py` `test_digital_assets_misaligned_print` (made-up words laid out like the print).
  - **2 · UltraTax entries with no document:** screen, entry, what, amount and page only as wide as needed, side by side on
    the left (a long entry wraps); the comment takes the rest of the line.
  - Seen on the new case, not changed: Koinly Schedule 1 line 8v 225,816 vs UT Other income 21,033 ("not entered"); a K1-3
    "Ordinary business income" line under no-document entries (the K-1 section, part 2, takes the K-1s).
  - Full suite: 95 passed + the new digital-assets test, the known `test_cases_found`; Sample and K-1_Sample still = the
    archive (their UT prints have no Digital Assets section).
- **2026-11-24 — read documents are corrected on their own screen, not on the Summary** (Lady: "Go, build the lock"; her
  rule, never written down before):
  - **Locked on the Income and Deduction Summary:** the corrected amount and Fed. w/h of every document the program read and
    of every K-1 line (`core\income.py` `where_to_correct` -> the row's `lock` = where to change it: "the W2 tab (Document
    inventory)", "the 1099-Comp tab …", "K-1 UT (Open K-1 Tab)"). The boxes are read-only; a key typed or a paste in one
    shows "Read from the document — change the amount on <screen>." (`templates\summary.html` lockWarn). The save refuses a
    new amount too (`web\py\pages\summary.py` `_without_locked`): only the comment is taken.
  - **Still typed on the Summary:** not-read documents, lines added with +, add-backs, the Schedule C / E box results, and
    the crypto reports' Schedule D / Schedule 1 rows - they have no screen of their own yet, so locking them would leave
    nowhere to correct them (when they get a form tab, `where_to_correct` locks them by itself). Inventory lines were
    read-only on the Summary already (changed on the inventory).
  - **Corrections saved before** (an older work in progress) **are kept** (Lady): they still count, and the row says
    "corrected here before amounts from documents were locked — still counts; move the correction to <screen>". A new amount
    can't replace it.
  - **Archive check:** the scenario's test correction typed on the first document row (a W-2) is now refused, so it moved to
    the first row still typed on the Summary (a crypto report's row, a Schedule C / E result or a not-read row) - in both
    apps - and the archive reference was made again (its other parts unchanged, checked). Intended difference written in
    `design\conversion_plan.md`. Side effect seen: the scenario's W-2 form-tab correction (12,345.67) now reaches the summary,
    as it should - before, the old summary correction on the same row hid it.
  - Tests: `tests\test_lock.py` (5: which rows lock, a new amount refused but the comment kept, a typeable row still takes
    one, a saved correction kept and not replaceable, the locked boxes on the page). Tried in the browser (Sample): 23 locked
    boxes; a key typed in the W-2's corrected amount -> the warning under it, the amount unchanged.
  - The archive check leaves out the two new row fields `lock` / `kept` (new, not different - like `src_path`). K-1_Sample
    has only K-1 lines, all locked, so its scenario no longer types a correction or a tick (Sample still covers both).
    Full suite: 99 passed + both archive cases = the archive (re-run after the fields were left out), the known
    `test_cases_found`. The in-browser archive check was not re-run for this change (same Python and template).
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
    with no width. Not covered: `insert_text`; the by-hand list PDF is a print page since step 5 (no PDF drawn).
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
- **Brief 2026-11-21 (K-1s tab, `design\brief_2026-11-21_k1_tab.md`) — all 6 steps built.** Decisions (Lady, 2026-11-21):
  - IRA distributions and pensions/annuities **stay two categories** (1040 line 4 vs line 5). The prior-year comparison and
    Verify return check them line by line.
  - The K-1 section opens in **its own browser tab, driven by the main tab**: one Python, one set of documents. It is not a
    second copy of the app and not a SharedWorker.
  - The K-1 page is called **"K-1s"**. **"K-1 Verification"** is the new name of the K-1 Interpreter.
  - The **stand-alone K-1 reader is dropped**. K-1s are reached only from a 1040 run.
  - The **K-1 entry check leaves the K-1 pages** and moves to Verify return, with K-1s included by default and an option to
    leave them out. The checking code stays.
  - The K-1s page is **split by form**: a K-1 1065 tab and a K-1 1120-S tab. 1120-S is not built yet; it will mirror 1065.
  - **K-1 Verification is split by form too** (asked while building): each tab shows its own form's K-1s.
  - Until Verify return is built, the entry check's pages and addresses (`/k1v/verify/<token>`, its Excel) keep working with
    no link to them, so the archive check (`tools\parity\scenario.py`) still covers them. They are removed when the check
    moves to Verify return.
  - **Step 6 built:** `design\conversion_plan.md` updated:
    - page 6 is now K-1s: its own tab, split by form, the stand-alone reader dropped;
    - page 7 is now K-1 Verification;
    - Verify return gets a **K-1 section**: included by default, an option to leave the K-1s out, one row per K-1 (name,
      Verified / n differences) that opens to the detail, its Excel, and the reason when the UT print has no K-1 screens;
    - the intended differences and question 3 are updated.

    That reason is now kept in the run: `attach_screens` stores it as the K-1 run's `scr_error`, and `load_ut` / the K-1s
    page copy it to `r["k1_scr_error"]`. Test: `test_no_k1_screens_reason_is_kept`. README's K-1 text is updated.
  - **Step 1 built (Lady: "Go, Step 1"):** Income and Deduction Summary: the page number is now on the same line as the
    document name ("… .pdf p.3", `srclink` in `templates\summary.html`). K-1 box: "K-1 documents found, review K-1's tab"
    in bold, not red, and no longer in the box of problems at the top ("changed since added — add again" stays red there).
    The button is now **Open K-1 Tab** (until Step 5 it still opens inside the app); the K-1 entry check button is gone.
    The two K-1 messages that named the old button were changed too. Tests: `test_k1route` checks the new text.
    The archive check now leaves out the date in the by-hand list's heading ("Tax year 2025 · <the day it was made> · …",
    `tools\parity\scenario.py`). Before, K-1_Sample failed on any day except the day its reference was made.
  - **Step 3 built (Lady: "Go, Step 3"): the K-1s page** (`templates\k1v\home.html`, `web\py\pages\k1.py`). Title "K-1s".
    Tabs **K-1 1065 (n)** / **K-1 1120-S (n)**: n counts K-1s, not files. Each tab is one section drawn by the same macro
    (`FORM_TABS` / `_form_tabs`, so 1120-S can later get what 1065 has). From top to bottom:
    - **Add K-1 PDFs…**
    - the K-1 PDFs, each name opening the PDF (`/open?path=…`) with "n K-1s" beside it;
    - the "Not read" lines;
    - **K-1 Verification** and **K-1 UT** (1120-S: "K-1 UT — not built yet", greyed). Both open in the same tab.

    A file goes on the tab of the K-1s found in it (both kinds: both tabs). A file with no K-1 read (e.g. a state K-1) is
    listed on both tabs with "no K-1 read". The banner and the entry check button are gone. The 1120-S code table stays.
    Back links say "← K-1s" (K-1 Verification, K-1 UT, the unlinked entry check page).
    **Stand-alone reader dropped:** the Read form, `POST /k1v/`, `read_on_its_own` and the frame's form code (`u1040.submit`
    and the SHIM's submit listener in `web\index.html` - no page has a form now). `/k1v/` without `?for=` shows "Open the
    K-1s from a client's Summary (K-1 box → Open K-1 Tab)." No test drove the stand-alone form.
    **K-1 Verification split by form (Lady: "Split by form"):** each tab's button opens it with `?form=1065` / `?form=1120-S`
    and only that form's K-1s show: the cards, "Jump to K-1", the count line, Verified n of N, print and the reviewer copy.
    The other K-1s stay on the page, hidden, not left out, because its saves (statement amounts, ticks, comments) are kept
    for the whole run by page number. Totals and Add to Income Summary work as before. The 1120-S view has no Calculate
    totals, Excel or Add to Income Summary (1065 only). "← K-1s" goes back to the tab it came from. A K-1 keeps its
    number (#1, #2 …) on both views. Without `?form=` every K-1 shows, as before.
    New `tests\test_k1s_page.py`:
    - the page itself;
    - which tab a file goes to;
    - no stand-alone reader;
    - adding one K-1 PDF reads only that file.
  - **Step 4 built (Lady: "Go, Step 4"): K-1 Verification** (the former K-1 Interpreter, `templates\k1v\report.html`).
    - **`#` links fixed for every page**, in the frame's `SHIM` (`web\index.html`). A link starting with `#` scrolls to that
      part of the page and never loads anything. The page's own click code runs first (the tabs view still switches tabs
      with the same links). Before, "#k1-3" loaded the app inside the frame, because a page drawn from text has the app's
      address. Checked in the app's frame: the jump scrolls, the frame stays on the page.
    - **Each K-1's name in its card header opens its PDF at that K-1's page** (`/open?path=…&page=N`, in the PDF's own
      tab). The page knows the run's PDFs in order (`DOCS`): the file is `DOCS[page / 1000]`, the page in it is
      `page % 1000`. The header shows the real page ("PDF page 3", the file name on hover). "Copy of PDF page …" now says
      "PDF page 3 of <file>" when there are several PDFs. The reviewer's copy keeps the name as plain text. Checked on the
      K-1 sample client: all 32 names link to the right file and page, and no file-coded page number is left.
    - **Renamed:** page title, heading and the reviewer copy's heading say **K-1 Verification**, and so do the two
      tooltips that named the Interpreter (K-1 UT, the entry check). The saved-entries file keeps its old tag ("K-1
      Interpreter entries") so files saved before still load. The code keeps its names (`interpreter`, `/k1v/k1/…`).
    - Tests: `tests\test_k1s_page.py` (the name, the PDFs in order, the link, no file-coded page).
  - **Step 5 built (Lady: "Go, Step 5"): the K-1 tab.** "Open K-1 Tab" on the Summary opens the K-1s in a browser tab of
    their own: `web\k1tab.html`, a page frame with no Python. The 1040 Ultimate tab (its `window.opener`) draws every page
    in it and does every save through its one worker (`web\index.html`, `u1040.k1`). The pages and their SHIM are
    unchanged: the K-1 tab's `u1040` passes each link, save, download and `sendBeacon` to the 1040 tab.
    - **One K-1 tab per app tab:** its name carries the app tab's id, which a reload of the app keeps (sessionStorage). A
      second click brings the open tab back; after a reload or a New run, the click fills the same tab again.
    - **PDF links in the K-1 tab** (the K-1 PDFs list, the K-1 names): the PDF's tab is opened by the K-1 tab's click, then
      filled from the 1040 tab's copy (`showDocument`).
    - **Add K-1 PDFs…** opens its file window in the K-1 tab; the files go to the 1040 tab's worker.
    - **After a change in the K-1 tab** (Add to Income Summary, K-1 PDFs added, any K-1 save) the 1040 tab draws the Summary
      again, 1.2 s after the last save, at the same scroll position. The K-1 box and the totals change.
    - **"← 1040 Ultimate (this client)"** in the K-1 tab brings the 1040 tab forward. If Chrome won't, it says "Switch to the
      1040 Ultimate tab"; it never loads the Summary in the K-1 tab.
    - **The 1040 tab closed or reloaded:** the K-1 tab checks every 2 s and before every request. It then shows "The 1040
      Ultimate tab was closed or reloaded — open the K-1 tab again from the Summary (K-1 box → Open K-1 Tab)." (the tab's
      name says "not connected"). Nothing saved is lost.
    - **Refresh (F5) in the K-1 tab:** the address keeps the page shown (`#/k1v/…`), so the same page comes back.
    - **A save sent as the K-1 tab closes** (K-1 Verification's `sendBeacon`): the 1040 tab reads the data, not the closing
      tab (the SHIM now calls `u1040.beacon`).
    - **Pop-ups blocked:** the document tabs' message, then the K-1s open inside the app as before. The K-1 pages' own new
      tabs (the totals, the by-hand print page) open from the page's click as before.
    - **Tried in the test browser:** it blocks real pop-ups, so the K-1 tab was loaded into a test frame of the 1040 tab with
      the 1040 tab as its opener (the same calls). Shown through the 1040 tab's worker: the K-1s page, K-1 Verification and
      "← K-1s". Add to Income Summary redrew the 1040 tab's Summary ("3 K-1s added", same scroll). Also checked: the
      "reloaded" message, a refresh on K-1 Verification, a closing-tab save, and the blocked-pop-up message with the K-1s
      inside the app. **For Lady to try in Chrome:**
      - the real K-1 tab: a second click, after reloading the app, after closing the app tab;
      - a PDF link from the K-1 tab;
      - "← 1040 Ultimate" bringing the tab forward;
      - Add K-1 PDFs… in the K-1 tab.
  - **Step 2 — nothing built (Lady, 2026-11-21).** IRA and pensions/annuities stay two categories (1040 line 4 vs line 5).
    The flag for an unread IRA/SEP/SIMPLE box already exists: the 1099-R note says "IRA/SEP/SIMPLE: box not read — placed
    under pensions, confirm" (`core\parsers.py` `_r_result`). It stays as it is. Known limits: on the IRS layout, a tick
    drawn as a picture reads as "not checked"; the broker-form text reader can't see an empty box, so an unchecked one
    says "not read".
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
- **Form view — what is left** (the form tabs were built 2026-11-23, see the status): a reader for 1099-G, 1099-K and 5498 (their
  tabs only list the documents); per-form reading for SSA-1099, 1098-T, 1095-A (pending list 2026-11-23).
- **Generic export CSV for every form + an export button per form tab** — history: "K-1 Prep and UT data entry" (2026-11-05);
  pending item 2 of the 2026-11-05 list.

## Open questions
- The conversion plan's open questions (Drive links, master checklist, more sample clients; K-1 pages inside the app and
  the by-hand print page were built in step 5) — `design\conversion_plan.md`.
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
- 4. One UT check for K-1s: Verify return skips the K-1 lines and shows the K-1 entry check's result — now planned as Verify
  return's K-1 section (`design\conversion_plan.md`, 2 · Verify return; brief 2026-11-21).
- 5. Clean-up: move what `screen_verify` borrows (`norm`, `MAP`) into it; delete the old `verify1040_*` files.
- 7. Sample K-1s: no EIN / name read — look at the reader with Lady (correct the note and the test keys if needed).

List of 2026-11-21 (after the K-1s tab brief):
- 1. **1099-R not read when the box number is printed apart from its name** (a 401(k) plan's 1099-R, IRS layout, 3 copies on
  one page, amounts with "$"). The "1" sits just left of "Gross distribution" on the page but was written as separate
  text, so `_page_copies` (`core\parsers.py`) finds no "1 Gross distribution" line and reads nothing. Fix: also accept
  the box number as the word just left of the name on the same row. The function is shared with MISC / NEC / SA / 1098-E,
  so check the archive. Also `_r_extras`: find the label printed as "IRA/SEP/" + "SIMPLE" on the next line. Test with a
  made-up form built the same way (not the client's file).

List of 2026-11-23 (form tabs brief):
- 1. **Per-form reading for SSA-1099, 1098-T, 1095-A** (later, Lady). Until then they read one form per file; the brief adds
  the note "This file seems to hold more than one <form> — check." Today the 1098-T takes the first value of each box from
  any page and the 1095-A the last line 33 it finds, so a file with two forms can mix them.
- 2. **Page-text memory in `core\pdfengine.py`** (later speed-up, Lady): keep each page's text / words the first time they are
  pulled out (by the file's fingerprint + page number, cleared at each Run check), so the document scan, the readers and the
  SSN search never ask MuPDF for the same page twice. Results don't change; the archive check proves it.

List of 2026-11-24:
- 1. ~~Read documents can't be changed on the Summary~~ — built 2026-11-24 (see the status).
- 2. **Reconciliation Summary (Excel)** (Lady, for her boss, 2026-11-24): one workbook, the comments included on every tab
  except the K-1 one. Tabs:
  - **Notes** - loosely after Lady's picture: a heading block (entity type 1040 Individual, tax year, accounting method,
    preparer, reviewer, date), then Questions (check off when cleared; answer / notes / document links), Documents needed
    (check off when received; notes), Prep comments & notes (reminders for prep & self-review; notes for reviewer; notes for
    next year), Reviewer comments;
  - **Document summary**, **Income summary**, **Client info** (Karbon + documents), **Schedule C**, **Schedule E**;
  - **K-1 summary** - the data only, no comments.
  On the Summary's bottom bar: the **Print Page** button goes, and **Income and Deduction Summary (Excel)** is replaced by
  **Reconciliation Summary**. Not built - waits for "go" (questions first: where each Notes section's lines come from).

- 3. **Brief `design\brief_2026-11-24_k1_documents.md` — K-1s as documents** (Lady: "step by step, stopping after each";
  before Verify return's K-1 section, then the Reconciliation Summary). Answers to the questions asked first (Lady,
  2026-11-24):
  - **One file:** everything the K-1 tab and K-1 UT keep (corrections, statement lines, Verified ticks, Count / Don't
    count, 11 ZZ, 11 S, notes, ticks, partner, UT #) goes into the client's one work in progress, like the other form tabs,
    keyed by the file's fingerprint + page. The old K-1 work file is read once to carry its work over (step 5), then not
    written any more.
  - **11 S Short-term / Long-term** choice: in the K-1 tab, on each 11 S line (next to the 11 ZZ → Schedule E tick).
  - Built so far: see the status (step by step).

Decided not to build: a document-type dropdown — history: "Decided not to build" (2026-11-02).

## Known gaps
- Schedule C vs the UT "C" screen: label-based, untested (no C screen print yet).
- B&D statement reader built from one print (column positions from the header rows); other layouts may need tuning.
- UT HSA / 8889 screen match for the 1099-SA: untested (no print with that screen).
- 1098: Prior Year from Schedule A line 8a untested (no return with a Schedule A); not checked against a UT input screen yet.
- List-layout W-2 / 1099-R tested on mock files only.
- A 2024 return once stopped both the desktop app and PDF_Mask (a PDF that crashes the reader) — cause unknown. In the browser
  app the PDF time limit comes back as a worker that can be stopped (conversion plan); until then a stuck PDF stops Run check.

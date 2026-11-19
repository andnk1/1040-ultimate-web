# Conversion plan — the desktop pages into the browser app

Written 2026-11-17, after the desktop app was retired (brief: `design\web_version.md`). Nothing below is built yet: build only
after Lady's "go", one step at a time, stopping after each step with its result.

**The reference for every page is the archive** — git tag `python-final` (commit 8e7b150) in the old repository `1040_ultimate`.
A page is done when it gives the same results as the archive on the sample clients (see "How a page is proven" at the end).

## Where things stand

| Page | Desktop (archive) | Browser app today |
|---|---|---|
| 0 · Choose the files | `templates\home.html` + `/run`, Windows file windows | **Built** (`web\index.html`): same fields, Work in progress + Continue / Start fresh |
| 1 · Summary | `summary.html` + 24 save / download addresses | **Built** (steps 2-3): every save and download |
| 2 · Verify return | `verify.html` + 4 addresses | not yet |
| 3 · AI Doc Review | `ai_requests.html` + 4 addresses, API key in `.env` | not yet — waits for the key decision |
| 4 · AI Return Review, 5 · AI Advisory | placeholder pages | **Built** (step A) — same pages |
| 6 · K-1 Verification | `k1v\home.html` (new browser tab) | **Built** (step 5) — inside the app |
| 7 · K-1 Interpreter + K-1 entry check | `k1v\report.html`, `k1v\verify.html` | **Built** (step 5) |
| 8 · K-1 UT | `k1v\prep.html` + CSV / Excel / PDF | **Built** (step 5) — the PDF is a print page |
| Mask page | `mask.html` | **not converted** — a separate app |

## How the pages run without a server (step A — before any page) — **built 2026-11-17**

On the desktop, every click on a page went to the Python server (`/edits/<run>`, `/verify/<run>/save` …). In the browser the
Python runs inside the tab (in the worker), so those addresses need a new answer:

- **A1. Page functions + one address table.** The code behind each desktop address is moved from the archive's `app.py` and
  K-1 / AI page files into plain Python functions, one file per page: `web\py\pages\summary.py`, `verify.py`, `k1.py`, `ai.py`.
  `web\py\routes.py` is one readable table: *this address → this function* (the same addresses the templates already use, so
  the templates and `static\*.js` stay almost unchanged). The page frame passes every save, link, form and download to the
  worker, which looks the address up in the table. No Flask: with one version only there is nothing to share it with, and a
  table you can read beats a framework you have to learn.
- **A2. The client folder.** "Add a folder…" asks Chrome for *read and write* access to the client folder (Chrome shows
  "Allow this site to edit files?" once per session). The work in progress is written there — the same file name and the same
  `.bak` rule as the desktop. With single files only, the existing "Choose a folder…" banner asks for the folder.
- **A3. The stuck-PDF guard.** Each PDF is first opened in a small separate worker with a time limit; a PDF that hangs is
  named (file + page) and left out ("Not read"), as on the desktop — the page never freezes.
- **A4. Opening source documents (new — the desktop had no "open" link).** The file name on the Document inventory becomes a
  link: a PDF opens in a new Chrome tab (straight from the picked file — nothing is uploaded); other files open by a Google
  Drive link (question 1).
- **A5. Downloads** (Excel, CSV): made in the tab, saved by the browser as a normal download (or written into the client folder
  where the desktop wrote into a folder — question per page below).
- **A6. The archive check** (`tools\parity\`, see the end): the reference results from `python-final`, and a
  **Check against the archive** button in the page, like *Check against the answer key*.

## Page by page

### 0 · Choose the files — finish
- **Changes:** the Work in progress field works: pick the `.json`, or it is found in the picked client folder → *Continue where
  you left off / Start fresh* (as on the desktop).
- **Loses:** the desktop found the work in progress next to a picked return anywhere on the disk, and found moved documents by
  searching the folder tree; typed paths; `start_folders` (where the file windows opened).
- **Replaced by:** a search inside the picked client folder only (the browser can't see the rest of the disk); documents are
  matched to the saved work by their fingerprint, as now. Chrome remembers the last folder by itself.
- **Proven by:** the same work in progress loaded in the archive and in the browser gives the same run (the Summary sheet and the
  saved work compared). The tests in `tests\test_docid.py` (4) come back.

### 1 · Summary — make it work (not just show)
Done in small pieces, each proven before the next: (a) corrections, ticks, comments, + lines, Re-confirm, Return Comments;
(b) Document inventory amounts / notes / AI ticks, free lines; (c) form tabs W2 / 1098-M corrections + Refresh; (d) UT summary;
(e) Schedule C box + Add P&L…; (f) Schedule E box + Import / Export template / workpaper CSV; (g) carryover / Karbon / client
summary ticks; (h) Income and Deduction Summary (Excel); (i) K-1 box Remove.
- **Changes:** every save goes to the page functions in the tab; the work in progress is saved into the client folder after
  every change (as the desktop did after every save).
- **Loses:** saving without asking anything (the desktop wrote next to the client's files freely); Windows file windows for
  *Add P&L…*, *Import Schedule E sheet…* and *Choose a folder…*; downloads served by the server.
- **Replaced by:** the folder permission from A2; the browser's file window; downloads made in the tab.
- **Proven by:** a fixed list of edits (one of each kind above) applied to the Sample case in the archive and in the browser →
  the Summary sheet, the saved work in progress (dates and paths left out) and the Excel file cell by cell are the same.
  Needs one sample P&L (CSV or Excel) — none in the samples yet.

### 2 · Verify return
- **Changes:** the UT input screens print and the 2025 return are picked on the page with the browser's file window; reading
  runs in the worker with the stuck-PDF guard; the result, ticks and comments are saved with the work in progress.
- **Loses:** the master checklist file `checklist_master.json` kept in the app folder (one per computer); *Save review
  (Excel)…* into a folder chosen in a Windows window (default: the prior-year return's folder).
- **Replaced by:** the master checklist in a file Lady picks once (question 2); the review Excel written into the client folder
  (or downloaded).
- **Proven by:** the "UT check" sheet (already in the answer keys) and the return-based checks on the same files; the review
  Excel compared cell by cell. The Sample case has the UT print; a sample with a finished 2025 return is needed for the checks
  *without* the input screens (question 4).

### 3 · AI Doc Review
- **Changes:** the page and its documents table (which documents, which pages) work; **Send stays off** until Lady decides
  how the key is held (rule: no API key in the web files — a Cloudflare Worker or a key each user enters).
- **Loses:** sending (for now); the cost log `AI_logs\cost_log.csv` on the disk; the request + raw reply copies in `_work\ai`.
- **Replaced by:** after the decision — the Worker (it can keep the cost log) or the user's key (the cost log downloaded or
  written into a folder).
- **Proven by:** the request the archive would send (documents, pages, the Schedule E template) built in the browser without
  sending — the same, byte for byte.

### 4 · AI Return Review, 5 · AI Advisory
- **Changes / loses:** nothing — placeholder pages. **Proven by:** the same page text. (Can go with step A.)

### 6 · K-1 Verification (the K-1 run page)
- **Changes:** opens inside the app with *← Back to Summary*, instead of a new browser tab (the run lives in this tab's
  worker; a new tab would start empty) — question 3. *+ Add K-1 PDFs…* uses the browser's file window. The K-1 work file is
  saved next to the work in progress in the client folder.
- **Loses:** the new tab; the stand-alone K-1 reader at `/k1v/` without a 1040 run (to keep as a mode of the same page, or drop).
- **Replaced by:** the same page in the app's frame; files from the browser's file window.
- **Proven by:** every K-1 line read from `tests\samples\K-1_Sample` (17 files, 64 K-1s) and from the Sample case, compared
  with the archive (the K-1_Sample case has no answer key yet: the archive's results are the reference).

### 7 · K-1 Interpreter + K-1 entry check
- **Changes:** statement amounts, 11 S / 11 ZZ ticks and corrections saved in the tab; *Add to Income Summary* sends the
  package to the Summary in the same tab; the entry check against the UT print; the two Excel files made in the tab.
- **Loses:** the server keeping the K-1 run while other tabs used it.
- **Replaced by:** the worker keeping it (one tab).
- **Proven by:** the package added and the income summary lines after adding; the entry-check rows; the Excel files cell by
  cell — the same as the archive. The tests in `tests\test_k1route.py` (6) come back.

### 8 · K-1 UT
- **Changes:** box E match, corrections, added lines, copies, Bot / By hand — all saved in the tab; *Export for UT data entry*
  downloads the CSV; the by-hand list as Excel.
- **Loses:** the by-hand list as **PDF** — the desktop built it from HTML with PyMuPDF; MuPDF.js has no HTML-to-PDF.
- **Replaced by:** a print page of the same list (Chrome → Save as PDF) — question 5.
- **Proven by:** the CSV byte for byte against the archive on K-1_Sample, and against its format (`tests\test_ut_export_format.py`,
  already passing); the by-hand Excel cell by cell. The tests in `tests\test_k1prep.py` (12) come back.

### Dropped
- **Mask page** — a separate app. **`/browse`** (Windows file windows) — the browser's own. **`/debug/stacks`** — the progress
  list in the page and the browser console (F12) instead.

## Order of work (each step: stop, report the archive check, wait for "go")
1. **A** — page plumbing, client-folder access, stuck-PDF guard, open-document links, the archive check tool; pages 4 · 5.
   **Built 2026-11-17** — both sample clients = the archive (0 differences); details in BUILD_NOTES.md.
2. **0 + 1a–1b** — work in progress (load / save), the Summary's corrections, ticks, comments, inventory.
   **Built 2026-11-17** — the saved work and the summaries = the archive after the same edits, and after reopening.
3. **1c–1i** — form tabs, UT summary, Schedule C / E, Excel, K-1 Remove. **Built 2026-11-17** — the whole Summary works.
4. **2** — Verify return.
5. **6 → 7 → 8** — the K-1 pages. **Built 2026-11-18** (before step 4, Lady) — details in BUILD_NOTES.md.
6. **3** — AI Doc Review, after the key decision.

## Intended differences from the archive (decided by Lady after python-final)
- 2026-11-17 — the Income and Deduction Summary (and its Excel) shows a document's name only, without the issuer in front
  (brief_2026-11-17, item 2). The archive check and the answer keys translate the old label before comparing
  (`tests\harness.py` `label_changes`).
- 2026-11-18 — the K-1 pages open inside the app (question 3); the by-hand list's PDF is a print page (question 5:
  Chrome's Save as PDF).
- 2026-11-17 — each summary row carries the page its amount was read on (`src_path` / `src_page`, the name's link) — new,
  the archive has no such field: the check leaves those two fields out (`tools\parity\scenario.py` `normalize`).

## How a page is proven ("same results as python-final")
- **The reference:** a clean copy of the archive (`git archive python-final`, in a temporary folder — the old repository is
  not touched) runs each sample client through the archive's own code and writes its results (the three answer-key sheets, plus
  per page: the saved work in progress, the Verify rows, the K-1 package, the CSV, every Excel file). The reference files
  stay on this computer (they hold client data; never in GitHub).
- **The browser:** the same sample client through the converted page in the tab → the same results → compared. Pass = 0
  differences; any difference is shown to Lady with the reason before the page counts as done.
- **The sample clients:** `tests\samples\Sample` (17 documents, prior-year return, UT input screens print, Karbon organizer) and
  `tests\samples\K-1_Sample` (17 K-1 files). Wanted too (question 4): the older client set used as the regression run (income
  total 431,704), the 110-page UT input screens print, a finished 2025 return, a sample P&L.

## Questions for Lady (with my recommendation)
1. **Google Drive links for files that aren't PDFs.** The browser sees a picked file's name, not its Drive address. (a) A Drive
   search link by the file's name (opens Drive's search; one more click) — simple, no setup. (b) Sign in to Google from the app
   (Drive Picker) for exact links — needs a Google Cloud project and an approval screen. *Recommend (a).*
2. **The master checklist.** (a) A file on the shared drive, picked once (one list for the whole office; Chrome asks for access
   again each session). (b) Kept in each browser (one list per computer; export / import to share). *Recommend (a).*
3. **K-1 pages** inside the app with *← Back* (recommended), or in a new tab (needs the two tabs to talk to each other — more
   code, no gain I can see).
4. **More sample clients** for the archive check: the regression set (431,704), the 110-page UT print, a finished 2025 return,
   a P&L — as folders under `tests\samples` (local only).
5. **The by-hand list PDF:** a print page (Chrome's Save as PDF) — recommended — or a PDF drawn line by line with MuPDF.js
   (more code to read and keep).

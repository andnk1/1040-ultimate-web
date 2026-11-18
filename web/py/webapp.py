"""webapp.py - the browser app's start: Run check from the first page (web/index.html), and the stuck-PDF guard's texts.

The pages after Run check are answered by web/py/routes.py (the address table) and web/py/pages/ (one file per page).

Called from web/worker.js:
    run_check(pyret, docs, step, clientsum, stuck, wip, writable)  -> the run's token (Run check: core/runcheck.run),
                                                    then the work in progress saved into the client folder
    add_documents(token, docs, step, stuck, writable)   -> Add more documents…: the run read again with the new documents,
                                                    the preparer's work put back -> the new run's token
    password_candidates(names)                      -> the passwords to try for each PDF (the stuck-PDF guard needs them)
    stuck_message(name, where, seconds)             -> the text shown when the PDF reader gets stuck on a file
"""
from __future__ import annotations

from pathlib import Path

import json

from core import runcheck
from core import readcache
from core import wip as wip_mod
from core.pdfutil import password_candidates as _candidates

from pages import RUNS, save_work

WORK = Path("/work")                                 # split brokerage packages (in memory, gone when the tab closes)


def _quiet(msg):
    pass


def run_check(pyret: str, docs: list, step=_quiet, clientsum: str = "", stuck: list | None = None, wip: str = "",
              writable: list | None = None) -> str:
    """pyret = the prior-year return, clientsum = the client summary (PDF / Word), wip = the work in progress to continue
    - '' = not picked; docs = the documents to read; stuck = documents the PDF reader got stuck on (left out).
    All are paths on the in-memory drive. writable = the places Chrome lets the app write: a folder ("/client/docs/X/",
    ending in /) or one file (a work in progress picked with Browse…) - the work in progress is saved only there."""
    places = list(writable or [])

    def can_write(path: str) -> bool:
        return any(path == w or (w.endswith("/") and path.startswith(w)) for w in places)
    form = dict(pyret=pyret or "", karbon="", clientsum=clientsum or "", utscreens="", wip=wip or "")
    readcache.clear()                                # a new Run check reads every file (Add more documents… reads only new ones)
    r = runcheck.run(form, [str(p) for p in docs], work_dir=WORK / "accounts", step=step, stuck_docs=list(stuck or []),
                     can_write=can_write)
    RUNS[r["token"]] = r
    step("saving the work in progress")
    save_work(r)
    step("done")
    return r["token"]


_adds = 0


def add_documents(token: str, docs: list, step=_quiet, stuck: list | None = None) -> str:
    """Add more documents… (Document inventory): documents that came later, added to a run that is open.

    How: the work so far is saved (as for Save work in progress), the run is worked out again with the old and the new
    documents - only the new files are actually read: what was read from the others is kept (core/readcache.py) - and the
    work is put back - the same way as *Continue where you left off* (core/runcheck.py open_work / put_back_work),
    so every correction, tick, comment, amount typed, Schedule C / E and K-1 package stays with its document (by its
    fingerprint), and everything that depends on the documents (the summaries, the form tabs ...) is worked out again.
    docs = every document of the run now (the old ones and the new ones); stuck = the ones the PDF reader got stuck on.
    The new run keeps saving to the same work-in-progress file. Returns the new run's token (the old run is closed)."""
    global _adds
    old = RUNS[token]
    _adds += 1
    folder = WORK / "add" / str(_adds)
    folder.mkdir(parents=True, exist_ok=True)
    wip = folder / "1040 Ultimate WIP - adding documents.json"
    wip.write_text(json.dumps(wip_mod.snapshot(old), default=str), encoding="utf-8")
    _, k1run = runcheck.k1_run(old)
    if k1run is not None:                               # the K-1 section's own work goes along (its file sits next to the work)
        wip_mod.save_k1(str(wip), [p for p, _ in k1run.get("files") or []], k1run.get("state"))
    form = dict(old["form"], wip=str(wip))
    new = runcheck.run(form, [str(p) for p in docs], work_dir=WORK / "accounts", step=step, stuck_docs=list(stuck or []),
                       can_write=lambda path: False)   # (the temporary copy is never the place to save)
    for d, ticked in runcheck.default_to_ai(new).items():   # a new document gets its AI tick as on a first run
        new["to_ai"].setdefault(d, ticked)
    for k in ("wip_path", "wip_bak_done", "wip_saved", "wip_error", "wip_loaded"):   # the same work-in-progress file as before
        new[k] = old.get(k)
    RUNS.pop(token, None)
    RUNS[new["token"]] = new
    step("saving the work in progress")
    save_work(new)
    step("done")
    return new["token"]


def password_candidates(names: list) -> list:
    """For each file name, the passwords to try (same rules as Run check: core/pdfutil.py - "PW-xxxx" in the name first)."""
    return [_candidates(Path(n)) for n in names]


def stuck_message(name: str, where: str, seconds: int) -> str:
    """The desktop's text for a PDF that makes the reader hang (same words, so the preparer knows what to do)."""
    return (f"\"{name}\": the PDF reader got stuck on {name} ({where or 'opening it'}) after {seconds} seconds. Open it in "
            "Acrobat and save a copy (File → Save As, or print it to Microsoft Print to PDF), then pick the copy.")

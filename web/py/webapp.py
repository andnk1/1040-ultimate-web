"""webapp.py - the browser app's start: Run check from the first page (web/index.html), and the stuck-PDF guard's texts.

The pages after Run check are answered by web/py/routes.py (the address table) and web/py/pages/ (one file per page).

Called from web/worker.js:
    run_check(pyret, docs, step, clientsum, stuck, wip, writable)  -> the run's token (Run check: core/runcheck.run),
                                                    then the work in progress saved into the client folder
    password_candidates(names)                      -> the passwords to try for each PDF (the stuck-PDF guard needs them)
    stuck_message(name, where, seconds)             -> the text shown when the PDF reader gets stuck on a file
"""
from __future__ import annotations

from pathlib import Path

from core import runcheck
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
    r = runcheck.run(form, [str(p) for p in docs], work_dir=WORK / "accounts", step=step, stuck_docs=list(stuck or []),
                     can_write=can_write)
    RUNS[r["token"]] = r
    step("saving the work in progress")
    save_work(r)
    step("done")
    return r["token"]


def password_candidates(names: list) -> list:
    """For each file name, the passwords to try (same rules as Run check: core/pdfutil.py - "PW-xxxx" in the name first)."""
    return [_candidates(Path(n)) for n in names]


def stuck_message(name: str, where: str, seconds: int) -> str:
    """The desktop's text for a PDF that makes the reader hang (same words, so the preparer knows what to do)."""
    return (f"\"{name}\": the PDF reader got stuck on {name} ({where or 'opening it'}) after {seconds} seconds. Open it in "
            "Acrobat and save a copy (File → Save As, or print it to Microsoft Print to PDF), then pick the copy.")

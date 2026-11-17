"""webapp.py - the browser app's Python side (Python runs in the browser tab with Pyodide - design\\web_version.md).

Today: read-only. Pick the files -> Run check -> the Summary page (document inventory + income summary), drawn with the
page template (templates\\summary.html) and the engine (core\\runcheck.py). Nothing is saved yet. The other pages come
one at a time (design\\conversion_plan.md).

Called from web\\worker.js:
    run_check(pyret, docs, step, clientsum)   -> token      (Run check: core\\runcheck.run)
    summary_html(token)            -> the Summary page as HTML
"""
from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core import runcheck
from core.inventory import ROUTE_LBL
from core.pl import MAP_LINES as PL_MAP_LINES
from core.py_return import SCHC_LINES, SCHE_LINES

APP = Path(__file__).resolve().parents[2]            # the app folder on the in-memory drive (core, templates ...)
WORK = Path("/work")                                 # split brokerage packages (in memory, gone when the tab closes)
RUNS: dict = {}


def _quiet(msg):
    pass


def run_check(pyret: str, docs: list, step=_quiet, clientsum: str = "") -> str:
    """pyret = the prior-year return, clientsum = the client summary (PDF / Word) - '' = not picked; docs = the documents
    to read. All are paths on the in-memory drive. The checks are core\\runcheck.check_form."""
    step("Run check received")
    form = dict(pyret=pyret or "", karbon="", clientsum=clientsum or "", utscreens="", wip="")
    r = runcheck.run(form, [str(p) for p in docs], work_dir=WORK / "accounts", step=step)
    RUNS[r["token"]] = r
    r["wip_path"] = None                             # nothing is saved yet (the work in progress comes with its own step)
    step("done")
    return r["token"]


# ---------------------------------------------------------------- the page (templates/summary.html, drawn by Jinja2)
def _url_for(endpoint: str, filename: str = "", **_kw) -> str:
    return "/static/" + filename if endpoint == "static" else "/" + endpoint


def _tab_name() -> str:
    try:
        from core.ai import settings
        return settings.tab_name()
    except Exception:  # noqa: BLE001
        return "AI Doc Review"


_ENV = None


def _env() -> Environment:
    global _ENV
    if _ENV is None:
        _ENV = Environment(loader=FileSystemLoader(str(APP / "templates")), autoescape=select_autoescape(["html", "htm", "xml"]))
        _ENV.globals.update(url_for=_url_for, AI_TAB_NAME=_tab_name())
    return _ENV


def summary_html(token: str) -> str:
    r = RUNS[token]
    r.setdefault("comments", {})
    inc, ded = runcheck.summaries(r)
    invrows = runcheck.inventory_rows(r)
    return _env().get_template("summary.html").render(
        r=r, token=token, ROUTE_LBL=ROUTE_LBL, inc=inc, ded=ded, MAPL=PL_MAP_LINES, k1=runcheck.k1_status(r),
        invrows=invrows, INV_SECS=runcheck.INV_SECS, fv=runcheck.form_view_data(r, inc, invrows, ded),
        SCHC=list(SCHC_LINES.items()), schc_json=json.dumps(r["schc"]),
        SCHE=list(SCHE_LINES.items()), sche_json=json.dumps(r.get("sche") or []))

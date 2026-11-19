"""k1.py - the K-1 section's pages: K-1 Verification (the run's K-1 PDFs), the K-1 Interpreter, the K-1 entry check, K-1 UT.

Moved from the desktop app's K-1 pages file (archive python-final, core/k1v/web.py): each address does what it did there.
The engine is core/k1v/ (the reader, the code list, the K-1 runs, K-1 UT's rules). In the browser app the K-1 pages open
inside the app (the desktop opened new browser tabs - conversion plan, question 3); each page has a "←" link back.

    /k1v/?for=<1040 run>    the client's K-1 run (made now if it has none yet): its K-1 PDFs + Add K-1 PDFs…, then open:
    /k1v/k1/<token>         K-1 Interpreter (entry guide, statement amounts, totals, Add to Income Summary)
    /k1v/verify/<token>     K-1 entry check: every K-1 item vs what was typed in UltraTax (the UT input screens print)
    /k1v/prep/<token>       K-1 UT: box E, corrected amounts, Bot / By hand, the UT data entry CSV, the by-hand list
    /k1v/                   the K-1 reader on its own (K-1 PDFs picked on the page; nothing goes to an income summary)

The K-1 run belongs to the client's 1040 run ("owner" = the 1040 run's token). What connects the two (on the desktop these
were "hooks" the 1040 app set):
    _added        the K-1 package -> the 1040 run (r["k1"]) - the only way K-1 amounts reach the income summary
    _save_state   the K-1 page's own work -> the K-1 work file next to the client's work in progress
    _people       the taxpayer / spouse SSN from the prior-year return (box E of each K-1 is matched by the last 4)
    _label        "2025 - Name 1234" from the work-in-progress file's name (the CSV's and the by-hand list's file names)
"""
from __future__ import annotations

import html
import re
import uuid
from pathlib import Path
from urllib.parse import parse_qs

from core import runcheck
from core.k1v import handoff, k1_codes, prep, ut_entry
from core.k1v import runs as k1runs
from core.k1v.codes_1120s import BOXES_1120S
from core.k1v.k1_parser import parse_pdf
from core.k1v.k1_rules import ORDER, RULES
from core.k1v.k1_summary import build_summary, write_xlsx
from core.k1v.screen_parser import parse_screens
from core.k1v.screen_verify import verify_screens
from core.k1v.verify1040_excel import write_verification_xlsx

from . import RUNS as RUNS_1040
from . import NotFound, Reply, data, file, page, render, save_k1_work, save_work

BASE = "/k1v"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _ctx(**kw):
    return dict(k1v_base=BASE, codes_1120s=BOXES_1120S, **kw)


def problem(msg: str, back: str = "") -> Reply:
    """A request the page can't do, with the reason (the desktop answered these with an error page, status 400).
    The reason sits in the first <p>: K-1 UT's download buttons show that text (templates/k1v/prep.html download())."""
    link = f'<p><a class="btn alt" href="{html.escape(back)}">&larr; Back</a></p>' if back else ""
    return page("<!doctype html><html><head><meta charset='utf-8'><link rel='stylesheet' href='/static/style.css'></head>"
                f"<body><div class='wrap'><h1>K-1</h1><p class='banner'>{html.escape(msg)}</p>{link}</div></body></html>", 400)


def _run(token: str) -> dict:
    run = k1runs.RUNS.get(token)
    if not run:
        raise NotFound("This K-1 run isn't open any more (the app was reloaded). Go back to the Summary and open it again.")
    return run


def _back(run) -> str:
    """Where the Interpreter's and the entry check's "←" link goes: the client's K-1 Verification page."""
    return f"{BASE}/?for={run['owner']}" if run.get("owner") else f"{BASE}/"


# ---------------------------------------------------------------- the connections to the client's 1040 run
def _added(owner: str, pkg: dict) -> bool:
    """Add to Income Summary: the K-1 package goes to the 1040 run (replacing an earlier one); the work in progress is saved."""
    r = RUNS_1040.get(owner)
    if r is None:
        return False
    r["k1"] = pkg
    save_work(r)
    return True


def _save_state(owner: str) -> None:
    """The K-1 page's own work (statement amounts, ticks, comments, corrections) -> the K-1 work file next to the client's."""
    r = RUNS_1040.get(owner)
    if r is None:
        return
    _, run = runcheck.k1_run(r)
    if run is not None:
        save_k1_work(r, [p for p, _ in run.get("files") or []], run.get("state"))


def _people(owner: str) -> dict:
    """K-1 UT: the taxpayer's / spouse's SSN from the prior-year return (box E of each K-1 is matched by the last 4)."""
    r = RUNS_1040.get(owner)
    if r is None:
        return {}
    if "_k1people" not in r:
        out = {}
        try:
            from core.people import read_people
            from core.readcache import remember
            pyret = r["form"].get("pyret")
            for p in (remember("people", pyret, lambda: read_people(pyret)) if pyret else []):
                key = {"Taxpayer": "tp", "Spouse": "sp"}.get(p.get("role"))
                if key and p.get("ssn"):
                    out[key] = p["ssn"]
        except Exception:  # noqa: BLE001 - no SSN found: the preparer types it on K-1 UT
            pass
        r["_k1people"] = out
    return r["_k1people"]


def _label(owner: str) -> str:
    """"2025 - Name 1234" (from the work-in-progress file's name)."""
    stem = Path((RUNS_1040.get(owner) or {}).get("wip_path") or "").stem
    return stem.replace("1040 Ultimate WIP", "").strip(" -") if stem.startswith("1040 Ultimate WIP") else ""


# ---------------------------------------------------------------- shared by the pages (moved unchanged)
def _recheck(run) -> None:
    """The K-1 entry check again (after a change to what counts: K-1s added, a copy choice, a box correction)."""
    if run.get("scr"):
        run["result"] = verify_screens(prep.for_check(run), run["scr"])


def _summary(k1s, state):
    """The Income Summary of the K-1s that count + "box_corr": {rid: amount} - the lines a K-1 UT box correction moves
    (the totals tab's Correction column starts from it)."""
    st = state or {}
    ks = prep.counted(k1s, st)
    s = build_summary(ks)
    s["box_corr"] = prep.summary_corr(ks, st.get("pcorr"), build_summary)[0]
    return s


def _report_ctx(run=None, error=None, filename=None, token=None):
    dicts = run["k1s"] if run else []
    state = (run or {}).get("state")
    return _ctx(k1s=dicts, rules=RULES, order=ORDER, summary=_summary(dicts, state),
                filename=filename or (run["k1name"] if run else None), error=error, static=False,
                codes=k1_codes.dropdown(), code_boxes=k1_codes.CODE_BOXES, token=token, owner=(run or {}).get("owner"),
                state=state, dups=prep.find_copies(dicts, (state or {}).get("dup")), plines=prep.plines_entries(state),
                back=_back(run) if run else f"{BASE}/")


def _prep_data(run):
    owner = run.get("owner")
    people = _people(owner) if owner else {}
    label = _label(owner) if owner else ""
    return prep.build(run, people, k1runs.file_ids(run), client=re.sub(r"^\d{4}\s*-\s*", "", label))


# ---------------------------------------------------------------- K-1 Verification (the run's page)
def home(query: str = ""):
    """?for=<1040 run>: that client's K-1 run (made now if it has none yet - the K-1 PDFs found among the client's
    documents were read by Run check). Without it: the K-1 reader on its own (pick K-1 PDFs on the page)."""
    q = parse_qs(query)
    owner, tab = (q.get("for") or [""])[0], (q.get("tab") or [None])[0]
    if not owner:
        return page(render("k1v/home.html", **_ctx(run=None, token=None, error=None, tab=tab, owner=None)))
    if owner not in RUNS_1040:
        raise NotFound("This run isn't open any more (the app was reloaded). Go back and click Run check again.")
    token, run = k1runs.run_for(owner)
    if not run:
        ut = RUNS_1040[owner].get("ut_path") or ""
        token, _, _ = k1runs.make_run([], ut or None, owner=owner)
        run = k1runs.RUNS[token]
    return page(render("k1v/home.html", **_ctx(run=run, token=token, error=None, tab=tab, owner=owner)))


def read_on_its_own(sent: dict):
    """The K-1 reader on its own: the form on /k1v/ (K-1 PDFs, a password, the UT input screens) -> a K-1 run with no 1040.
    sent = {"files": {field: [paths on the in-memory drive]}, "fields": {field: text}} (the frame copies the picked files
    onto the drive - web/index.html, the form submit)."""
    files, fields = (sent or {}).get("files") or {}, (sent or {}).get("fields") or {}
    fks = [p for p in files.get("k1pdf") or [] if p]
    scr = (files.get("scrpdf") or [""])[0]
    home_error = lambda msg: page(render("k1v/home.html", **_ctx(run=None, token=None, owner=None, tab=None, error=msg)))
    if not fks or not all(p.lower().endswith(".pdf") for p in fks):
        return home_error("Please choose the K-1 PDF(s).")
    run = {"k1name": " + ".join(Path(p).name for p in fks), "result": None, "manual": {}, "flags": {}, "scr": None, "scrname": None}
    pw = (fields.get("pdfpw") or "").strip()
    run["k1s"], problems = [], []
    for n, p in enumerate(fks):
        ks, pr, _ = k1runs.read_k1_files([(p, Path(p).name)], pw)
        for d in ks:
            d["page"] += 1000 * n
            for line in d["lines"]:                           # line ids follow the page number
                line.pop("lid", None)
            run["k1s"].append(prep.assign_lids(d))
        problems += pr
    run["problems"] = problems
    if not run["k1s"]:
        return home_error("; ".join(problems) if problems else "No Schedule K-1 pages found in the K-1 PDF(s).")
    run["n1065"] = sum(1 for k in run["k1s"] if k.get("form") == "1065")
    run["n1120"] = sum(1 for k in run["k1s"] if k.get("form") == "1120-S")
    if scr:
        try:
            run["scr"], run["scrname"] = parse_screens(scr), Path(scr).name
        except Exception as e:  # noqa: BLE001
            return home_error(f"Couldn't read the Input Screens PDF: {e}")
        if not run["scr"]["units"]:
            return home_error("No K-1 input screens (K1, K1-2 …) found in the Input Screens PDF — print UltraTax File > Print > "
                              "Input screens.")
        run["result"] = verify_screens(prep.counted(run["k1s"], None), run["scr"])
    token = uuid.uuid4().hex[:12]
    k1runs.RUNS[token] = run
    return page(render("k1v/home.html", **_ctx(run=run, token=token, error=None, tab=None, owner=None)))


def add_files(token: str, sent: dict):
    """Add K-1 PDFs… (a run opened from the 1040): the picked files are added to the run and every K-1 file is read again
    (the ones read before come from what was kept - core/readcache.py)."""
    run = _run(token)
    paths = [p for p in (sent or {}).get("paths") or [] if p and Path(p).is_file()]
    have = {p for p, _ in run.get("files") or []}
    new = [(p, Path(p).name) for p in paths if p.lower().endswith(".pdf") and p not in have]
    if new:
        k1runs._fill(run, (run.get("files") or []) + new)
        _recheck(run)
        if run.get("owner"):
            _save_state(run["owner"])
    return data(dict(ok=True, added=len(new), problems=run["problems"]))


# ---------------------------------------------------------------- the K-1 Interpreter
def interpreter(token: str, query: str = ""):
    """?tabs=1: the K-1s as tabs instead of one long page."""
    tabs = (parse_qs(query).get("tabs") or [""])[0] == "1"
    return page(render("k1v/report.html", **_report_ctx(_run(token), token=token), tabs=tabs))


def statement_amounts(token: str, sent: dict):
    """Statement amounts typed on the Interpreter (and the 11 S short / long ticks) -> the entry check runs again with them."""
    run = _run(token)
    d = sent or {}
    new, flags = d.get("manual") or {}, d.get("flags") or {}
    changed = new != (run.get("manual") or {}) or flags != (run.get("flags") or {})
    run["manual"], run["flags"] = new, flags
    if changed:
        _recheck(run)
    return data(dict(ok=True, changed=changed))


def totals(sent: dict):
    """The Interpreter's totals: the Income Summary of the K-1s that count, with the statement amounts."""
    d = sent or {}
    run = k1runs.RUNS.get(d.get("token") or "")
    return data(_summary(d.get("k1s") or [], (run or {}).get("state")))


def add_to_income_summary(token: str, sent: dict):
    """'Add to Income Summary': one package of the run's K-1 lines (amount read -> per document, a correction typed on the
    totals tab -> corrected amount) to the 1040 run that owns this K-1 run. Adding again replaces the package."""
    run = _run(token)
    if not run.get("owner"):
        return Reply("json", dict(ok=False, error="Open the K-1 page from the 1040 (K-1 box, Open K-1 Verification) to add "
                                                  "the K-1s."), status=400)
    d = sent or {}
    if isinstance(d.get("state"), dict):
        run["state"] = prep.keep_prep_keys(run.get("state"), d["state"])
    st = run.get("state") or {}
    skip = {p for p, m in prep.find_copies(run["k1s"], st.get("dup")).items() if not m["counted"]}      # a copy counts once
    k1s = [k for k in (d.get("k1s") or []) if k.get("form") in handoff.FORMS and k.get("page") not in skip]
    if not k1s:
        return Reply("json", dict(ok=False, error="No Form 1065 K-1s to add."), status=400)
    box_corr, box_rows = prep.summary_corr(k1s, st.get("pcorr"), build_summary)
    pkg = handoff.build_package(k1s, st.get("corr") or {}, build_summary(k1s), [n for _, n in run["files"]],
                                handoff.signature(run["k1s"], run.get("state")), k1runs.file_ids(run), box_corr, box_rows)
    if not _added(run["owner"], pkg):
        return Reply("json", dict(ok=False, error="The 1040 run is gone (the app was reloaded) — open the client again."),
                     status=400)
    _save_state(run["owner"])
    return data(dict(ok=True, k1s=pkg["n"], lines=len(pkg["rows"]), at=pkg["added"]))


def save_state(token: str, sent: dict):
    """The K-1 page's own work (statement amounts, 11 S / 11 ZZ ticks, Verified ticks, comments, UT numbers, corrections) -
    kept with the run and saved next to the client's work in progress."""
    run = _run(token)
    if isinstance(sent, dict):
        run["state"] = prep.keep_prep_keys(run.get("state"), sent)      # what K-1 UT saved is not the Interpreter's to change
        if run.get("owner"):
            _save_state(run["owner"])
    return data({"ok": True})


def interpreter_excel(sent: dict):
    """The Interpreter's Excel summary."""
    d = sent or {}
    k1s = d.get("k1s") or []
    if not k1s:
        return Reply("json", dict(error="No K-1 data"), status=400)
    content = write_xlsx(k1s, ut=d.get("ut"), pcomments=d.get("pc"), items=d.get("items"), filename=d.get("filename", ""),
                         corr=d.get("corr"))
    return file(content, (Path(d.get("filename") or "K-1").stem or "K-1") + "_Income_Summary.xlsx", XLSX)


# ---------------------------------------------------------------- the K-1 entry check (against the UT input screens)
NO_SCREENS = "No Input Screens PDF was read — go back and add the UltraTax Input Screens PDF."


def entry_check(token: str):
    run = _run(token)
    if not run["result"]:
        return problem(NO_SCREENS, _back(run))
    return page(render("k1v/verify.html", **_ctx(res=run["result"], k1name=run["k1name"], retname=run["scrname"], token=token,
                                                 manual=run.get("manual") or {}, flags=run.get("flags") or {},
                                                 back=_back(run))))


def entry_check_excel(token: str):
    run = _run(token)
    if not run["result"]:
        return problem(NO_SCREENS, _back(run))
    content = write_verification_xlsx(run["result"], run["k1name"], run["scrname"])
    return file(content, Path(run["scrname"] or "UltraTax").stem + "_K1_verification.xlsx", XLSX)


# ---------------------------------------------------------------- K-1 UT (spec design/k1_prep.md)
NO_TP = "Enter the taxpayer SSN (last 4) on K-1 UT first - box E is matched to it."


def k1_ut(token: str):
    run = _run(token)
    if not run.get("owner"):
        return problem("Open the K-1 page from the 1040 (K-1 box, Open K-1 Verification) for K-1 UT.", _back(run))
    return page(render("k1v/prep.html", **_ctx(token=token, owner=run["owner"], data=_prep_data(run))))


def k1_ut_save(token: str, sent: dict):
    """A change on K-1 UT (a corrected amount, a tick, count / don't count, the taxpayer / spouse SSN) - also used by the
    Interpreter for count / don't count. Saved in the K-1 work file; the entry check runs again."""
    run = _run(token)
    prep.save(run, sent or {})
    _recheck(run)
    if run.get("owner"):
        _save_state(run["owner"])
    return data(dict(ok=True, data=_prep_data(run)))


def ut_export(token: str):
    """Export for UT data entry: the CSV the separate UT Data Entry app reads (its format: design/ut_export_format.md)."""
    run = _run(token)
    d = _prep_data(run)
    if not d["people"].get("tp"):
        return problem(NO_TP)
    if not prep.export_rows(d):
        return problem("Nothing to export - no K-1 is Ready.")
    label = _label(run.get("owner")) if run.get("owner") else ""
    return file(prep.export_csv(d), ("UT data entry K-1 " + label).strip() + ".csv", "text/csv")


def by_hand(token: str, fmt: str):
    """The lines to enter by hand in UltraTax (core/k1v/ut_entry.py), Ready K-1s, in the page's order.
    fmt "xlsx" = the Excel file; "print" = the same list as a page in a new tab, to print or save as PDF with Chrome
    (the desktop drew the PDF itself; MuPDF.js in the browser can't turn HTML into a PDF - conversion plan, question 5)."""
    if fmt not in ("xlsx", "print") or not ut_entry.on():
        raise NotFound("No such list.")
    run = _run(token)
    d = _prep_data(run)
    if not d["people"].get("tp"):
        return problem(NO_TP)
    items = d["hand"]
    if not items:
        return problem("Nothing to enter by hand - no Ready K-1 has a by-hand line.")
    label = _label(run.get("owner")) if run.get("owner") else ""
    m = re.match(r"(\d{4})\s*-\s*", label)
    year = m.group(1) if m else next((k["year"] for k in d["k1s"] if k.get("year")), "")
    h = ut_entry.head(d["client"], year, items)
    name = ("UT by hand K-1 " + (label or str(year))).strip()
    if fmt == "xlsx":
        return file(ut_entry.hand_xlsx(items, h), name + ".xlsx", XLSX)
    return file(ut_entry.hand_html(items, h).encode("utf-8"), name + ".html", "text/html", inline=True)

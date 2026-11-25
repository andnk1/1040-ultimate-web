"""scenario.py - the fixed list of edits used to check the Summary's saves against the archive (python-final).

The same edits are applied to a sample client in the archive (tools/parity/make_reference.py, through the desktop app's own
addresses) and in this app (tests/harness.py check_reference, through web/py/routes.py). What both keep must be the same:
the saved work in progress, the income and deduction summary (corrected amounts, flags, totals) - and again after the saved
work is opened (Continue where you left off).

This file is plain Python with no import from either app: it only reads the run (a dict) both apps build the same way.
"""
from __future__ import annotations

import json
import re


def edits(r: dict, inc: dict, ded: dict) -> list:
    """[(address, what the page sends)] - one save of each kind the Summary has (step 2 of design/conversion_plan.md).
    Chosen from the run itself, the same way in both apps, so any sample client works. {token} = the run's token."""
    rows = [x for s in inc["sections"] for x in s["rows"]]
    # the corrected amount goes on a line still typed on the summary (2026-11-24: a document the program read is corrected
    # on its own screen - core/income.py where_to_correct): a crypto report's row, a Schedule C / E box result, a not-read row
    fam = {d["file"]: d.get("family") for d in r["inv"]["docs"]}
    open_rows = [x for x in rows if x.get("id") and not x.get("added") and not x.get("inv") and not x.get("excluded")
                 and (x.get("status") == "none" or x.get("sche") is not None or x.get("schc") is not None
                      or fam.get(x.get("file")) == "koinly")]
    with_doc = sorted(open_rows, key=lambda x: x.get("doc_cy") is None)      # one with a per-document amount first
    docs = [d for d in r["inv"]["docs"] if d.get("family") != "pyreturn"]
    first_sec = inc["sections"][0]["key"]
    out = []
    if with_doc:                                       # a corrected amount (typed over), with a note
        x = with_doc[0]
        out.append(("/edits/{token}", {x["id"]: {"cy": round((x["doc_cy"] or 0) + 100, 2), "note": "corrected in the test"}}))
        out.append(("/marks/{token}", {"inc|" + x["id"]: True, "n|inc|" + x["id"]: "ticked in the test"}))
    out.append(("/added/{token}", [{"id": "t1", "sec": first_sec, "doc": "Added in the test", "cy": 1234.5, "fit": None,
                                     "note": "+ line"}]))
    out.append(("/carryadd/{token}", [{"id": "c1", "item": "Carryover added in the test", "activity": "", "amount": 500,
                                        "note": ""}]))
    out.append(("/comments/{token}", {"client": "Return comment from the test", "recv": {}, "recv_ok": {},
                                      "recv_note": "received? note"}))
    inv = dict(verified={}, amt={}, notes={}, free=[])
    if docs:
        inv["verified"][docs[0]["did"]] = True
        inv["notes"][docs[-1]["did"]] = "inventory note from the test"
    not_read = [d for d in docs if d.get("read") not in ("read", "partial")]
    if not_read:                                       # an amount for a document the program didn't read
        inv["amt"][not_read[0]["did"]] = {"cy": "2,500.40", "sec": first_sec}
    inv["free"].append({"id": "f1", "name": "Free line from the test", "issuer": "Someone", "cy": "$1,000", "sec": first_sec,
                        "note": "free line", "verified": True})
    out.append(("/inventory/{token}", inv))
    out.append(("/invnote/{token}", {"id": "inv|free|f1", "note": "note typed on the summary"}))
    if docs:
        out.append(("/toai/{token}", {docs[0]["path"]: True}))
    if with_doc:                                       # the corrected line again: Re-confirm keeps the correction
        out.append(("/edits/{token}/confirm", {"id": with_doc[0]["id"]}))
    return out


# ---------------------------------------------------------------- step 3: the rest of the Summary
# A made-up P&L (no client data) for the Schedule C box's Add P&L…
PL_CSV = ("Demo Business LLC\nProfit and Loss\n,Total\nIncome,\nSales,50000.00\nTotal Income,50000.00\nExpenses,\n"
          "Advertising,1200.00\nOffice supplies,300.00\nTotal Expenses,1500.00\nNet Income,48500.00\n")


def more_edits(r: dict, post, pl_path: str) -> None:
    """Step 3's saves, through post(address, what the page sends) -> the reply's data. pl_path = PL_CSV written to a file.
    Form tab correction (W-2 box 1), a UT summary field, the Schedule C box with a P&L read by Add P&L…, the Schedule E box."""
    w2 = [d for d in r["inv"]["docs"] if d.get("family") == "w2"]
    if w2:
        post("/formview/{token}/w2", {f"{w2[0]['did']}#0": {"b1": 12345.67}})
    post("/ut/{token}", {"agi": "100000", "fs": "MFJ"})
    pl = post("/pl/{token}", {"path": pl_path})
    biz = {"name": "", "py": None, "cy": {"1": "50000", "8": "1200", "18": "300"}, "pl": pl, "calculated": True,
           "totals": {"31": 48500}, "final": {"1": 50000, "8": 1200, "18": 300}, "total_only": None}
    post("/schc/{token}", list(r.get("schc") or []) + [biz])
    prop = {"name": "1 Test Street", "py": None, "cy": {"3": "24000", "9": "3000"}, "info": {"type": "1", "fair_days": 365},
            "calculated": True, "totals": {"20": 3000, "21": 21000, "net": 21000}}
    post("/sche/{token}", list(r.get("sche") or []) + [prop])


def downloads(r: dict, get) -> dict:
    """Every download of the Summary through get(address) -> (file name, bytes), made comparable: an Excel file as its
    cells (sheet by sheet), a CSV as its text."""
    n_biz, n_prop = len(r.get("schc") or []), len(r.get("sche") or [])
    addresses = ["/income/{token}/excel", "/sche/{token}/template.xlsx", "/sche/template.xlsx"]
    addresses += [f"/schc/{{token}}/{n_biz - 1}/{w}.csv" for w in ("workpaper", "other_expenses", "book_tax")] if n_biz else []
    addresses += [f"/sche/{{token}}/{n_prop - 1}/workpaper.csv"] if n_prop else []
    out = {}
    for a in addresses:
        name, content = get(a)
        out[a.replace("{token}", "<run>")] = dict(file=name, content=_cells(content) if name.endswith(".xlsx")
                                                  else content.decode("utf-8").replace("\r\n", "\n"))
    return out


def _cells(xlsx: bytes) -> dict:
    """An Excel file's cell values, sheet by sheet (what the preparer sees - not the file's bytes, which hold its time)."""
    import io
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(xlsx))
    return {ws.title: [[c for c in row] for row in ws.iter_rows(values_only=True)] for ws in wb.worksheets}


# ---------------------------------------------------------------- step 5: the K-1 pages
def k1_pages(r: dict, k1runs, open_page, post, get, post_file, summaries) -> dict:
    """The K-1 pages on a fresh run (no K-1s added yet), the same in both apps, through their own addresses:
    K-1 Verification opened from the 1040, a statement amount typed on the Interpreter, the totals, K-1 UT (box E matched to
    the taxpayer, a corrected amount, a tick), Add to Income Summary, then every K-1 download.
    k1runs = the app's K-1 runs (run_for, RUNS); open_page(address) -> status; post(address, body) -> the reply's data;
    get / post_file -> (file name, bytes); summaries(r) -> (income, deductions)."""
    out = {}
    assert open_page("/k1v/?for={token}") == 200
    tok, run = k1runs.run_for(r["token"])
    out["read"] = dict(files=[n for _, n in run["files"]], problems=run["problems"], k1s=run["k1s"], n1065=run["n1065"],
                       n1120=run["n1120"])
    if not run["k1s"]:
        return out
    k = run["k1s"][0]
    out["manual"] = post(f"/k1v/manual/{tok}", {"manual": {str(k["page"]): [["13W", "75"]]}, "flags": {}})
    out["entry_check"] = run.get("result")
    out["totals"] = post("/k1v/summary", {"k1s": run["k1s"], "token": tok})
    e4 = re.sub(r"\D", "", k.get("E") or "")[-4:] or "1234"
    d = post(f"/k1v/prep/{tok}/save", {"people": {"tp": e4}})["data"]
    row = next((q for x in d["k1s"] for q in x["rows"] if q.get("kind") == "line" and isinstance(q.get("amt"), (int, float))
                and q.get("amt")), None)
    if row:
        d = post(f"/k1v/prep/{tok}/save", {"pcorr": {row["id"]: "777"}})["data"]
        d = post(f"/k1v/prep/{tok}/save", {"pticks": {row["id"]: True}})["data"]
    out["k1_ut"] = d
    ks = [x for x in run["k1s"] if x.get("form") == "1065"]
    state = {"items": {"x": {"v": True, "c": "seen in the test"}}}
    if ks:
        out["add"] = post(f"/k1v/add/{tok}", {"k1s": ks, "state": state})
        inc, ded = summaries(r)
        out["after_add"] = dict(package=r.get("k1"), income=inc, deductions=ded)
    out["state"] = run.get("state")
    dl = {}
    wanted = ([f"/k1v/prep/{tok}/export"] if d.get("ready") else []) + ([f"/k1v/prep/{tok}/hand/xlsx"] if d.get("hand") else [])
    wanted += [f"/k1v/verify/{tok}/excel"] if run.get("result") else []
    for a in wanted:
        name, content = get(a)
        key = a.replace(tok, "<k1run>").lstrip("/")             # (no leading "/": normalize() would shorten it to a name)
        dl[key] = dict(file=name, content=_cells(content) if name.endswith(".xlsx")
                       else content.decode("utf-8").replace("\r\n", "\n"))
    name, content = post_file("/k1v/excel", {"k1s": run["k1s"], "ut": {}, "pc": {}, "items": {}, "filename": run["k1name"],
                                             "corr": {}})
    dl["k1v/excel"] = dict(file=name, content=_cells(content))
    out["downloads"] = dl
    return out


# ---------------------------------------------------------------- step 4: Verify return
def verify_page(r: dict, ut_path: str, open_page, post, save_review, snapshot, master_items) -> dict:
    """Verify return, the same in both apps, through their own addresses. The run starts without the UT print (the browser
    app's first page has no field for it - it is picked on Verify return), then: the page opened, the UT input screens picked
    and checked, a tick + comment on the first and the last line of the checks, the checklist (first line done with a note,
    a line for this return only, a line for every client), Save review (Excel).
    open_page(address) -> (status, html); post(address, body) -> the reply's data; save_review() -> (file name, bytes);
    snapshot(r) -> the work in progress; master_items() -> the master checklist."""
    import html as html_mod
    r["ut_scr"], r["ut_path"], r["ut_error"] = None, "", None
    r["form"]["utscreens"] = ""
    out = {}
    status, _ = open_page("/verify/{token}")
    assert status == 200
    out["run"] = post("/verify/{token}/run", {"path": "", "ut": ut_path})
    status, page = open_page("/verify/{token}")
    assert status == 200
    keys = list(dict.fromkeys(html_mod.unescape(k) for k in re.findall(r'data-mk="(v\|[^"]+)"', page)))
    marks = {}
    for k in keys[:1] + keys[-1:]:
        marks[k], marks["n|" + k] = True, "checked in the test"
    out["marks"] = post("/marks/{token}", marks)
    out["lines"] = len(keys)
    cl = json.loads(re.search(r"let CL = (.*);$", page, re.M).group(1))
    if cl:
        cl[0].update(done=True, note="done in the test")
    cl.append(dict(text="Line for this return (test)", done=False, stays=False, master=False, note=""))
    cl.append(dict(text="Line for every client (test)", done=True, stays=True, master=False, note="kept"))
    out["checklist"] = {k: v for k, v in post("/verify/{token}/checklist", cl).items() if k != "kept"}
    out["master"] = master_items()
    name, content = save_review()
    out["review"] = dict(file=name, cells=_cells(content))
    out["work"] = snapshot(r)
    return out


# ---------------------------------------------------------------- what is compared
_PATHISH = re.compile(r"^(?:[A-Za-z]:[\\/]|/|\\\\).+")
_CLOCK = re.compile(r"\d{4}-\d\d-\d\d \d\d:\d\d(:\d\d)?")      # "2026-11-17 17:19" - a time stamp
# the by-hand list's heading "Tax year 2025 · 11/18/2026 · 169 items": the middle date is the day the list was made
_MADE_ON = re.compile(r"^(Tax year \d{4}\W+)\d{1,2}/\d{1,2}/\d{4}(\W)")
# the review Excel's Checklist heading "<UT print> · saved 2026-11-24 15:23": when the review was made
_SAVED_AT = re.compile(r"( · saved )\d{4}-\d\d-\d\d \d\d:\d\d$")


def normalize(value):
    """What both apps keep, made comparable: file paths become file names (the archive ran from C:\\..., this app from its
    own folders); clock times are left out (when the work was saved, when the K-1s were added, when the review Excel was
    made - its Checklist heading), and so is the day the
    by-hand list was made (its heading - otherwise the check fails on any day but the one the reference was made);
    lock / kept are left out - new in the browser app (2026-11-24: where a read document's row is corrected, and a correction
    saved before that lock); src_path / src_page are left out - new in the browser app (each summary row's link to the page its amount was read on,
    2026-11-17), the archive has no such field. Everything else must be the same."""
    def walk(v):
        if isinstance(v, dict):
            return {walk(k) if isinstance(k, str) else k: walk(x) for k, x in v.items()
                    if k not in ("saved", "src_path", "src_page", "lock", "kept") and not (isinstance(x, str) and _CLOCK.fullmatch(x))}
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, str) and _PATHISH.match(v):
            return v.replace("\\", "/").rsplit("/", 1)[-1]
        if isinstance(v, str) and _MADE_ON.match(v):
            return _MADE_ON.sub(r"\1(date)\2", v)
        if isinstance(v, str) and _SAVED_AT.search(v):
            return _SAVED_AT.sub(r"\1(time)", v)
        return v
    return walk(json.loads(json.dumps(value, default=str)))


def differences(expected, now, where="", out=None, limit=40):
    """The places where two normalized values differ: ["path: expected -> now"]."""
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(expected, dict) and isinstance(now, dict):
        for k in sorted(set(expected) | set(now), key=str):
            if k not in now:
                out.append(f"{where}/{k}: only in the archive")
            elif k not in expected:
                out.append(f"{where}/{k}: only now")
            else:
                differences(expected[k], now[k], f"{where}/{k}", out, limit)
    elif isinstance(expected, list) and isinstance(now, list) and len(expected) == len(now):
        for i, (a, b) in enumerate(zip(expected, now)):
            differences(a, b, f"{where}[{i}]", out, limit)
    elif expected != now:
        out.append(f"{where}: {str(expected)[:120]} -> {str(now)[:120]}")
    return out

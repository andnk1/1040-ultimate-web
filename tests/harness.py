"""harness.py - runs one test case (a fake client in tests\\samples\\<case>) through the 1040's own code and lists what
the program reads, one row per value. The same code runs here on this computer's Python (pytest, PyMuPDF as the PDF engine)
and inside the browser app (the "Check against the answer key" button, MuPDF.js as the PDF engine):

  Documents  - per document: type, issuer, tax year, read status, number of forms, then every box the reader reads
               (W-2 / 1098 by box as on the form tabs; K-1s by line from the K-1 section; other forms by the reader's fields)
  Summary    - the income / deduction summary lines (per document) and their federal withholding
  UT check   - Verify return with the UT input screens: the result per line, then the UT entries with no document

Row = (File, Form #, What, value). Values: amounts rounded to the cent, text as printed, yes / no for check boxes,
"blank" for an empty box (never 0). Nothing is saved (Run check itself saves nothing; split packages go to a temporary folder).
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_DIR = HERE.parent
SAMPLES = HERE / "samples"
KEY_NAME = "answer_key.xlsx"
REF_NAME = "archive_reference.json"     # the archive's results (tools/parity/make_reference.py)
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR / "web" / "py"))         # the pages' Python (web/py/routes.py, web/py/pages/)

import core.wip as _wip                                  # noqa: E402
_wip.save = lambda r: None                               # a test never writes a work in progress (the desktop's rule)

ROLES = ("Document", "Prior-year return", "UT input screens", "Current-year return", "Leave out")
_TMP = None


def _work() -> Path:
    """A temporary folder for the brokerage packages Run check splits by account (made once per test session)."""
    global _TMP
    if _TMP is None:
        _TMP = Path(tempfile.mkdtemp(prefix="u1040_test_"))
    return _TMP


# ---------------------------------------------------------------- files of a case and their role
def case_dirs() -> list[Path]:
    return sorted(p for p in SAMPLES.iterdir() if p.is_dir()) if SAMPLES.is_dir() else []


def case_files(case: Path) -> list[Path]:
    return sorted((p for p in case.iterdir() if p.is_file() and not p.name.startswith(("~$", "."))
                   and p.name not in (KEY_NAME, REF_NAME)), key=lambda p: p.name.lower())


def guess_roles(case: Path) -> dict:
    """First guess for a new case (the preparer can change it on the key's Files sheet): the UT input screens print, the
    prior-year return (the earliest 1040), a later 1040 = the current-year return, work-in-progress files left out."""
    from core.inventory import return_year
    from core.pdfutil import open_pdf, page_text
    from core.runcheck import looks_like_1040
    from core.utscreens import looks_like_ut_screens, read_ut_screens
    roles, returns, uts = {}, [], []
    for p in case_files(case):
        roles[p.name] = "Document"
        if p.suffix.lower() in (".json", ".bak"):
            roles[p.name] = "Leave out"
        elif p.suffix.lower() == ".pdf":
            try:
                if looks_like_ut_screens(str(p)):            # (a K-1 can pass this check too - the one with most entries wins)
                    ut = read_ut_screens(str(p))
                    uts.append((len(ut.get("entries") or []) + len(ut.get("rents") or []), p.name))
                elif looks_like_1040(str(p)):
                    doc, _ = open_pdf(p)
                    with doc:
                        yr = return_year(" ".join(page_text(doc, i) for i in range(min(len(doc), 3))))
                    returns.append((yr or 9999, p.name))
            except Exception:  # noqa: BLE001
                pass
    if uts:
        roles[max(uts)[1]] = "UT input screens"
    for i, (_, name) in enumerate(sorted(returns)):
        roles[name] = "Prior-year return" if i == 0 else "Current-year return"
    return roles


# ---------------------------------------------------------------- one run through the app
def page(method: str, url: str, sent=None):
    """One address of the pages, as the page frame sends it (web/py/routes.py) -> the reply (a dict: kind, status, body ...).
    The run must be open: open_run(r)."""
    import routes
    return routes.handle(method, url, json.dumps(sent) if sent is not None else "")


def open_run(r: dict) -> dict:
    """Makes a run Run check gave known to the pages (as the browser app does after Run check)."""
    from pages import RUNS
    RUNS[r["token"]] = r
    return r


class Reply:
    """A page's answer as the tests read it (the desktop's tests used Flask's test client: status_code, data, headers ...)."""
    def __init__(self, d: dict):
        self.kind, self.status_code, body = d["kind"], d["status"], d["body"]
        self.data = body if isinstance(body, bytes) else (json.dumps(body) if d["kind"] == "json" else str(body)).encode("utf-8")
        self.json = body if d["kind"] == "json" else None
        self.headers = {"Content-Disposition": f'attachment; filename="{d["filename"]}"'} if d["kind"] == "file" else {}

    def get_data(self, as_text: bool = False):
        return self.data.decode("utf-8") if as_text else self.data

    def get_json(self):
        return self.json


class Client:
    """The pages' addresses called the way the page frame calls them (web/py/routes.py) - for the tests that drove the desktop
    app's pages through Flask's test client. post("/run", data=...) = Run check on the first page (web/py/webapp.py)."""
    def get(self, url: str) -> Reply:
        return Reply(page("GET", url))

    def post(self, url: str, json=None, data=None) -> Reply:   # noqa: A002 - Flask's names
        if url == "/run":
            from core import runcheck
            docs = [d["path"] for d in __import__("json").loads(data.get("docs") or "[]") if d.get("on", True)]
            form = {k: data.get(k, "") for k in ("pyret", "karbon", "clientsum", "utscreens", "wip")}
            r = open_run(runcheck.run(form, docs, work_dir=_work() / "accounts"))
            rep = Reply(dict(kind="html", status=302, body="", filename=""))
            rep.headers["Location"] = f"/summary/{r['token']}"
            return rep
        return Reply(page("POST", url, json if json is not None else {}))


class App:
    """What the K-1 tests used from the desktop app: its runs, the K-1 runs, the K-1 box, the summaries, a test client."""
    def __init__(self):
        from core import runcheck
        from core.k1v import runs as k1runs
        from pages import RUNS
        self.RUNS, self.k1v_web, self.k1_status, self._summaries = RUNS, k1runs, runcheck.k1_status, runcheck.summaries
        self.app = self

    def test_client(self) -> Client:
        return Client()


def _app() -> App:
    return App()


def run_case(case: Path, roles: dict, add_k1: bool = True) -> dict:
    """Run check on the case, as the first page does it (core/runcheck.run), and returns the run + what the K-1 section read."""
    from core import runcheck
    pick = lambda role: next((str(case / n) for n, r in roles.items() if r == role and (case / n).is_file()), "")
    docs = [str(case / n) for n, r in roles.items() if r == "Document" and (case / n).is_file()]
    form = dict(pyret=pick("Prior-year return"), karbon="", clientsum="", utscreens=pick("UT input screens"), wip="")
    try:
        r = runcheck.run(form, docs, work_dir=_work() / "accounts")
    except runcheck.Problem as e:
        raise RuntimeError(f"Run check failed for {case.name}: {e}") from e
    k1 = []
    _, run = runcheck.k1_run(r)
    if run:                                                    # each K-1 with the file it came from (pages 1001+ = 2nd file ...)
        names = [Path(p).name for p, _ in run["files"]]
        for k in run["k1s"]:
            i = k["page"] // 1000
            k1.append((names[i] if i < len(names) else "", k))
    r["_test_k1"] = k1
    if add_k1:
        add_k1s(r)
    return r


def add_k1s(r: dict, corr: dict | None = None) -> None:
    """What "Add to Income Summary" on the K-1 page does, with no statement amounts typed: the K-1 package to the 1040 run."""
    from core import runcheck
    from core.k1v import handoff, runs as k1runs
    from core.k1v.k1_summary import build_summary
    _, run = runcheck.k1_run(r)
    if not run:
        return
    k1s = [k for k in run["k1s"] if k.get("form") in handoff.FORMS]
    if k1s:
        r["k1"] = handoff.build_package(k1s, corr or {}, build_summary(k1s), [n for _, n in run["files"]],
                                        handoff.signature(run["k1s"], run.get("state")), k1runs.file_ids(run))


# ---------------------------------------------------------------- values
def norm(v):
    """A value as the key holds it."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return "blank"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    if isinstance(v, (list, tuple)):
        return " / ".join(str(norm(x)) for x in v) or "blank"
    return re.sub(r"\s*\n\s*", " / ", str(v)).strip()


def same(a, b) -> bool:
    a, b = norm(a), norm(b)
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) < 0.005
    if isinstance(a, float) or isinstance(b, float):       # a number typed as text in Excel ("1,234.50")
        try:
            return abs(float(str(a).replace(",", "")) - float(str(b).replace(",", ""))) < 0.005
        except ValueError:
            return False
    return str(a) == str(b)


def _flat(prefix: str, v, out: list):
    if isinstance(v, dict):
        for k, x in v.items():
            _flat(f"{prefix}.{k}" if prefix else str(k), x, out)
    elif isinstance(v, (list, tuple)) and v and any(isinstance(x, (dict, list, tuple)) for x in v):
        for i, x in enumerate(v):
            _flat(f"{prefix}[{i + 1}]", x, out)
    else:
        out.append((prefix, v))


# ---------------------------------------------------------------- sheet 1: per document
def _fv_label(form: str, k: str) -> str:
    """A form-tab row key -> words (W-2 / 1098)."""
    from core.formview import DEFS
    for s in DEFS[form]["sections"]:
        for x in s.get("rows") or []:
            if x["k"] == k:
                return f'Box {x["box"]} {x["label"]}' + (f" ({x['k'][3:]})" if x["k"].startswith("b13") else "")
    names = dict(ssn="Box a Employee's SSN", ein="Box b Employer EIN", er="Box c Employer name", er_addr="Box c Employer address",
                 ctl="Box d Control number", ee="Box e Employee name", ee_addr="Box f Employee address",
                 ln="Lender", br="Borrower", acct="Account number", b11="Box 11 Mortgage acquisition date")
    if k in names:
        return names[k]
    m = re.fullmatch(r"b(12|14|10):(.+)", k)
    if m:
        return f"Box {m.group(1)} {m.group(2)}"
    m = re.fullmatch(r"st:(.+):(15|16|17)", k)
    if m:
        return f"State {m.group(1)} box {m.group(2)}"
    m = re.fullmatch(r"lc:(.+):(18|19)", k)
    if m:
        return f"Local {m.group(1)} box {m.group(2)}"
    return k


SKIP_DETAIL = {"w2": {"boxes", "w2"}, "1098": {"boxes"}}


def rows_documents(r: dict) -> list:
    import core.formview as fv
    out = []
    for d in r["inv"]["docs"]:
        if d.get("family") == "pyreturn":
            continue
        f = d["file"]
        p = d.get("parsed")
        out += [(f, "", "Type", d.get("doc_type")), (f, "", "Issuer", d.get("issuer")), (f, "", "Tax year", d.get("year")),
                (f, "", "Program read", d.get("read") or "none")]
        fam = d.get("family")
        if fam in fv.FORMS:
            forms = fv.forms_of(d, fam)
            out.append((f, "", "Forms read", len(forms)))
            for i, one in enumerate(forms):
                for k, v in fv.FORMS[fam][0](one).items():
                    out.append((f, i + 1, _fv_label(fam, k), v))
        k1s = [k for fn, k in r.get("_test_k1") or [] if fn == f]
        if k1s:
            out.append((f, "", "Forms read", len(k1s)))
            for i, k in enumerate(k1s):
                for key in ("form", "year", "name", "ein", "final", "amended", "ptp", "G", "H1", "I1", "M"):
                    if key in k:
                        out.append((f, i + 1, f"K-1 {key}", k[key]))
                for kk, v in (k.get("L") or {}).items():
                    out.append((f, i + 1, f"L {kk}", v))
                for ln in k.get("lines") or []:
                    out.append((f, i + 1, f'Line {ln.get("key") or ln.get("box")}', "STMT" if ln.get("stmt") and ln.get("amt") is None else ln.get("amt")))
        if isinstance(p, list):                                # the old K-1 reader (one dict per K-1)
            out.append((f, "", "Forms read", len(p)))
            for i, k in enumerate(p):
                out.append((f, i + 1, "K-1 name", k.get("name")))
                for kk, v in sorted((k.get("amounts") or {}).items()):
                    out.append((f, i + 1, f"amounts.{kk}", v))
        elif isinstance(p, dict) and fam not in fv.FORMS and d.get("route") != "k1v":
            flat = []
            _flat("", {k: v for k, v in (p.get("detail") or {}).items() if k not in SKIP_DETAIL.get(fam, ())}, flat)
            for k, v in flat:
                out.append((f, "", k, v))
            for k, v in sorted((p.get("amounts") or {}).items()):
                out.append((f, "", f"amounts.{k}", v))
            for sec, parts in sorted((p.get("parts") or {}).items()):
                for lb, v in parts:
                    out.append((f, "", f"part {sec} · {lb}", v))
            if p.get("fit"):
                out.append((f, "", "Federal withholding", p["fit"]))
    return _unique(out)


def _k1_file(r: dict, doc: str) -> str:
    """The K-1 file a K-1 section line ("K-1 <name>" or "K-1 page 1001") came from (lines carry it as "k1v:<file>")."""
    for f, k in r.get("_test_k1") or []:
        if (k.get("name") and k["name"] in doc) or re.search(r"\bpage " + str(k["page"]) + r"\b", doc):
            return f
    return "(K-1 section)"


# ---------------------------------------------------------------- sheet 2: income / deduction summary (per document)
def rows_summary(r: dict) -> list:
    from core.runcheck import summaries
    inc, ded = summaries(r)
    out = []
    for title, summ in (("Income", inc), ("Deduction", ded)):
        for s in summ["sections"]:
            for x in s["rows"]:
                if x.get("added") and not x.get("inv"):
                    continue
                f = x.get("file") or ""
                if f.startswith("k1v:"):
                    f = f[4:] or _k1_file(r, x["doc"])
                elif x.get("sche") is not None:
                    f = "(Schedule E box)"
                elif x.get("schc") is not None:
                    f = "(Schedule C box)"
                what = f'{title} · {s["label"].replace("Total ", "")} · {x["doc"]}' + (" · memo" if x.get("memo") else "")
                out.append((f, "", what, x.get("doc_cy")))
                if x.get("doc_fit"):
                    out.append((f, "", what + " · Fed. w/h", x["doc_fit"]))
    return _unique(out)


# ---------------------------------------------------------------- sheet 3: Verify return against the UT input screens
ENTRY = {"ok": "ok", "diff": "different", "not entered": "not entered", "wrong line": "entered on another line"}


def rows_ut(r: dict) -> list:
    if not r.get("ut_scr"):
        return []
    import core.formview as fv
    from core.runcheck import summaries
    from core.utscreens import doc_verify
    inc, _ = summaries(r)
    ut = doc_verify(inc, fv.effective_docs(r), r["ut_scr"], r.get("sche"), r.get("schc"))
    out = []
    for l in ut["lines"]:
        res = [ENTRY.get(l["entry"], l["entry"])]
        n = l.get("ut_note") or ""
        if re.search(r"entered in \d+ pieces", n):
            res.append("entered in pieces")
        if "entered once on" in n:
            res.append("one UT entry for several lines")
        m = re.search(r"8949 box (\S+) in UT", n)
        if m:
            res.append(f"8949 box {m.group(1)} in UT")
        f = l.get("file") or ("(Schedule E box)" if l["cat"] == "sche" else "(Schedule C box)" if l["cat"] == "schcl" else "")
        if f.startswith("k1v:"):
            f = f[4:] or _k1_file(r, l["doc"])
        out.append((f, "", f'{l["group"]} · {l["doc"]} · {l["box"]}', " · ".join(res)))
    file = Path(r.get("ut_path") or "").name or "(UT print)"
    for b in ut["back"]:
        what = "UT entry with no document · " + " · ".join(str(b.get(k)) for k in ("screen", "label", "what") if b.get(k)) + \
               (f' · p. {b["page"]}' if b.get("page") else "")
        out.append((file, "", what, b.get("amount")))
    return _unique(out)


def _unique(rows: list) -> list:
    """(File, Form #, What) must be unique - a second row with the same words gets " (2)"."""
    seen, out = {}, []
    for f, n, w, v in rows:
        k = (f, str(n), w)
        seen[k] = seen.get(k, 0) + 1
        out.append((f, n, w if seen[k] == 1 else f"{w} ({seen[k]})", v))
    return out


SHEETS = (("Documents", rows_documents), ("Summary", rows_summary), ("UT check", rows_ut))


def read_all(case: Path, roles: dict) -> dict:
    """{sheet name: [(File, Form #, What, value)]} for a case."""
    r = run_case(case, roles)
    with contextlib.redirect_stdout(io.StringIO()):
        out = {name: fn(r) for name, fn in SHEETS}
    out["labels"] = label_changes(r)                       # (not a sheet: the intended differences for compare)
    return out


# ---------------------------------------------------------------- the answer key (answer_key.xlsx per case)
COLS = ("File", "Form #", "What", "Expected", "Checked")
HELP = {"Documents": "Per document: type, issuer, tax year, read status, forms read, then every box the reader reads. "
                     "Exact to the cent; an empty box = blank (not 0).",
        "Summary": "Income / deduction summary lines: the per document amount (and federal withholding).",
        "UT check": "Verify return with the UT input screens: the result per line (ok / different / not entered / entered on "
                    "another line / entered in pieces / 8949 box), then the UT entries with no document (amount).",
        "Files": "The role of each file in this case: " + " / ".join(ROLES) + "."}


def load_key(path: Path) -> dict:
    """{"roles": {file: role}, sheet: [dict(file, form, what, expected, checked)]}"""
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=True)
    out = {"roles": {}}
    if "Files" in wb.sheetnames:
        for row in wb["Files"].iter_rows(min_row=3, values_only=True):
            if row and row[0]:
                out["roles"][str(row[0]).strip()] = str(row[1] or "Document").strip()
    for name, _ in SHEETS:
        rows = []
        if name in wb.sheetnames:
            for row in wb[name].iter_rows(min_row=3, values_only=True):
                if not row or not row[0]:
                    continue
                f, n, w, e, c = (list(row) + [None] * 5)[:5]
                rows.append(dict(file=str(f).strip(), form="" if n in (None, "") else str(int(n) if isinstance(n, float) else n),
                                 what=str(w or "").strip(), expected=e, checked=str(c or "").strip()))
        out[name] = rows
    return out


def _sheet(wb, name, cols):
    from openpyxl.styles import Font, PatternFill, Alignment
    ws = wb.create_sheet(name)
    ws.append([HELP.get(name, "")])
    ws["A1"].font = Font(italic=True, color="555555")
    ws.append(list(cols))
    for c in ws[2]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="4E7874")
        c.alignment = Alignment(vertical="center")
    ws.freeze_panes = "A3"
    widths = {"File": 52, "Form #": 8, "What": 70, "Expected": 22, "Checked": 10, "Role": 22}
    for i, h in enumerate(cols):
        ws.column_dimensions[chr(65 + i)].width = widths.get(h, 14)
    return ws


def _put(ws, f, n, w, v):
    v = norm(v)
    ws.append([f, n if n != "" else None, w, v, None])
    c = ws.cell(row=ws.max_row, column=4)
    if isinstance(v, float):
        c.number_format = "#,##0.00"
    else:
        c.number_format = "@"


def write_key(path: Path, roles: dict, data: dict, existing: dict | None = None, drop=()) -> dict:
    """New key, or rows added to an existing one: only files that have no rows yet on a sheet get rows (nothing already in the
    key is changed). drop = files no longer in the case folder whose rows are removed (only rows nobody checked - make_key
    keeps a file with a checked row). Returns {sheet: rows added}."""
    from openpyxl import Workbook, load_workbook
    added = {}
    if existing is None:
        wb = Workbook()
        wb.remove(wb.active)
        for name, _ in SHEETS:
            _sheet(wb, name, COLS)
        fs = _sheet(wb, "Files", ("File", "Role"))
        for f, role in roles.items():
            fs.append([f, role])
        from openpyxl.worksheet.datavalidation import DataValidation
        dv = DataValidation(type="list", formula1='"' + ",".join(ROLES) + '"', allow_blank=False)
        fs.add_data_validation(dv)
        dv.add("B3:B500")
    else:
        wb = load_workbook(path)
        for ws in [wb[n] for n, _ in SHEETS] + [wb["Files"]]:
            for i in range(ws.max_row, 2, -1):
                if ws.cell(row=i, column=1).value in drop:
                    ws.delete_rows(i)
                    added["removed"] = added.get("removed", 0) + 1
        fs = wb["Files"]
        for f, role in roles.items():
            if f not in existing["roles"]:
                fs.append([f, role])
                added["Files"] = added.get("Files", 0) + 1
    for name, _ in SHEETS:
        ws = wb[name]
        have = {x["file"] for x in (existing or {}).get(name, []) if x["file"] not in drop}
        for f, n, w, v in data.get(name, []):
            if f in have:
                continue
            _put(ws, f, n, w, v)
            added[name] = added.get(name, 0) + 1
    wb.save(path)
    return added


# ---------------------------------------------------------------- intended differences from the archive / the answer keys
# Changes Lady decided after the answer keys and the archive (python-final) were made. The expected side is translated to the
# new way before comparing, so only real mismatches show. Each is listed in design/conversion_plan.md as well.
#   2026-11-17  Income and Deduction Summary (and its Excel): a document's name only - the archive showed
#               "<issuer> — <name>" when the issuer wasn't already in the name (core/income.py _disp).
def label_changes(r: dict) -> list:
    """[(the archive's label, today's label)] for this run's documents (longest first, so a longer label is replaced whole)."""
    pairs = []
    for d in r["inv"]["docs"]:
        name, issuer = Path(d["file"]).stem, d.get("issuer")
        if issuer and issuer.lower() not in name.lower():
            pairs.append((f"{issuer} — {name}", name))
    return sorted(set(pairs), key=lambda p: -len(p[0]))


def apply_label_changes(value, pairs: list):
    """The same value with the archive's labels written the new way (strings anywhere inside lists / dicts)."""
    if not pairs:
        return value
    if isinstance(value, str):
        for old, new in pairs:
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [apply_label_changes(v, pairs) for v in value]
    if isinstance(value, dict):
        return {apply_label_changes(k, pairs): apply_label_changes(v, pairs) for k, v in value.items()}
    return value


def compare(key_rows: list, now: list, labels: list | None = None) -> list:
    """Differences between a key sheet and what the program reads now: [(kind, File, Form #, What, expected, now)].
    kind = "changed" / "not read now" (in the key, gone) / "new" (read now, not in the key) /
    "no key" (a file with no rows on this sheet - run make_key). labels = label_changes(r): the intended differences."""
    if labels:
        key_rows = [dict(x, what=apply_label_changes(x["what"], labels), expected=apply_label_changes(x["expected"], labels))
                    for x in key_rows]
    have = {(x["file"], x["form"], x["what"]): x for x in key_rows}
    files = {x["file"] for x in key_rows}
    cur = {(f, str(n), w): v for f, n, w, v in now}
    out = []
    for k, x in have.items():
        if k not in cur:
            out.append(("not read now", *k, norm(x["expected"]), ""))
        elif not same(x["expected"], cur[k]):
            out.append(("changed", *k, norm(x["expected"]), norm(cur[k])))
    nokey = set()
    for k, v in cur.items():
        if k in have:
            continue
        if k[0] in files:
            out.append(("new", *k, "", norm(v)))
        elif k[0] not in nokey:
            nokey.add(k[0])
            out.append(("no key", k[0], "", "this file has no rows on this sheet — run make_key", "", ""))
    return out


def report(diffs: list) -> str:
    lines = [f"{len(diffs)} difference(s):"]
    for kind, f, n, w, e, v in diffs:
        lines.append(f"  [{kind}] {f}" + (f" #{n}" if n else "") + f" | {w}" +
                     (f" | key: {e} | now: {v}" if kind in ("changed", "not read now", "new") else ""))
    return "\n".join(lines)


# ---------------------------------------------------------------- the archive check (tools/parity/make_reference.py)


def check_reference(case: Path) -> dict:
    """The case through this app, compared with what the retired desktop app (python-final) read for it - the three sheets.
    The reference is written by tools/parity/make_reference.py into the case folder (local only, like the answer key).
    -> {case, against, archive, sheets: [{name, rows, checked, differences}], ok}"""
    ref = json.loads((case / REF_NAME).read_text(encoding="utf-8"))
    r = run_case(case, ref["roles"])
    out = dict(case=case.name, against="the archive (python-final)", archive=ref.get("archive", ""), sheets=[], ok=True)
    with contextlib.redirect_stdout(io.StringIO()):
        for name, fn in SHEETS:
            expected = [dict(file=f, form="" if n in (None, "") else str(n), what=w, expected=v, checked="")
                        for f, n, w, v in ref["sheets"].get(name, [])]
            diffs = compare(expected, fn(r), label_changes(r))
            out["sheets"].append(dict(name=name, rows=len(expected), checked=0,
                                      differences=[[str(v) for v in d] for d in diffs]))
            out["ok"] = out["ok"] and not diffs
        for name, now in pages_after_edits(case, ref["roles"], r).items():     # the converted pages (scenario.py)
            if name not in (ref.get("pages") or {}):
                continue
            expected = apply_label_changes(_scenario().normalize(ref["pages"][name]), label_changes(r))  # same rules both sides
            diffs = _scenario().differences(expected, now)
            out["sheets"].append(dict(name=f"Page: {name}", rows=1, checked=0,
                                      differences=[["changed", "", "", d, "", ""] for d in diffs]))
            out["ok"] = out["ok"] and not diffs
    return out


def _scenario():
    sys.path.insert(0, str(APP_DIR / "tools" / "parity"))
    import scenario
    return scenario


def _more_after_edits(r: dict, sc) -> dict:
    """Step 3: the rest of the Summary's saves (form tabs, UT summary, Schedule C with a P&L, Schedule E), every download,
    then the K-1 box's Remove - what the archive check compares as "summary_more"."""
    import tempfile
    import core.wip as wip_mod
    from core import runcheck

    def post(url, body):
        reply = page("POST", url.format(token=r["token"]), body)
        assert reply["status"] == 200, (url, reply)
        return reply["body"]

    def get(url):
        reply = page("GET", url.format(token=r["token"]))
        assert reply["status"] == 200 and reply["kind"] == "file", (url, reply.get("body"))
        return reply["filename"], reply["body"]
    pl = Path(tempfile.mkdtemp(prefix="u1040_pl_")) / "Demo P&L.csv"
    pl.write_text(sc.PL_CSV, encoding="utf-8")
    sc.more_edits(r, post, str(pl))
    dl = sc.downloads(r, get)
    post("/k1/{token}/remove", {})
    inc, ded = runcheck.summaries(r)
    return dict(summary_more=sc.normalize(dict(work=wip_mod.snapshot(r), income=inc, deductions=ded, downloads=dl)))


def pages_after_edits(case: Path, roles: dict, r: dict) -> dict:
    """The Summary's saves (tools/parity/scenario.py) through this app's pages, then the saved work opened again - what the
    archive check compares with the archive doing the same."""
    import tempfile
    import core.wip as wip_mod
    from core import runcheck
    sc = _scenario()
    open_run(r)
    inc, ded = runcheck.summaries(r)
    for url, body in sc.edits(r, inc, ded):
        reply = page("POST", url.format(token=r["token"]), body)
        assert reply["status"] == 200, (url, reply)
    snap = wip_mod.snapshot(r)
    inc, ded = runcheck.summaries(r)
    out = dict(summary_edits=sc.normalize(dict(work=snap, income=inc, deductions=ded)))
    out.update(_more_after_edits(r, sc))
    snap = wip_mod.snapshot(r)                           # the work as it is now (after step 3) is what gets reopened
    wp = Path(tempfile.mkdtemp(prefix="u1040_wip_")) / "1040 Ultimate WIP test.json"
    wp.write_text(json.dumps(snap, default=str), encoding="utf-8")
    pick = lambda role: next((str(case / n) for n, x in roles.items() if x == role and (case / n).is_file()), "")
    docs = [str(case / n) for n, x in roles.items() if x == "Document" and (case / n).is_file()]
    form = dict(pyret=pick("Prior-year return"), karbon="", clientsum="", utscreens=pick("UT input screens"), wip=str(wp))
    r2 = open_run(runcheck.run(form, docs, work_dir=_work() / "accounts"))
    inc2, ded2 = runcheck.summaries(r2)
    out["summary_reopened"] = sc.normalize(dict(work=wip_mod.snapshot(r2), income=inc2, deductions=ded2))
    out["k1_pages"] = sc.normalize(k1_pages_after_edits(case, roles))
    return out


def k1_pages_after_edits(case: Path, roles: dict) -> dict:
    """Step 5: the K-1 pages (tools/parity/scenario.py k1_pages) on a fresh run with no K-1s added, through this app's pages."""
    from core import runcheck
    from core.k1v import runs as k1runs
    r = open_run(run_case(case, roles, add_k1=False))
    if r.get("wip_path"):                  # the K-1 page saves its work next to the client's: a temporary folder, same name
        r["wip_path"] = str(Path(tempfile.mkdtemp(prefix="u1040_k1_")) / Path(r["wip_path"]).name)

    def reply(method, url, body=None):
        rep = page(method, url.format(token=r["token"]), body)
        assert rep["status"] == 200, (url, rep["status"], str(rep["body"])[:300])
        return rep

    def as_file(rep):
        assert rep["kind"] == "file", rep
        return rep["filename"], rep["body"]
    return _scenario().k1_pages(r, k1runs, lambda url: page("GET", url.format(token=r["token"]))["status"],
                                lambda url, body: reply("POST", url, body)["body"], lambda url: as_file(reply("GET", url)),
                                lambda url, body: as_file(reply("POST", url, body)), runcheck.summaries)


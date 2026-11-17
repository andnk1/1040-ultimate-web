"""runcheck.py - Run check: the steps from the picked files to the run the pages show (document inventory, income
summary ...). The browser app (web/py/webapp.py) and the tests (tests/harness.py) call the same functions.

Moved here from the desktop app's app.py unchanged (2026-11-16; the desktop app is archived as the git tag python-final in
the old repository). `step` is where progress lines go (the progress list under Run check in the browser).

    run(form, docs, ...)       Run check as the first page does it: the checks on the picked files, the reading, the K-1
                               section linked, the UT input screens loaded -> the run (a dict)
    check_form(form)           the first page's checks (is the prior-year return a 1040? ...); raises Problem
    read(form, docs_on, ...)   the whole reading: prior-year return, documents, K-1 routing, Karbon, client summary,
                               amounts -> the run (a dict); raises Problem(text for the preparer)
    load_ut(r, path)           the UltraTax input screens print -> the run (and the K-1 entry check)
    summaries(r)               income + deduction summary of a run
    inventory_rows(r)          the Document inventory's rows
    form_view_data(...)        the form tabs (W2, 1098-M)
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

from . import formview as fv_mod
from . import wip as wip_mod
from .carryovers import read_carryovers
from .clientsum import read_client_summary
from .income import CATS, DED_CATS, build_deduction_summary, build_income_summary
from .clientsum import EXTS as CLIENTSUM_EXTS
from .k1v import handoff as k1v_handoff
from .k1v import runs as k1runs
from .inventory import ROUTE_LBL, natural_key as _natural, scan_files, summary_pages_for
from .karbon import answered, read_karbon
from .parsers import koinly_8949_group, parse_document
from .pdfutil import split_accounts
from .people import read_people
from .py_return import match_expected, read_prior_return, read_py_income, read_schedule_c, read_schedule_e
from .utscreens import looks_like_ut_screens, read_ut_screens


class Problem(Exception):
    """Something the preparer has to fix before the run can go on - the text is shown on the first page."""


def _quiet(msg):
    pass


EMPTY_PY = dict(file="", pages=0, year=None, software="", summary=None, filing_status=None, dependents=None, forms=[],
                expected=[], carryovers=[], warnings=[])


def run(form: dict, docs: list, *, work_dir, step=_quiet, k1w=None) -> dict:
    """Run check, start to end, as the first page does it. form = {pyret, karbon, clientsum, utscreens, wip}: paths of the
    picked files ('' = not picked); docs = the documents to read. The run gets a new "token" (its name while the app is
    open). Raises Problem when a picked file is the wrong kind - the text is shown to the preparer."""
    check_form(form)
    r = read(form, docs, work_dir=work_dir, make_k1_run=k1runs.make_run, k1w=k1w, step=step)
    r["token"] = uuid.uuid4().hex[:12]
    if r.get("k1v_token"):
        k1runs.set_owner(r["k1v_token"], r["token"])       # the K-1 run belongs to this run from the start
    if form.get("utscreens"):
        load_ut(r, form["utscreens"])
    return r


def check_form(form: dict) -> None:
    """The first page's checks on the picked files (the same texts as the desktop app's). Raises Problem."""
    if form.get("pyret"):
        if not Path(form["pyret"]).is_file():
            raise Problem("The prior-year return file wasn't found.")
        if not looks_like_1040(form["pyret"]):
            raise Problem(f"\"{Path(form['pyret']).name}\" doesn't look like a tax return — choose the prior-year 1040 "
                          "(full print package), or leave it empty.")
    if form.get("clientsum"):
        if not Path(form["clientsum"]).is_file():
            raise Problem("The client summary file wasn't found.")
        if Path(form["clientsum"]).suffix.lower() not in CLIENTSUM_EXTS:
            raise Problem(f"\"{Path(form['clientsum']).name}\" — the client summary must be a PDF or a Word document (.docx).")
    if form.get("utscreens"):
        if not Path(form["utscreens"]).is_file():
            raise Problem("The UltraTax input screens file wasn't found.")
        if not looks_like_ut_screens(form["utscreens"]):
            raise Problem(f"\"{Path(form['utscreens']).name}\" doesn't look like the UltraTax input screens print.")


def k1_run(r):
    """The K-1 section's run that belongs to this run: (token, run) or (None, None)."""
    tok = r.get("k1v_token")
    if tok and tok in k1runs.RUNS:
        return tok, k1runs.RUNS[tok]
    tok, k1 = k1runs.run_for(r.get("token"))
    if tok:
        r["k1v_token"] = tok
    return tok, k1


def load_ut(r, path) -> None:
    """The UltraTax input screens print -> r["ut_scr"] (what Verify return checks against), or r["ut_error"] with the reason.
    The K-1 section gets the same print for its K-1 entry check."""
    r["ut_path"], r["ut_scr"], r["ut_error"] = path, None, None
    try:
        r["ut_scr"] = read_ut_screens(path)
        if not (r["ut_scr"]["entries"] or r["ut_scr"].get("rents") or r["ut_scr"].get("memo") or r["ut_scr"].get("payments")
                or r["ut_scr"].get("cscreens")):
            r["ut_error"] = f"No income entries found in \"{Path(path).name}\" — is it the input screens print?"
    except Exception as e:  # noqa: BLE001
        r["ut_error"] = f"Couldn't read the input screens: {type(e).__name__}: {e}"
    tok, _ = k1_run(r)
    if tok and r.get("ut_scr"):
        k1runs.attach_screens(tok, path)


def read(form: dict, docs_on: list, *, work_dir, doc_list=None, mode: str = "summary", make_k1_run=None, k1w=None,
         moved=None, stuck_docs=(), step=_quiet) -> dict:
    """The run for the picked files. form = {pyret, karbon, clientsum, utscreens, wip} (paths, '' = not picked);
    docs_on = the documents to read; work_dir = where a brokerage package is split by account;
    make_k1_run(files, state=) = the K-1 section's reader (None = K-1 files are not routed); k1w = the K-1 work file's content.
    The run has "k1v_token" when K-1 files went to the K-1 section. Nothing is saved here."""
    doc_list = doc_list if doc_list is not None else [dict(path=p, on=True) for p in docs_on]
    moved = moved if moved is not None else []
    step("Run check started")
    if form["pyret"]:
        try:
            step("reading the prior-year return: summary")
            py = read_prior_return(form["pyret"])
            step("prior-year return: Schedule C / E, income, carryovers")
            schc_py = read_schedule_c(form["pyret"])
            sche_py = read_schedule_e(form["pyret"])
            py_inc = read_py_income(form["pyret"], py, schc_py)
            carry = read_carryovers(form["pyret"])
        except Exception as e:  # noqa: BLE001
            raise Problem(f"Couldn't read the prior-year return: {e}") from e
    else:
        py, schc_py, sche_py, py_inc = json.loads(json.dumps(EMPTY_PY)), [], [], {}
        carry = dict(summary=[], from_forms=[], checks=[])
    skip = {os.path.normcase(form[k]) for k in ("utscreens", "clientsum") if form[k]}
    paths = [p for p in docs_on if os.path.normcase(p) not in skip]
    step(f"scanning {len(paths)} documents")
    inv = scan_files(paths, py_year=py.get("year"), py_return=form["pyret"] or None)
    split_packages(inv, work_dir, step)
    k1v_token, k1v_problems = route_k1s(inv, make_k1_run, k1w, step) if make_k1_run else (None, [])
    ut = None
    if form["utscreens"]:
        step("reading the UT input screens")
        try:
            ut = read_ut_screens(form["utscreens"])
        except Exception:  # noqa: BLE001
            ut = None
    if not py.get("year"):                                    # no prior-year return: the tax year from the documents
        years = [d.get("year") for d in inv["docs"] if isinstance(d.get("year"), int)]
        cy = max(set(years), key=years.count) if years else ((ut or {}).get("year") or datetime.now().year - 1)
        py["year"], py["no_return"] = cy - 1, not form["pyret"]
        for d in inv["docs"]:                                 # the tax-year flag needs the year
            d["year_flag"] = bool(d.get("year")) and isinstance(d.get("year"), int) and d["year"] != cy and d.get("route") in ("program", "ai")
    # the Karbon "Client Request Summary" is recognized among the documents (same layout every time)
    found = [d for d in inv["docs"] if d["family"] == "karbon"]
    for d in found:
        d["note"] = ("Karbon Client Request Summary — the client's answers are in the Karbon Summary box. " + (d.get("note") or "")).strip()
    kpath = (found[0]["path"] if found else "") or form["karbon"]
    form["karbon"] = kpath
    try:
        karbon = read_karbon(kpath) if kpath else None
    except Exception as e:  # noqa: BLE001
        karbon = dict(title="", questions=[], error=str(e))
    if karbon is not None:
        karbon["file"] = Path(kpath).name
        karbon["shown"] = answered(karbon)
        if found and not karbon.get("error") and karbon.get("questions"):
            found[0]["read"] = "read"                         # read by the program - its answers are in the Karbon Summary box
        if len(found) > 1:
            karbon["more"] = [Path(d["path"]).name for d in found[1:]]
    clientsum = None
    if form["clientsum"]:
        step("reading the client summary")
        try:
            clientsum = read_client_summary(form["clientsum"])
        except Exception as e:  # noqa: BLE001
            clientsum = dict(file=Path(form["clientsum"]).name, items=[], error=str(e))
    step("reading the amounts on each document")
    read_amounts(inv, step)
    match_expected(py["expected"], inv["docs"])
    schc = [dict(name=b["name"], py=b["lines"], cy={}) for b in schc_py]
    sche = [dict(name=p["name"], py=p["lines"], cy={}, info=dict(type=p.get("type", ""), fair_days=p.get("fair_days"),
                                                                personal_days=p.get("personal_days"))) for p in sche_py]
    r = dict(mode=mode, form=form, py=py, inv=inv, schc_py=schc_py, schc=schc, sche_py=sche_py, sche=sche, py_inc=py_inc,
             docs=paths, doc_list=doc_list, mask=None, carry=carry, edits={}, karbon=karbon, clientsum=clientsum, marks={}, comments={},
             cy_year=(py.get("year") or 0) + 1 if py.get("year") else None, moved=moved,
             stuck=[f"{Path(p).name} — the PDF reader got stuck on it, left out; open it in Acrobat and save a copy, then add the copy"
                    for p in stuck_docs])
    if k1v_token:
        r["k1v_token"] = k1v_token
    if k1v_problems:
        r["stuck"] = list(r.get("stuck") or []) + [f"{m} — not read in the K-1 section" for m in k1v_problems]
    r["client"] = client_label(form, paths)
    r["to_ai"] = default_to_ai(r)
    return r


def route_k1s(inv, make_run, k1w=None, step=_quiet):
    """K-1 PDFs among the documents (+ the ones added on the K-1 page, from the K-1 work file) go to the K-1 section's engine.
    The 1040 reads no K-1 amounts itself: the K-1 lines reach the income summary only through "Add to Income Summary" on the
    K-1 page. make_run(files, state=) = the K-1 section's reader. Returns (K-1 run token or None, [problems])."""
    cands = [d for d in inv["docs"] if d["path"].lower().endswith(".pdf") and d.get("route") != "skipped" and d.get("family") != "pyreturn"
             and (d.get("family") in ("k1p", "k1s", "k1t", "k1x")
                  or re.search(r"(?<![A-Za-z0-9])K-?1(?![0-9])", d["file"], re.I))]      # a K-1 package can be classified as a return / statement
    files = [(d["path"], d["file"]) for d in cands]
    have = {os.path.normcase(p) for p, _ in files}
    for p in (k1w or {}).get("files") or []:                 # K-1 PDFs added on the K-1 page (not among the documents)
        if p and os.path.normcase(p) not in have and Path(p).is_file():
            files.append((p, Path(p).name))
            have.add(os.path.normcase(p))
    if not files:
        return None, []
    step(f"K-1 section: reading {len(files)} K-1 file(s): " + "; ".join(n[:30] for _, n in files))
    try:
        token, problems, counts = make_run(files, state=(k1w or {}).get("state"))
    except Exception as e:  # noqa: BLE001
        step(f"   K-1 section failed ({type(e).__name__}: {e})")
        return None, [f"K-1 section: {type(e).__name__}: {e}"]
    for d in cands:
        forms = counts.get(d["file"]) or []
        if not forms:
            continue
        n = len(forms)
        d.update(family="k1p" if "1065" in forms else "k1s", doc_type="K-1 (1065)" if "1065" in forms else "K-1 (1120-S)", route="k1v",
                 read="read", parsed=dict(status="read", amounts={}, notes=[], checks=[]), k1v_n=n,
                 note=f"Read in the K-1 section — {n} K-1{'s' if n != 1 else ''}.")
    return token, problems


def split_packages(inv, work_dir, step=_quiet):
    """A brokerage package with 2+ accounts (e.g. Ameriprise consolidated) -> one document per account."""
    out = []
    for d in inv["docs"]:
        if d.get("family") in ("composite", "1099b", "1099div", "1099int") and d["path"].lower().endswith(".pdf"):
            try:
                parts = split_accounts(d["path"], work_dir)
            except Exception:  # noqa: BLE001
                parts = []
            if parts:
                step(f"   {d['file']}: {len(parts)} accounts — read separately")
                for p in parts:
                    pg = p["pages"]
                    out.append(dict(d, path=p["path"], orig_path=d["path"], account=p["account"], did=f'{d["did"]}~{p["account"][-4:]}',
                                    tfp=f'{d["tfp"]}~{p["account"][-4:]}' if d.get("tfp") else None,
                                    file=f"{Path(d['file']).stem} — acct …{p['account'][-4:]}{Path(d['file']).suffix}",
                                    note=(f"Account …{p['account'][-4:]} — pages {pg[0]}-{pg[-1]} of the package ({len(parts)} accounts). "
                                          + (d.get("note") or "")).strip()))
                continue
        out.append(d)
    inv["docs"] = out


def client_label(form, paths) -> str:
    """Taxpayer's last name + last 4 of the SSN from the 2024 return (page 1); else the client folder's name."""
    if form.get("pyret"):
        try:
            tp = (read_people(form["pyret"]) or [{}])[0]
            last = re.sub(r"[^A-Za-z' -]", "", tp.get("last") or "").strip().title()
            ssn = re.sub(r"\D", "", tp.get("ssn") or "")
            if last:
                return f"{last} {ssn[-4:]}".strip() if len(ssn) == 9 else last
        except Exception:  # noqa: BLE001
            pass
    return wip_mod.client_name(form, paths)


def looks_like_1040(path) -> bool:
    """The prior-year / current-year return: a Form 1040 package, not a 1099 or other document."""
    try:
        from .pdfutil import open_pdf, page_text
        doc, _ = open_pdf(path)
        with doc:
            n = len(doc)
            txt = " ".join(page_text(doc, i) for i in range(min(n, 15)))
    except Exception:  # noqa: BLE001
        return False
    return n >= 2 and "1040" in txt and bool(re.search(r"Individual Income Tax Return|Two Year Comparison|Form 1040 \(20\d\d\)", txt))


def read_amounts(inv: dict, step=_quiet) -> None:
    """Reads the 2025 amounts from every document the program can read; the rest goes to the AI."""
    for d in inv["docs"]:
        if d["route"] not in ("program", "excluded"):
            continue
        if d["route"] == "excluded":
            continue
        if d["family"] == "koinly" and "8949" in d.get("doc_type", "") and any(
                x["family"] == "koinly" and "Schedule D" in x.get("doc_type", "") for x in inv["docs"]):
            d.update(read="read", parsed=dict(status="read", amounts={}, notes=[], checks=[]),
                     note=(d["note"] + " Detail of the Koinly Schedule D — totals taken from the Schedule D.").strip())
            continue
        step(f"   {d['file']}")
        p = parse_document(d)
        d["parsed"] = p
        if p is None:
            d.update(read="none", route="ai", note=(d["note"] + " No program reader for this form yet — AI review.").strip())
        else:
            d["read"] = p["status"]
            if p.get("inv_note"):                               # 1095-A / 1098-T: a note only, not in the income summary
                d["note"] = (p["inv_note"] + (" · " + d["note"] if d["note"] else "")).strip()
            if p["status"] == "none":
                d.update(route="ai", note=(d["note"] + " Not read: " + "; ".join(p.get("checks") or ["no amounts found"]) + " — AI review.").strip())
            elif p["status"] == "partial":
                d["note"] = (d["note"] + " Partly read — check: " + "; ".join(p["checks"])).strip()
    # Koinly Schedule D: the 8949 tells which box of each pair (1099-B A-F / 1099-DA G-L)
    k8949 = next((d for d in inv["docs"] if d["family"] == "koinly" and "8949" in d.get("doc_type", "")), None)
    grp = None
    if k8949:
        try:
            grp = koinly_8949_group(k8949["path"])
        except Exception:  # noqa: BLE001
            grp = None
    for d in inv["docs"]:
        p = d.get("parsed")
        if d["family"] == "koinly" and isinstance(p, dict) and p.get("parts") and grp:
            pick = 1 if grp == "da" else 0
            one = lambda lb: re.sub(r"\(([A-L])/([A-L])\)", lambda m: f"({m.group(1 + pick)})", lb)
            p["parts"] = {k: [(one(lb), v) for lb, v in pl] for k, pl in p["parts"].items()}
            p["part_notes"] = {one(lb): n for lb, n in (p.get("part_notes") or {}).items()}
    for d in inv["docs"]:
        # no known issuer in the text: the employer (W-2 box c) / lender (1098) the reader found on the form
        p = d.get("parsed")
        if not d.get("issuer") and isinstance(p, dict) and d["family"] in ("w2", "1098"):
            f = next(iter((p.get("detail") or {}).get("boxes") or []), {})
            d["issuer"] = (f.get("er") or f.get("ln") or "").split("\n")[0].strip() or None
    for d in inv["docs"]:
        # documents that now go to the AI: long ones send only their summary pages
        if (d["route"] in ("ai", "context") or d.get("read") == "partial") and not d.get("ai_page_list") and d["ext"] == ".pdf":
            sp = summary_pages_for(d["path"], d.get("pages") or 0)
            if sp:
                d.update(ai_page_list=sp, ai_pages=", ".join(map(str, sp)) + f" of {d['pages']}")
            elif d.get("pages") and not d.get("ai_pages"):
                d["ai_pages"] = f"all ({d['pages']})"
    inv["counts"] = {k: sum(1 for d in inv["docs"] if d["route"] == k) for k in ROUTE_LBL}


def default_to_ai(r) -> dict:
    """Goes to AI (ticked by default): not read / partly read / context documents and the prior-year return.
    Not ticked: documents the program read, excluded / skipped files, the Karbon organizer (its summary goes instead)."""
    out = {r["form"]["pyret"]: True} if r["form"].get("pyret") else {}
    for d in r["inv"]["docs"]:
        tick = (d["route"] in ("ai", "context") or d.get("read") == "partial") and d["family"] not in ("karbon", "pyreturn")
        out[d["path"]] = bool(tick)
    if r["form"].get("karbon"):
        out[r["form"]["karbon"]] = False
    return out


# ---------------------------------------------------------------- document inventory
INV_SECS = CATS + DED_CATS            # "Added to": the income (and deduction) lines
def inventory_rows(r) -> list:
    """Document inventory (top of screen 1): read by the program first, then not read, each alphabetical.
    Read documents are listed only (their amounts are on the income summary); a not-read document can carry
    one amount + the income line it goes to. Free lines (+) come last."""
    st = r.setdefault("invstate", {"verified": {}, "amt": {}, "notes": {}, "free": []})
    rows = []
    for d in r["inv"]["docs"]:
        if d["family"] == "pyreturn":
            continue
        read = d.get("read") in ("read", "partial")
        note = d.get("note") or ""
        if d.get("ai_page_list") and r.get("to_ai", {}).get(d["path"]):
            note = (note + " · " if note else "") + "AI pages: " + d["ai_pages"]
        a = st["amt"].get(d["did"]) or {}
        typ = d.get("doc_type") or ""
        amts = (d.get("parsed") or {}).get("amounts") if isinstance(d.get("parsed"), dict) else None
        if d["family"] == "composite" and amts:          # the forms that hold amounts (the text names every 1099 in its instructions)
            parts = [f for f, ks in (("INT", ("interest",)), ("DIV", ("dividends",)), ("B", ("st", "lt")), ("MISC", ("other", "rental")))
                     if any(amts.get(k) for k in ks)]
            typ += " (" + ", ".join(parts) + ")" if parts else ""
        rows.append(dict(key=d["did"], file=d["file"], path=d["path"], issuer=d.get("issuer") or "", type=typ, year=d.get("year") or "",
                         year_flag=d.get("year_flag"), read=d.get("read") or "none", is_read=read, password=d.get("password"),
                         feeds=("Karbon Summary" if d["family"] == "karbon" else
                                "comments only" if isinstance(d.get("parsed"), dict) and d["parsed"].get("memo_only") else feeds_label(d)) if read else "",
                         cy=a.get("cy"), sec=a.get("sec", ""),
                         note=st["notes"].get(d["did"], note), verified=bool(st["verified"].get(d["did"])),
                         warn=(r.get("docnotes") or {}).get(d["did"], ""),
                         ai=bool(r.get("to_ai", {}).get(d["path"])), free=False))
    rows.sort(key=lambda x: _natural(x["file"]))                   # by file name: numbers in order (2 before 10), then A-Z
    for f in st["free"]:
        rows.append(dict(key=f["id"], file=f.get("name", ""), issuer=f.get("issuer", ""), type="", year="", read="", is_read=False,
                         feeds="", cy=f.get("cy"), sec=f.get("sec", ""), note=f.get("note", ""),
                         verified=bool(f.get("verified")), ai=False, free=True))
    return rows


def feeds_label(d) -> str:
    """Income lines a read document landed on (from what the parser found)."""
    if d.get("route") == "k1v":
        return "K-1 section"
    p = d.get("parsed")
    amts = {}
    for x in (p if isinstance(p, list) else [p] if isinstance(p, dict) else []):
        amts.update({k: v for k, v in (x.get("amounts") or {}).items() if v})
    keys = [k for k, _, _ in INV_SECS if k in amts]
    lbl = dict((k, l) for k, l, _ in INV_SECS)
    return ", ".join(lbl[k].replace("Total ", "") for k in keys)


def inventory_export(r) -> list:
    """Inventory rows for the Excel Documents sheet."""
    lbl = {k: l.replace("Total ", "") for k, l, _ in INV_SECS}
    rl = {"read": "Read", "partial": "Partly read", "none": "Not read"}
    return [dict(d, read_lbl=rl.get(d["read"], "") if not d["free"] else "Added line", sec_lbl=lbl.get(d.get("sec"), ""))
            for d in inventory_rows(r)]


def inventory_added(r) -> list:
    """Inventory amounts -> income summary lines (corrected amount only; per document stays blank). Keyed by the document's id."""
    st = r.get("invstate") or {}
    names = {d["did"]: d["file"] for d in r["inv"]["docs"]}
    out = []
    for did, a in (st.get("amt") or {}).items():
        if a.get("sec") and a.get("cy") is not None and did in names:
            out.append(dict(id="inv|" + did, sec=a["sec"], doc=names[did], file=names[did], cy=a["cy"], fit=None,
                            note=(st.get("notes") or {}).get(did, ""), inv=True))
    for f in st.get("free") or []:
        if f.get("sec") and f.get("cy") is not None:
            out.append(dict(id="inv|free|" + f["id"], sec=f["sec"], doc=f.get("name") or "Added line", cy=f["cy"], fit=None,
                            note=f.get("note", ""), inv=True))
    return out


# ---------------------------------------------------------------- form tabs of the Document inventory
def form_view_data(r, inc, invrows, ded=None) -> dict:
    """The Document inventory's form tabs (W2 / 1098-M = 6 forms per tab, then the form types), every W-2 / 1098 column, the
    corrections ({form: {column: {row: value}}}), and the lines typed over on the income / deduction summary (those win)."""
    order = [d["key"] for d in invrows if not d["free"]]
    cols = fv_mod.columns(r, order, "w2") + fv_mod.columns(r, order, "1098")
    typed = {"w2": {}, "1098": {}}
    for form, summ, key in (("w2", inc, "w2"), ("1098", ded, "mortgage")):
        for s in (summ or {}).get("sections", []):
            if s["key"] == key:
                for x in s["rows"]:
                    if x.get("edited") and x.get("file"):
                        typed[form][x["file"]] = dict(cy=x.get("cy"), fit=x.get("fit"))
    py_year = r["py"].get("year")
    cy_year = (py_year or 0) + 1 if py_year else None
    fvs = r.get("formview") or {}
    return dict(tabs=fv_mod.tabs(r, cols), defs=fv_mod.DEFS, cols=cols, edits={f: fvs.get(f) or {} for f in fv_mod.FORMS},
                typed=typed, codes=fv_mod.W2_12, year=cy_year, base=fv_mod.WAGE_BASE.get(cy_year), rate=fv_mod.SS_RATE,
                per=fv_mod.PER_TAB)


# ---------------------------------------------------------------- income / deduction summary
def summaries(r):
    py_year = r["py"].get("year")
    cy_year = (py_year or 0) + 1 if py_year else None
    added = list(r.get("added") or []) + inventory_added(r)
    docs = fv_mod.effective_docs(r)                     # W-2 corrections from the form view; typed income summary amounts still win
    inc = build_income_summary(r["py_inc"], docs, r["schc"], py_year, cy_year, r.get("edits"), added, sche=r.get("sche"),
                               k1=r.get("k1"))
    ded = build_deduction_summary(r["py_inc"], docs, py_year, cy_year, r.get("edits"), added)
    return inc, ded


# ---------------------------------------------------------------- the K-1 box
def k1_status(r, tok=None, run=None) -> dict:
    """The main page's K-1 box: K-1 documents found / added (when, how many) / changed since added.
    tok, run = the K-1 run of this 1040 run (core/k1v/runs.py); not given = looked up."""
    if tok is None and run is None:
        tok, run = k1_run(r)
    pkg = r.get("k1")
    found = bool(run and run.get("k1s")) or any(d.get("route") == "k1v" for d in r["inv"]["docs"])
    changed = bool(pkg and run and k1v_handoff.signature(run["k1s"], run.get("state")) != pkg.get("sig"))
    added = (pkg or {}).get("added") or ""
    when = added[11:] if added[:10] == datetime.now().strftime("%Y-%m-%d") else added
    return dict(token=tok, found=found, pkg=pkg, changed=changed, when=when, check=bool(run and run.get("result")),
                files=[n for _, n in (run or {}).get("files") or []])

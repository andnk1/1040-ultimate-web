"""summary.py - page 1 · Summary (templates/summary.html), and its downloads.

The saves below are the desktop app's, unchanged in what they keep (moved from its app.py): each takes the run's token and
what the page sent (`sent`), changes the run, and answers {"ok": true}. After each one the work in progress is saved
(web/py/routes.py, AUTOSAVE). The downloads (Excel, CSV) answer a file; the page saves it as a download.
A file the preparer picks on the page (a P&L, a Schedule E sheet) is first copied onto the tab's in-memory drive by the page
(web/index.html, "Browse"): the functions get its path there, as the desktop got a path on the disk.
"""
from __future__ import annotations

import io
import json

import csv
import re
from datetime import datetime
from pathlib import Path

from core import runcheck
from core.inventory import ROUTE_LBL
from core.pl import MAP_LINES as PL_MAP_LINES, book_tax_csv, other_expenses_csv, read_pl, workpaper_csv
from core.py_return import SCHC_LINES, SCHE_LINES

from . import NotFound, data, file, get_run, page, render, save_work, shown_folder

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CSV = "text/csv"


def _safe_name(name: str) -> str:
    """A name that can be a file name (no \\ / : * ? " < > |)."""
    return re.sub(r'[\\/:*?"<>|]+', " ", name).strip()


def show(token: str):
    """The Summary page of a run (the desktop's /summary/<run>)."""
    r = get_run(token)
    r.setdefault("comments", {})
    inc, ded = runcheck.summaries(r)
    invrows = runcheck.inventory_rows(r)
    return page(render(
        "summary.html", r=r, token=token, ROUTE_LBL=ROUTE_LBL, inc=inc, ded=ded, MAPL=PL_MAP_LINES, k1=runcheck.k1_status(r),
        invrows=invrows, INV_SECS=runcheck.INV_SECS, fv=runcheck.form_view_data(r, inc, invrows, ded),
        SCHC=list(SCHC_LINES.items()), schc_json=json.dumps(r["schc"]),
        SCHE=list(SCHE_LINES.items()), sche_json=json.dumps(r.get("sche") or [])))


def schedule_e_template(token: str | None = None):
    """The standard Schedule E sheet (Schedule E box → Export Template). With a run, the sheet comes pre-filled with the
    prior-year return's property addresses (amounts blank), so the names match when the sheet is imported back."""
    from core.sche_template import template_rows, write_template
    rows = template_rows(get_run(token).get("sche_py") or []) if token else None   # skips "Property n" placeholders
    buf = io.BytesIO()
    write_template(buf, rows or None)
    return file(buf.getvalue(), "Schedule E template.xlsx", XLSX)


# ---------------------------------------------------------------- income and deduction summary
def save_edits(token: str, sent: dict):
    """Amounts typed over on the income / deduction summary: {row id: {cy, fit, note}}; each correction keeps the per-document
    amount it was typed over (base) for the stale-correction flag."""
    from core.income import per_doc, stamp_edits
    r = get_run(token)
    inc, ded = runcheck.summaries(r)
    sent = _without_locked(sent or {}, r.get("edits") or {}, inc, ded)
    r["edits"] = stamp_edits(sent, r.get("edits"), per_doc(inc, ded))
    return data({"ok": True})


def _without_locked(sent: dict, old: dict, inc: dict, ded: dict) -> dict:
    """A document the program read is corrected on its own screen, not here (Lady, 2026-11-24 - core/income.py
    where_to_correct). On those rows only the comment is taken; an amount typed anyway is left out - except a correction saved
    before the lock, which comes back unchanged and is kept (it still counts; the row says to move it)."""
    locked = {x["id"] for t in (inc, ded) for sec in t["sections"] for x in sec["rows"] if x.get("lock")}
    out = {}
    for rid, e in sent.items():
        if rid in locked and isinstance(e, dict):
            prev = old.get(rid) or {}
            e = {k: v for k, v in e.items() if k not in ("cy", "fit")}
            e.update({k: prev[k] for k in ("cy", "fit") if k in prev})     # a correction saved before the lock stays as it was
        out[rid] = e
    return out


def confirm_edit(token: str, sent: dict):
    """Re-confirm a correction whose per-document amount changed: its base becomes the current per-document amount."""
    from core.income import per_doc
    r = get_run(token)
    rid = str((sent or {}).get("id") or "")
    e = (r.get("edits") or {}).get(rid)
    if e:
        inc, ded = runcheck.summaries(r)
        dc, df = per_doc(inc, ded).get(rid, (None, None))
        if "cy" in e:
            e["base"] = dc
        if "fit" in e:
            e["base_fit"] = df
    return data({"ok": True})


def save_added(token: str, sent: list):
    """Lines added with + on the income summary: [{id, sec, doc, cy, fit, note}]."""
    r = get_run(token)
    r["added"] = [a for a in (sent or []) if isinstance(a, dict) and a.get("id")]
    return data({"ok": True})


def save_carry_added(token: str, sent: list):
    """Carryovers added with + by the preparer: [{id, item, activity, amount, note}]."""
    r = get_run(token)
    r["carry_added"] = [a for a in (sent or []) if isinstance(a, dict) and a.get("id")]
    return data({"ok": True})


def save_comments(token: str, sent: dict):
    """Return comments (top of the summary page) and the "received?" comments: {client, recv: {kind|name: text}, recv_note}."""
    r = get_run(token)
    j = sent or {}
    r["comments"] = dict(client=str(j.get("client") or ""), recv={k: str(v) for k, v in (j.get("recv") or {}).items() if str(v).strip()},
                         recv_ok={k: True for k, v in (j.get("recv_ok") or {}).items() if v}, recv_note=str(j.get("recv_note") or ""))
    return data({"ok": True})


def save_marks(token: str, sent: dict):
    """Ticks (✓) and typed comments on any line of any screen: {key: true/false} and {"n|" + key: text} - merged;
    false / empty removes the key."""
    r = get_run(token)
    m = r.setdefault("marks", {})
    for k, v in (sent or {}).items():
        if v in (False, None, "") or (isinstance(v, str) and not v.strip()):
            m.pop(k, None)
        else:
            m[k] = v
    return data({"ok": True})


# ---------------------------------------------------------------- document inventory
def _num(v):
    """An amount as typed ("1,234.50", "$80") -> a number with cents, or None."""
    try:
        return None if v in (None, "") else round(float(str(v).replace(",", "").replace("$", "")), 2)
    except ValueError:
        return None


def save_inventory(token: str, sent: dict):
    """Inventory state (keyed by the document's id): {verified: {key: bool}, amt: {id: {cy, sec}}, notes: {id: text},
    free: [{id, name, issuer, cy, sec, note, verified}]}."""
    r = get_run(token)
    j = sent or {}
    r["invstate"] = dict(
        verified={k: bool(v) for k, v in (j.get("verified") or {}).items()},
        amt={k: dict(cy=_num(v.get("cy")), sec=v.get("sec") or "") for k, v in (j.get("amt") or {}).items() if isinstance(v, dict)},
        notes={k: str(v) for k, v in (j.get("notes") or {}).items()},
        free=[dict(id=str(f.get("id")), name=f.get("name", ""), issuer=f.get("issuer", ""), cy=_num(f.get("cy")), sec=f.get("sec") or "",
                   note=f.get("note", ""), verified=bool(f.get("verified"))) for f in (j.get("free") or []) if isinstance(f, dict) and f.get("id")])
    for k in r["invstate"]["verified"]:                     # ticked Verified: the replaced / matched-by-name note has been seen
        (r.get("docnotes") or {}).pop(k, None)
    return data({"ok": True})


def save_invnote(token: str, sent: dict):
    """The comment typed on an inventory line of the income summary = that line's inventory note."""
    r = get_run(token)
    j = sent or {}
    rid, note = str(j.get("id") or ""), str(j.get("note") or "")
    st = r.setdefault("invstate", {"verified": {}, "amt": {}, "notes": {}, "free": []})
    if rid.startswith("inv|free|"):
        for f in st.get("free") or []:
            if f.get("id") == rid[9:]:
                f["note"] = note
    elif rid.startswith("inv|"):
        st.setdefault("notes", {})[rid[4:]] = note
    return data({"ok": True})


def save_toai(token: str, sent: dict):
    """Goes-to-AI ticks from the Documents table: {path: true/false}."""
    r = get_run(token)
    r["to_ai"].update(sent or {})
    r["mask"] = None                     # (the desktop's masking list followed these ticks)
    return data({"ok": True})


# ---------------------------------------------------------------- the work in progress: Save now / Choose a folder…
def wip_save(token: str, sent: dict | None = None):
    """The 'Save work in progress' button: saves now (it is also saved after every change)."""
    r = get_run(token)
    path = save_work(r)
    if path:
        return data(dict(ok=True, file=Path(path).name, folder=shown_folder(path), at=r.get("wip_saved") or datetime.now().strftime("%H:%M")))
    if not r.get("wip_path"):
        return data(dict(ok=False, nofolder=True, error="No place to save yet - choose a folder."))
    return data(dict(ok=False, error=r.get("wip_error") or "Couldn't save the work in progress."))


def wip_folder(token: str, sent: dict):
    """No folder Chrome lets the app edit (single files only): the preparer picks one. The page opens the folder window
    first and sends {"folder": its place on the in-memory drive} - or {"cancelled": true}."""
    from core import wip as wip_mod
    r = get_run(token)
    if (sent or {}).get("cancelled") or not (sent or {}).get("folder"):
        return data(dict(cancelled=True))
    r["wip_path"] = wip_mod.new_path(sent["folder"], r)
    r.setdefault("places", []).append(sent["folder"].rstrip("/") + "/")   # Chrome lets the app write in it (Verify's review Excel)
    saved = save_work(r)
    return data(dict(saved=saved, error=r.get("wip_error")))


# ---------------------------------------------------------------- form tabs (W2, 1098-M) and the UT summary
def save_formview(token: str, form: str, sent: dict):
    """Form view corrections: {"<doc id>#<form index>": {row key: value}} - the whole form's set (parsed values stay as read)."""
    r = get_run(token)
    if not isinstance(r.get("formview"), dict):
        r["formview"] = {}
    r["formview"][form] = {k: v for k, v in (sent or {}).items() if isinstance(v, dict) and v}
    return data({"ok": True})


def save_ut(token: str, sent: dict):
    """UT summary fields typed over: {field: value}."""
    get_run(token)["ut"] = sent or {}
    return data({"ok": True})


# ---------------------------------------------------------------- Schedule C box
def save_schc(token: str, sent: list):
    """The Schedule C box: every business (lines, the P&L read, totals; "calculated" = moved to the income summary)."""
    get_run(token)["schc"] = sent or []
    return data({"ok": True})


def load_pl(token: str, sent: dict):
    """Add P&L…: reads a P&L (CSV / Excel / PDF) for the Schedule C box: accounts, suggested lines, total check."""
    get_run(token)
    path = (sent or {}).get("path", "")
    if not path or not Path(path).is_file():
        return data(dict(file=Path(path).name if path else "", rows=[], error="File not found."))
    return data(read_pl(path))


def schedule_c_csv(token: str, i: str, which: str):
    """The Schedule C box's downloads for business i: workpaper / other expenses (Part V, line 27b) / books vs Schedule C."""
    r = get_run(token)
    i = int(i)
    bz = r.get("schc") or []
    if i >= len(bz):
        raise NotFound("That business isn't in the Schedule C box.")
    b = bz[i]
    rows = ((b.get("pl") or {}).get("rows")) or []
    for x in rows:
        x["amount"] = float(x.get("amount") or 0)
    lines = {}                                         # each Schedule C line's amount from the P&L accounts mapped to it
    for x in rows:
        inc_side = x["section"] in ("income", "other_income")
        sign = 1 if inc_side == (x["line"] in ("1", "6")) else -1
        lines[x["line"]] = lines.get(x["line"], 0) + (x["amount"] if x["line"] in ("nd", "x") else sign * x["amount"])
    name = _safe_name(b.get("name") or f"Business {i + 1}")
    if which == "workpaper":
        content, fn = workpaper_csv(b, lines, b.get("final") or {}), f"{name} - Schedule C workpaper.csv"
    elif which == "other_expenses":
        content, fn = other_expenses_csv(rows), f"{name} - Schedule C other expenses.csv"
    elif which == "book_tax":
        content, fn = book_tax_csv(rows), f"{name} - books vs Schedule C.csv"
    else:
        raise NotFound("No such download.")
    return file(content.encode("utf-8") if isinstance(content, str) else content, fn, CSV)


# ---------------------------------------------------------------- Schedule E box
def save_sche(token: str, sent: list):
    """The Schedule E box: every property (lines, days, totals; "calculated" = moved to the income summary)."""
    get_run(token)["sche"] = sent or []
    return data({"ok": True})


def import_schedule_e(token: str, sent: dict):
    """Import Schedule E sheet…: reads a filled Schedule E sheet (the standard template, .xlsx or .csv) -> properties."""
    from core.sche_template import read_template
    get_run(token)
    path = ((sent or {}).get("path") or "").strip().strip('"')
    if not path or not Path(path).is_file():
        return data(dict(error="File not found."))
    try:
        res = read_template(path)
    except Exception as e:  # noqa: BLE001 - a sheet that can't be read: say why, as the desktop did
        return data(dict(error=f"Couldn't read {Path(path).name}: {type(e).__name__}: {e}"))
    if not res["properties"]:
        return data(dict(error="; ".join(res["errors"]) or "No properties in the sheet."))
    return data(dict(file=Path(path).name, properties=res["properties"], errors=res["errors"]))


def schedule_e_csv(token: str, i: str):
    """A property's workpaper (CSV): last year and this year line by line, and what goes to the income summary."""
    r = get_run(token)
    i = int(i)
    props = r.get("sche") or []
    if i >= len(props):
        raise NotFound("That property isn't in the Schedule E box.")
    p = props[i]
    t = p.get("totals") or {}
    buf = io.StringIO()
    w = csv.writer(buf)
    info = p.get("info") or {}
    w.writerow(["Schedule E workpaper", p.get("name") or f"Property {i + 1}"])
    w.writerow(["Type", info.get("type", ""), "Fair rental days", info.get("fair_days") or "", "Personal use days",
                info.get("personal_days") or ""])
    w.writerow([])
    w.writerow(["Line", "Description", "Last year", "This year"])

    def n(x):
        try:
            return f"{float(str(x).replace(',', '')):.2f}"
        except (TypeError, ValueError):
            return ""
    for k, lbl in SCHE_LINES.items():
        if k == "19" and info.get("other_desc"):
            lbl += " — " + info["other_desc"]
        cy = t.get(k) if k in ("20", "21") else (p.get("cy") or {}).get(k)
        w.writerow([k, lbl, n((p.get("py") or {}).get(k)), n(cy)])
    w.writerow(["", "To the income summary", "", n(t.get("net"))])
    name = _safe_name(p.get("name") or f"Property {i + 1}")
    return file(buf.getvalue().encode("utf-8"), f"{name} - Schedule E workpaper.csv", CSV)


# ---------------------------------------------------------------- Excel and the K-1 box
def income_excel(token: str):
    """Income and Deduction Summary (Excel): both tables (corrected amounts, per document, comments) + the Documents sheet."""
    from core.excel import income_xlsx
    r = get_run(token)
    inc, ded = runcheck.summaries(r)
    name = r.get("client") or "Client"
    content = income_xlsx(inc, name, ded, runcheck.inventory_export(r))
    return file(content, f"Income Summary {inc['cy_year'] or ''} - {name}.xlsx", XLSX)


def k1_remove(token: str, sent: dict | None = None):
    """The K-1 box's Remove: the K-1 lines leave the income summary (the K-1 section's own work stays)."""
    get_run(token)["k1"] = None
    return data({"ok": True})

"""summary.py - page 1 · Summary (templates/summary.html), and its downloads.

The saves below are the desktop app's, unchanged in what they keep (moved from its app.py): each takes the run's token and
what the page sent (`sent`), changes the run, and answers {"ok": true}. After each one the work in progress is saved
(web/py/routes.py, AUTOSAVE). Not converted yet: Schedule C / E, the form tabs, the UT summary, Excel (next step).
"""
from __future__ import annotations

import io
import json

from datetime import datetime
from pathlib import Path

from core import runcheck
from core.inventory import ROUTE_LBL
from core.pl import MAP_LINES as PL_MAP_LINES
from core.py_return import SCHC_LINES, SCHE_LINES

from . import data, file, get_run, page, render, save_work

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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
    r["edits"] = stamp_edits(sent or {}, r.get("edits"), per_doc(inc, ded))
    return data({"ok": True})


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
        return data(dict(ok=True, file=Path(path).name, folder=_shown_folder(path), at=r.get("wip_saved") or datetime.now().strftime("%H:%M")))
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
    saved = save_work(r)
    return data(dict(saved=saved, error=r.get("wip_error")))


def _shown_folder(path: str) -> str:
    """Where the file is, as the preparer knows it: the client folder's name and sub-folders (not the in-memory drive)."""
    parts = Path(path).parent.parts
    for lead in (("/", "client", "docs"), ("/", "client", "save"), ("/", "client", "picked")):
        if parts[:3] == lead:
            return "/".join(parts[3:]) or parts[-1]
    return str(Path(path).parent)

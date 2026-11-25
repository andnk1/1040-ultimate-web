"""verify.py - page 2 · Verify return (templates/verify.html), its checklist and its review Excel.

Moved from the desktop app's app.py (python-final), unchanged in what it checks and keeps:
    show            the page: the files picked, the checks (UT input screens and / or the 2025 return), the checklist
    check_files     "Check": reads the UT input screens print and / or the 2025 return the preparer picked
    save_checklist  the checklist's ticks, notes, Stays Y / N (Stays Y = on the master list for every client)
    save_review     "Save review (Excel)": into the client folder when the app may write there, else a download
    master          the master checklist file on the shared drive (picked once; Chrome remembers it)

What changed for the browser (design/conversion_plan.md, 2 · Verify return):
- The files are picked with the browser's file window; the page copies them onto the tab's in-memory drive and sends their
  path there (web/index.html browseFile). Before reading, each PDF is opened in the stuck-PDF guard (web/probe.js) with the
  desktop's 90 seconds; a stuck one arrives here as sent["stuck"] = the desktop's message.
- The master checklist (checklist_master.json) was a file in the app folder - one list per computer. Now it is a file on
  the shared drive, picked once (Lady, 2026-11-24: question 2, option a): the page reads it and sends its text here; it is
  kept at core/verify.py's MASTER on the in-memory drive, so master_load / master_save work as before, and every change is
  written back to the shared file. Without the file the built-in list is used (as on the desktop when the file was missing).
- The review Excel went into a folder chosen in a Windows window (starting at the work-in-progress folder). Now it goes
  into the work-in-progress folder when Chrome lets the app write there, else the browser downloads it.
"""
from __future__ import annotations

import filecmp
import json
import re
from pathlib import Path

from core import formview as fv_mod
from core import runcheck
from core import verify as verify_mod
from core.utscreens import doc_verify, looks_like_ut_screens
from core.verify import master_load, master_save, read_cy_return, review_xlsx, run_checks

from . import data, file, get_run, page, render, shown_folder, writable_folder, write_out

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# the master checklist file while the app is open: its name and whether its content is here (the page sends it)
MASTER = dict(name="", connected=False, waiting=False)


def _checklist(r):
    """The run's checklist: made from the master list the first time the page is drawn (as on the desktop). "fresh" = not
    changed yet by the preparer - if the master file is connected after that, the checklist starts again from it."""
    if r.get("checklist") is None:
        r["checklist"] = [dict(text=t, done=False, stays=True, master=True, note="") for t in master_load()]
        r["_cl_fresh"] = True
    return r["checklist"]


def _same_file(a: str, b: str) -> bool:
    """Two picks of one file: the same path, or the same content (the browser gives each pick its own place)."""
    try:
        return Path(a) == Path(b) or filecmp.cmp(a, b, shallow=False)
    except OSError:
        return False


# ---------------------------------------------------------------- the page
def show(token: str):
    r = get_run(token)
    r.setdefault("comments", {})
    checks, err, ut = None, r.get("cy_error"), None
    inc, ded = runcheck.summaries(r)
    if r.get("cy_ret"):
        try:
            checks = run_checks(r["cy_ret"], inc, ded, fv_mod.effective_docs(r), r["py"], r.get("sche"))
        except Exception as e:  # noqa: BLE001
            err = f"Couldn't check the return: {type(e).__name__}: {e}"
    if r.get("ut_scr"):
        ut = doc_verify(inc, fv_mod.effective_docs(r), r["ut_scr"], r.get("sche"), r.get("schc"))
    cy_path, ut_path = r.get("cy_path", ""), r.get("ut_path") or ""
    return page(render("verify.html", r=r, token=token, checks=checks, error=err, ut=ut, ut_error=r.get("ut_error"),
                       cy_path=cy_path, ut_path=ut_path, cy_name=Path(cy_path).name if cy_path else "",
                       ut_name=Path(ut_path).name if ut_path else "", inc=inc, master=MASTER,
                       checklist=json.dumps(_checklist(r))))


def check_files(token: str, sent: dict):
    """The 2025 return and / or the UT input screens. With the input screens -> the three-way check;
    without them -> the return-based check."""
    r = get_run(token)
    j = sent or {}
    path = (j.get("path") or "").strip().strip('"')
    utp = (j.get("ut") or "").strip().strip('"')
    r["cy_path"], r["cy_error"], r["cy_ret"] = path, None, None
    r["ut_path"], r["ut_error"], r["ut_scr"] = utp, None, None
    if not path and not utp:
        r["cy_error"] = "Choose the UltraTax input screens and / or the 2025 return (PDF)."
    if j.get("stuck"):                          # the stuck-PDF guard (web/index.html) couldn't open one of them
        r["cy_error"] = str(j["stuck"])
        return data(dict(ok=False, error=r["cy_error"]))
    if path:
        if not Path(path).is_file():
            r["cy_error"] = "The 2025 return file wasn't found."
        elif r["form"].get("pyret") and _same_file(path, r["form"]["pyret"]):
            r["cy_error"] = "That's the prior-year return — choose the 2025 return."
        elif not runcheck.looks_like_1040(path):
            r["cy_error"] = f"\"{Path(path).name}\" doesn't look like a tax return — choose the 2025 1040 (full print package)."
        else:
            try:
                r["cy_ret"] = read_cy_return(path)
            except Exception as e:  # noqa: BLE001
                r["cy_error"] = f"Couldn't read the return: {type(e).__name__}: {e}"
    if utp:
        if not Path(utp).is_file():
            r["ut_error"] = "The input screens file wasn't found."
        elif not looks_like_ut_screens(utp):
            r["ut_error"] = f"\"{Path(utp).name}\" doesn't look like the UltraTax input screens print."
        else:
            runcheck.load_ut(r, utp)
    return data(dict(ok=not (r["cy_error"] or r["ut_error"]), error=r["cy_error"] or r["ut_error"]))


# ---------------------------------------------------------------- the checklist
def save_checklist(token: str, sent: list):
    """Checklist lines: done / note / stays. Stays Y = on the master list for every client; N = this return only."""
    r = get_run(token)
    items = [x for x in (sent or []) if isinstance(x, dict) and str(x.get("text", "")).strip()]
    master = master_load()
    for x in items:
        t = x["text"].strip()
        if x.get("stays") and t not in master:
            master.append(t)
        if not x.get("stays") and x.get("master") and t in master:
            master.remove(t)
        x["master"] = bool(x.get("stays"))
    master_save(master)
    _master_to_shared_drive()
    r["checklist"] = items
    r["_cl_fresh"] = False
    return data(dict(ok=True, master=len(master), kept=MASTER["connected"]))


def _master_to_shared_drive() -> None:
    """The master list just saved (core/verify.py master_save) -> the file on the shared drive (web/index.html saveFile)."""
    if MASTER["connected"] and verify_mod.MASTER.is_file():
        write_out(str(verify_mod.MASTER))


def master_path() -> str:
    """Where the master checklist sits on the in-memory drive (the page maps it to the shared-drive file)."""
    return str(verify_mod.MASTER)


def master(token: str, sent: dict):
    """The master checklist file, from the page: {name, text} = its content (text "" = a new file: the list as it is now
    is written into it); {name, waiting: true} = Chrome remembers the file but asks again before the app may use it (the
    page shows "Allow access"); {cancelled: true} = nothing picked."""
    r = get_run(token)
    j = sent or {}
    if j.get("cancelled"):
        return data(dict(cancelled=True, error=j.get("error") or ""))
    MASTER.update(name=str(j.get("name") or ""), connected=False, waiting=bool(j.get("waiting")))
    if MASTER["waiting"]:
        return data(dict(ok=True))
    text = str(j.get("text") or "")
    if text.strip():
        try:
            items = json.loads(text).get("items")
            assert isinstance(items, list)
        except (ValueError, AttributeError, AssertionError):
            return data(dict(ok=False, error=f"\"{MASTER['name']}\" isn't a master checklist file (checklist_master.json)."))
        verify_mod.MASTER.parent.mkdir(parents=True, exist_ok=True)
        verify_mod.MASTER.write_text(text, encoding="utf-8")
        MASTER["connected"] = True
    else:                                        # a new, empty file: the list as it is now goes into it
        master_save(master_load())
        MASTER["connected"] = True
        _master_to_shared_drive()
    if r.get("_cl_fresh") or r.get("checklist") is None:   # not changed yet: the checklist starts again from the shared list
        r["checklist"] = None
    else:
        _follow_shared_list(r["checklist"], master_load())
    return data(dict(ok=True, items=len(master_load())))


def _follow_shared_list(items: list, shared: list) -> None:
    """The shared file connected to a checklist the preparer already changed (or one saved with the work): the shared list
    decides which lines are master lines. A line marked master that isn't on it (the built-in list, an older list) stays on
    this return only - otherwise the next save would add it to the office's list; the shared lines missing are added.
    (The desktop never needed this: its one master file was always there.)"""
    have = {x["text"].strip() for x in items}
    for x in items:
        on = x["text"].strip() in shared
        if on or x.get("master"):
            x["master"] = x["stays"] = on
    items += [dict(text=t, done=False, stays=True, master=True, note="") for t in shared if t not in have]


# ---------------------------------------------------------------- the review Excel
def _review(r) -> tuple:
    """(file name, the review Excel) - the desktop's review, the same sheets."""
    inc, ded = runcheck.summaries(r)
    docs = fv_mod.effective_docs(r)
    checks = run_checks(r["cy_ret"], inc, ded, docs, r["py"], r.get("sche")) if r.get("cy_ret") else None
    ut = doc_verify(inc, docs, r["ut_scr"], r.get("sche"), r.get("schc")) if r.get("ut_scr") else None
    client = r.get("client") or "Client"
    files = " + ".join(x for x in [(r.get("ut_scr") or {}).get("file"), (r.get("cy_ret") or {}).get("file")] if x)
    content = review_xlsx(client, files, checks, _checklist(r), runcheck.inventory_export(r), ut, r.get("comments"),
                          (r.get("py") or {}).get("expected"), marks=r.get("marks") or {}, inc=inc, ded=ded)
    safe = re.sub(r'[\\/:*?"<>|]+', " ", client).strip()
    return "Review " + str(inc.get("cy_year") or "") + " - " + safe + ".xlsx", content


def save_review(token: str, sent: dict | None = None):
    """Save review (Excel): written into the work-in-progress folder when Chrome lets the app write there (the desktop's
    file window started in that folder); otherwise the page downloads it (review_file)."""
    r = get_run(token)
    if not r.get("cy_ret") and not r.get("ut_scr"):
        return data(dict(error="Check the return first (input screens and / or the 2025 return)."))
    name, content = _review(r)
    folder = writable_folder(r)
    if not folder:
        return data(dict(download=f"/verify/{token}/review.xlsx", file=name))
    out = Path(folder) / name
    out.write_bytes(content)
    write_out(str(out))
    return data(dict(saved=shown_folder(str(out)) + "/" + name))


def review_file(token: str):
    """The review Excel as a download (no folder the app may write in)."""
    r = get_run(token)
    if not r.get("cy_ret") and not r.get("ut_scr"):
        return data(dict(error="Check the return first (input screens and / or the 2025 return)."))
    name, content = _review(r)
    return file(content, name, XLSX)

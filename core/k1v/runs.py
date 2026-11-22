"""runs.py - the K-1 section's runs: reading the K-1 PDFs of a client and keeping them while the program runs.

Moved here unchanged (2026-11-16) from the desktop app's K-1 pages file (desktop/k1v_web.py, archived as python-final).

    make_run(files)         K-1 PDFs -> a run (token); nothing goes to the income summary here
    read_k1_files(files)    [(path, display name)] -> (K-1 dicts, problems, {display name: forms})
    attach_screens(token, path)   the UltraTax input screens -> the K-1 entry check of that run
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from . import prep
from .k1_parser import parse_pdf
from .screen_parser import parse_screens
from .screen_verify import verify_screens
from ..readcache import remember

RUNS: dict = {}          # token -> {"k1s", "k1name", "files", "owner", "state", "scr", "scrname", "result", "manual", "flags", "n1065", "n1120"}


def _is_password_error(e) -> bool:
    c, n = e, 0
    while c is not None and n < 6:                       # pdfplumber wraps pdfminer's error
        if "Password" in type(c).__name__ or "password" in str(c).lower():
            return True
        c = c.__cause__ or c.__context__ or (c.args[0] if c.args and isinstance(c.args[0], BaseException) else None)
        n += 1
    return not str(e).strip() and "Pdfminer" in type(e).__name__    # pdfminer's own message is empty


def _name_password(filename: str) -> str:
    """The password is kept at the end of the file name: '... PW-8wRxFRRM.pdf', '... PW - 8wRxFRRM.pdf'."""
    m = re.search(r"\bPW[\s_]*[-:=]?[\s_]*([A-Za-z0-9!@#$%^&*._]+?)(?:\s*\(\d+\))?\.pdf$", filename or "", re.I)
    return m.group(1).strip("._") if m else ""


def read_k1_files(files, pw: str = ""):
    """files: [(path on disk, display name)] -> (K-1 dicts, problems, {display name: number of K-1s}).
    A password at the end of the name ('... PW-8wRxFRRM.pdf') is tried first. Pages of the 2nd file are 1001+, 3rd 2001+."""
    try:
        from core.pdfutil import password_candidates
    except Exception:  # noqa: BLE001
        password_candidates = lambda path, extra=None: []  # noqa: E731
    out, problems, counts = [], [], {}
    for n, (path, name) in enumerate(files):
        got, err = None, None
        for cand in dict.fromkeys([_name_password(name), pw, *password_candidates(Path(name)), ""]):
            try:
                got = remember("K-1s", path, lambda: parse_pdf(str(path), password=cand), cand)   # (read once - core/readcache.py)
                break
            except Exception as e1:  # noqa: BLE001
                err = e1
                if not _is_password_error(e1):
                    break
        if got is None:
            if _is_password_error(err):
                problems.append(f"{name} is password-protected — the password at the end of the file name (PW-…) didn't open it")
            else:
                problems.append(f"{name} couldn't be read ({type(err).__name__}: {err})")
            continue
        counts[name] = [k.form for k in got]
        for k in got:
            d = k.to_dict()
            d["page"] += 1000 * n
            out.append(prep.assign_lids(d))
    return out, problems, counts


def _fill(run, files):
    """(Re-)reads the run's K-1 files: [(path, display name)]."""
    k1s, problems, counts = read_k1_files(files)
    run.update(files=list(files), k1s=k1s, problems=problems, k1name=" + ".join(n for _, n in files),
               n1065=sum(1 for k in k1s if k.get("form") == "1065"), n1120=sum(1 for k in k1s if k.get("form") == "1120-S"))
    return counts


def make_run(files, scr_path=None, scr_name=None, owner=None, state=None):
    """Used by the 1040: the K-1 files found among its documents go through the same engine as this page.
    Returns (token, problems, counts) - a run is made even when nothing was read (more K-1s can be added on the page).
    Nothing goes to the income summary here: that waits for "Add to Income Summary"."""
    run = {"result": None, "manual": {}, "flags": {}, "scr": None, "scrname": None, "owner": owner, "state": state}
    counts = _fill(run, files)
    token = uuid.uuid4().hex[:12]
    RUNS[token] = run
    if scr_path:
        attach_screens(token, scr_path, scr_name)
    return token, run["problems"], counts


def file_ids(run) -> list:
    """The fingerprint of each K-1 file of the run (same rule as the 1040's documents: the first 16 characters of the SHA-1)."""
    import hashlib
    out = []
    for p, _ in run.get("files") or []:
        try:
            h = hashlib.sha1(Path(p).read_bytes()).hexdigest()[:16]
        except OSError:
            h = ""
        out.append(h)
    return out


def run_for(owner):
    """The K-1 run of a 1040 run (token, run) - or (None, None)."""
    return next(((t, x) for t, x in RUNS.items() if owner and x.get("owner") == owner), (None, None))


def attach_screens(token, path, name=None) -> str:
    """The UltraTax Input Screens PDF -> the K-1 entry check of that run. Returns an error text ('' = ok), also kept in the
    run as run["scr_error"] (None = ok): Verify return's K-1 section shows why there is no K-1 check (brief 2026-11-21)."""
    run = RUNS.get(token)
    if not run:
        return "run not found"
    err = ""
    try:
        scr = parse_screens(str(path))
        if not scr["units"]:
            err = "No K-1 input screens (K1, K1-2 …) found in the input screens PDF."
        else:
            run["scr"], run["scrname"] = scr, name or Path(path).name
            run["result"] = verify_screens(prep.for_check(run), scr)
    except Exception as e:  # noqa: BLE001
        err = f"Couldn't read the input screens for the K-1 check: {type(e).__name__}: {e}"
    run["scr_error"] = err or None
    return err


def set_owner(token, owner) -> None:
    run = RUNS.get(token)
    if run:
        run["owner"] = owner

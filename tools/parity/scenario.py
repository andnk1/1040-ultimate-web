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
    with_doc = [x for x in rows if x.get("doc_cy") is not None and x.get("id")]
    docs = [d for d in r["inv"]["docs"] if d.get("family") != "pyreturn"]
    first_sec = inc["sections"][0]["key"]
    out = []
    if with_doc:                                       # a corrected amount (typed over), with a note
        x = with_doc[0]
        out.append(("/edits/{token}", {x["id"]: {"cy": round(x["doc_cy"] + 100, 2), "note": "corrected in the test"}}))
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


# ---------------------------------------------------------------- what is compared
_PATHISH = re.compile(r"^(?:[A-Za-z]:[\\/]|/|\\\\).+")
_CLOCK = re.compile(r"\d{4}-\d\d-\d\d \d\d:\d\d(:\d\d)?")      # "2026-11-17 17:19" - a time stamp


def normalize(value):
    """What both apps keep, made comparable: file paths become file names (the archive ran from C:\\..., this app from its
    own folders); clock times are left out (when the work was saved, when the K-1s were added). Everything else must be the
    same."""
    def walk(v):
        if isinstance(v, dict):
            return {walk(k) if isinstance(k, str) else k: walk(x) for k, x in v.items()
                    if k != "saved" and not (isinstance(x, str) and _CLOCK.fullmatch(x))}
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, str) and _PATHISH.match(v):
            return v.replace("\\", "/").rsplit("/", 1)[-1]
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

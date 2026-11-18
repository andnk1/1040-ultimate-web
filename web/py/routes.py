"""routes.py - which Python function answers each address of the pages.

The templates and their scripts were written for the desktop app's server: a link goes to /summary/<run>, a save posts to
/edits/<run>, a download is /sche/<run>/template.xlsx. In the browser app the same addresses stay - the page frame hands each
one to the worker, and handle() below looks it up in ROUTES and calls the function named there.

    ROUTES      the table: (method, address pattern, function). <name> in a pattern = a part passed to the function.
    handle()    one address -> the reply as a plain dict the worker passes to the page (see web/index.html)

Addresses not in the table yet: a page shows "Not in the browser app yet"; a save answers "not saved yet" - those pages are
converted one at a time (design/conversion_plan.md). After a save in AUTOSAVE the work in progress is saved.
"""
from __future__ import annotations

import json
import re
from urllib.parse import unquote

from pages import NotFound, Reply, data, get_run, not_yet, save_work
from pages import ai, documents, k1, summary, verify

ROUTES = [
    # method  address                               function                      what it is
    ("GET",  "/summary/<token>",                    summary.show),                # 1 · Summary
    ("GET",  "/sche/template.xlsx",                 summary.schedule_e_template), # Schedule E box → Blank template
    ("GET",  "/sche/<token>/template.xlsx",         summary.schedule_e_template), # Schedule E box → Export Template
    ("GET",  "/verify/<token>",                     verify.show),                 # 2 · Verify return (not yet)
    ("GET",  "/ai/<token>",                         ai.doc_review),               # 3 · AI Doc Review (waits for the key)
    ("GET",  "/ai-return/<token>",                  ai.return_review),            # 4 · AI Return Review
    ("GET",  "/ai-advisory/<token>",                ai.advisory),                 # 5 · AI Advisory
    ("GET",  "/k1v/",                               k1.home),                     # K-1 Verification (not yet)
    ("GET",  "/open",                               documents.open_document),     # a source document in a new tab
    # the Summary's saves (each followed by saving the work in progress - AUTOSAVE below)
    ("POST", "/edits/<token>",                      summary.save_edits),          # corrected amounts, Fed. w/h
    ("POST", "/edits/<token>/confirm",              summary.confirm_edit),        # Re-confirm a correction
    ("POST", "/added/<token>",                      summary.save_added),          # + lines on the income summary
    ("POST", "/carryadd/<token>",                   summary.save_carry_added),    # + lines in the carryovers box
    ("POST", "/comments/<token>",                   summary.save_comments),       # Return Comments, "received?" comments
    ("POST", "/marks/<token>",                      summary.save_marks),          # ticks and comments on any line
    ("POST", "/inventory/<token>",                  summary.save_inventory),      # Document inventory: Verified, amounts, notes, + lines
    ("POST", "/invnote/<token>",                    summary.save_invnote),        # an inventory line's comment typed on the summary
    ("POST", "/toai/<token>",                       summary.save_toai),           # the AI ticks
    ("POST", "/wip/<token>/save",                   summary.wip_save),            # Save work in progress (button)
    ("POST", "/wip/<token>/folder",                 summary.wip_folder),          # Choose a folder… (no folder to save in)
    ("POST", "/formview/<token>/<form>",            summary.save_formview),       # form tabs (W2, 1098-M): corrections
    ("POST", "/ut/<token>",                         summary.save_ut),             # UT summary: fields typed over
    ("POST", "/schc/<token>",                       summary.save_schc),           # Schedule C box
    ("POST", "/pl/<token>",                         summary.load_pl),             # Schedule C box → Add P&L…
    ("GET",  "/schc/<token>/<i>/<which>.csv",       summary.schedule_c_csv),      # Schedule C box → the three downloads
    ("POST", "/sche/<token>",                       summary.save_sche),           # Schedule E box
    ("POST", "/sche/<token>/import",                summary.import_schedule_e),   # Schedule E box → Import Schedule E sheet…
    ("GET",  "/sche/<token>/<i>/workpaper.csv",     summary.schedule_e_csv),      # Schedule E box → a property's workpaper
    ("GET",  "/income/<token>/excel",               summary.income_excel),        # Income and Deduction Summary (Excel)
    ("POST", "/k1/<token>/remove",                  summary.k1_remove),           # K-1 box → Remove
]

# after these saves the work in progress is saved (the desktop app did the same after every change)
AUTOSAVE = {summary.save_edits, summary.confirm_edit, summary.save_added, summary.save_carry_added, summary.save_comments,
            summary.save_marks, summary.save_inventory, summary.save_invnote, summary.save_toai, summary.save_formview,
            summary.save_ut, summary.save_schc, summary.save_sche, summary.k1_remove}


def _pattern(address: str) -> re.Pattern:
    """'/summary/<token>' -> a regular expression that matches '/summary/3f9a1c0b2d4e' and names the part 'token'."""
    return re.compile("^" + re.sub(r"<(\w+)>", r"(?P<\1>[^/]+)", re.escape(address).replace(r"\<", "<").replace(r"\>", ">")) + "$")


_TABLE = [(m, _pattern(a), fn) for m, a, fn in ROUTES]


def find(method: str, path: str):
    """(function, {part: value}) for an address, or (None, {})."""
    for m, rx, fn in _TABLE:
        hit = rx.match(path)
        if m == method and hit:
            return fn, {k: unquote(v) for k, v in hit.groupdict().items()}
    return None, {}


def handle(method: str, url: str, body: str = "") -> dict:
    """One request from the page -> {kind, status, body, filename, mime, inline, note}. body = what a save sent (JSON text)."""
    path, _, query = url.partition("?")
    method = method.upper()
    fn, parts = find(method, path)
    try:
        if fn is None:
            reply = _not_converted(method, path)
        else:
            if fn is documents.open_document:          # /open?path=...: the path is in the query
                parts = {"path": unquote(query.partition("path=")[2].split("&")[0])}
            elif fn is k1.home:
                parts = {"query": query}
            if method == "POST":
                parts["sent"] = json.loads(body) if body else {}
            reply = fn(**parts)
            if fn in AUTOSAVE and reply.status == 200:
                save_work(get_run(parts["token"]))
    except NotFound as e:
        reply = (Reply("json", {"error": str(e)}, status=404) if method == "POST"
                 else not_yet("", "", "Can't show this", str(e), lead=""))
    return dict(kind=reply.kind, status=reply.status, body=reply.body, filename=reply.filename, mime=reply.mime,
                inline=reply.inline, note=reply.note)


def _not_converted(method: str, path: str) -> Reply:
    """An address whose page isn't converted yet."""
    if method == "POST":                               # a save from a page that is shown read-only for now
        return data({"ok": True, "saved": False}, note="Not saved — saving comes with the next step of the conversion.")
    token = next((p for p in path.split("/") if re.fullmatch(r"[0-9a-f]{12}", p)), "")
    return not_yet(token, "", "Not in the browser app yet", f"This part of the program ({path}) comes with a later step "
                   "of the conversion plan.")

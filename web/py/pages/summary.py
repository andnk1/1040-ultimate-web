"""summary.py - page 1 · Summary (templates/summary.html), and its downloads.

Today the page is shown read-only: what Run check read, the inventory, the income and deduction summary. Its saves
(corrections, ticks, comments ...) come with the next steps of design/conversion_plan.md.
"""
from __future__ import annotations

import io
import json

from core import runcheck
from core.inventory import ROUTE_LBL
from core.pl import MAP_LINES as PL_MAP_LINES
from core.py_return import SCHC_LINES, SCHE_LINES

from . import file, get_run, page, render

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

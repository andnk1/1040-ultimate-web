"""test_perdoc.py - per document = every source, corrected amount = the preparer's override, the stale-correction flag
(pending items 1-3, 2026-11-03). Runs on core/income.py directly (no documents needed)."""
from __future__ import annotations

import harness as h  # noqa: F401 - puts the app folder on the path

from core.income import build_income_summary, build_deduction_summary, stamp_edits, per_doc


def _rows(inc):
    return {x["id"]: x for s in inc["sections"] for x in s["rows"]}


SCHC = [dict(name="Consulting", py={"31": 100}, calculated=True, totals={"31": 5000.0})]
SCHE = [dict(name="12 Main St", py={"21": 1}, calculated=True, totals={"net": -1200.0})]
INV = [dict(id="inv|abc123", sec="other", doc="letter.pdf", file="letter.pdf", cy=750.0, fit=None, note="", inv=True),
       dict(id="add|other|1", sec="other", doc="typed line", cy=300.0, fit=None, note="")]


def build(schc=SCHC, sche=SCHE, added=INV, edits=None):
    return build_income_summary({}, [], schc, 2024, 2025, edits, added, sche=sche)


def test_schedule_c_and_e_fill_per_document():
    rows = _rows(build())
    c, e = rows["schc||Consulting"], rows["rental||12 Main St"]
    assert c["doc_cy"] == c["cy"] == 5000.0 and not c["differs"]
    assert e["doc_cy"] == e["cy"] == -1200.0 and e["sche"] == 0 and "schc" not in e     # its own marker (no schc=-1-i)


def test_inventory_amount_is_per_document_and_plus_line_is_not():
    rows = _rows(build())
    inv, plus = rows["inv|abc123"], rows["add|other|1"]
    assert inv["doc_cy"] == inv["cy"] == 750.0 and not inv.get("added") and inv["source"] == "document inventory"
    assert plus["doc_cy"] is None and plus["cy"] == 300.0 and plus["added"]


def test_correction_wins_and_stale_flag():
    inc = build()
    edits = stamp_edits({"schc||Consulting": {"cy": 4800.0}, "inv|abc123": {"cy": 700.0}}, {}, per_doc(inc))
    assert edits["schc||Consulting"]["base"] == 5000.0 and edits["inv|abc123"]["base"] == 750.0
    rows = _rows(build(edits=edits))
    c = rows["schc||Consulting"]
    assert c["cy"] == 4800.0 and c["doc_cy"] == 5000.0 and c["differs"] and not c.get("stale")
    # Schedule C recalculated / inventory amount changed: the corrections stay, flagged
    schc2 = [dict(SCHC[0], totals={"31": 5600.0})]
    inv2 = [dict(INV[0], cy=900.0), INV[1]]
    rows = _rows(build(schc=schc2, added=inv2, edits=edits))
    assert rows["schc||Consulting"]["cy"] == 4800.0 and rows["schc||Consulting"]["stale"]
    assert rows["inv|abc123"]["cy"] == 700.0 and rows["inv|abc123"]["stale"]
    # the same correction posted again keeps its base (still stale); re-confirmed (new base) it isn't
    inc2 = build(schc=schc2, added=inv2, edits=edits)
    again = stamp_edits({"schc||Consulting": {"cy": 4800.0}}, edits, per_doc(inc2))
    assert again["schc||Consulting"]["base"] == 5000.0
    again["schc||Consulting"]["base"] = 5600.0
    assert not _rows(build(schc=schc2, added=inv2, edits=again))["schc||Consulting"].get("stale")
    # a changed correction takes the current per document as its base
    changed = stamp_edits({"schc||Consulting": {"cy": 5500.0}}, edits, per_doc(inc2))
    assert changed["schc||Consulting"]["base"] == 5600.0


def test_old_correction_without_base_is_not_flagged():
    rows = _rows(build(edits={"schc||Consulting": {"cy": 1.0}}))
    assert rows["schc||Consulting"]["cy"] == 1.0 and not rows["schc||Consulting"].get("stale")


def test_deduction_summary_inventory_line():
    ded = build_deduction_summary({}, [], 2024, 2025, None,
                                  [dict(id="inv|m1", sec="mortgage", doc="1098 scan.pdf", file="1098 scan.pdf", cy=9000.0, inv=True)])
    r = _rows(ded)["inv|m1"]
    assert r["doc_cy"] == r["cy"] == 9000.0

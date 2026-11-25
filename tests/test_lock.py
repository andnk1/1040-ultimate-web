"""test_lock.py - a document the program read is corrected on its own screen, not on the Summary (Lady, 2026-11-24).

On the Income and Deduction Summary the rows of read documents and K-1 lines are read-only (their Fed. w/h too) and say where
to change them (core/income.py where_to_correct); typing there shows a warning (templates/summary.html). A save that still
carries a new amount for such a row keeps only its comment (web/py/pages/summary.py _without_locked). A correction saved
before the lock (an older work in progress) is kept: it still counts, and the row says to move it.
Rows that stay typeable: not-read documents, lines added with +, the Schedule C / E box results, the crypto reports (no
screen of their own yet). Inventory lines were read-only on the Summary already.
"""
from __future__ import annotations

import pytest

import harness as h

CASE = h.SAMPLES / "Sample"


@pytest.fixture(scope="module")
def run():
    if not (CASE / h.KEY_NAME).exists():
        pytest.skip("the Sample case isn't on this computer")
    return h.open_run(h.run_case(CASE, h.load_key(CASE / h.KEY_NAME)["roles"]))


def _rows(r):
    from core import runcheck
    inc, ded = runcheck.summaries(r)
    return [x for t in (inc, ded) for s in t["sections"] for x in s["rows"]]


def _row(r, rid):
    return next(x for x in _rows(r) if x["id"] == rid)


def test_which_rows_lock(run):
    fam = {d["file"]: d.get("family") for d in run["inv"]["docs"]}
    rows = _rows(run)
    w2 = [x for x in rows if fam.get(x["file"]) == "w2"]
    assert w2 and all(x["lock"] == "the W2 tab (Document inventory)" for x in w2)
    assert all(x["lock"] == "K-1 UT (Open K-1 Tab)" for x in rows if x["file"].startswith("k1v:"))
    assert any(x["file"].startswith("k1v:") for x in rows)
    assert all(x["lock"] for x in rows if fam.get(x["file"]) in ("composite", "1099r", "1098"))
    assert all(not x["lock"] for x in rows if fam.get(x["file"]) == "koinly" or x.get("sche") is not None)


def test_new_amount_on_a_read_row_is_refused(run):
    x = next(x for x in _rows(run) if x["lock"] and x.get("doc_cy"))
    reply = h.page("POST", f"/edits/{run['token']}", {x["id"]: {"cy": x["doc_cy"] + 500, "note": "typed anyway"}})
    assert reply["status"] == 200
    assert "cy" not in (run.get("edits") or {}).get(x["id"], {})            # the amount isn't taken
    assert run["edits"][x["id"]]["note"] == "typed anyway"                  # the comment is
    assert _row(run, x["id"])["cy"] == x["doc_cy"]


def test_typeable_row_still_takes_an_amount(run):
    x = next(x for x in _rows(run) if not x["lock"] and x.get("doc_cy") is not None and not x.get("inv") and not x.get("added"))
    h.page("POST", f"/edits/{run['token']}", {x["id"]: {"cy": round(x["doc_cy"] + 1, 2)}})
    assert _row(run, x["id"])["cy"] == round(x["doc_cy"] + 1, 2)
    run["edits"] = {}


def test_correction_saved_before_the_lock_is_kept(run):
    x = next(x for x in _rows(run) if x["lock"] and x.get("doc_cy"))
    run["edits"] = {x["id"]: {"cy": x["doc_cy"] + 7, "base": x["doc_cy"]}}  # as an older work in progress holds it
    row = _row(run, x["id"])
    assert row["cy"] == x["doc_cy"] + 7 and row["kept"]
    h.page("POST", f"/edits/{run['token']}", {x["id"]: {"cy": x["doc_cy"] + 7}})          # the page sends it back unchanged
    assert _row(run, x["id"])["cy"] == x["doc_cy"] + 7
    h.page("POST", f"/edits/{run['token']}", {x["id"]: {"cy": x["doc_cy"] + 99}})         # a new amount: still refused
    assert _row(run, x["id"])["cy"] == x["doc_cy"] + 7
    page = h.page("GET", f"/summary/{run['token']}")["body"]
    assert "corrected here before amounts from documents were locked" in page
    run["edits"] = {}


def test_the_page_draws_locked_boxes(run):
    page = h.page("GET", f"/summary/{run['token']}")["body"]
    assert 'class="amt cyin locked"' in page and 'data-lock="the W2 tab (Document inventory)"' in page
    assert "function lockWarn" in page

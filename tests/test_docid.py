"""test_docid.py - saved work keyed by the documents' fingerprints (core/docid.py), on a copy of four Sample documents:
an older work-in-progress file is converted, a renamed file keeps its work, a re-saved file keeps it with "check", a replaced
file shows the message and starts clean."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import harness as h

# Waits for its page: these tests drove the desktop app's pages (app.py / the K-1 web file, archived as python-final).
# They come back, unchanged in what they check, when that page is converted - design\conversion_plan.md.
pytestmark = pytest.mark.skip(reason="waits for the work in progress (Continue / Start fresh) - conversion plan, page 1")

SRC = h.SAMPLES / "Sample"
W2 = "1.2025 W2_sample.pdf"
W2B = "2. Anonymus_2025_ FORM W-2 (LEDGER)_sample.pdf"
INT = "5. 1099_8W12GMF7-WB_LO (Wealthfront xGMF7)_sample.pdf"
DIV = "6. 1099_8W238483-WB_LO (Wealthfront x8483)_sample (2).pdf"
OLD_WIP = h.HERE / "fixtures" / "sample_wip_v1.json"      # a version-1 WIP of the Sample case (keys from file names), frozen


def _run(folder: Path, names: list, wip: dict):
    a = h._app()
    import core.wip as wip_mod
    wp = folder / "wip.json"
    wp.write_text(json.dumps(wip), encoding="utf-8")
    c = a.app.test_client()
    resp = c.post("/run", data=dict(mode="summary", pyret="", utscreens="", karbon="", clientsum="", wip=str(wp),
                                    docs=json.dumps([dict(path=str(folder / n), on=True) for n in names])))
    tok = (resp.headers.get("Location") or "").rsplit("/", 1)[-1]
    assert tok in a.RUNS, resp.get_data(as_text=True)[:500]
    r = a.RUNS[tok]
    return r, json.loads(json.dumps(wip_mod.snapshot(r), default=str)), c


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    if not OLD_WIP.exists():
        pytest.skip("the Sample work-in-progress file isn't there")
    folder = tmp_path_factory.mktemp("docid")
    for n in (W2, W2B, INT, DIV):
        shutil.copy2(SRC / n, folder / n)
    old = json.loads(OLD_WIP.read_text(encoding="utf-8"))
    old["form"] = dict(old["form"], pyret="", karbon="", clientsum="", utscreens="")
    old["docs"] = [dict(path=str(folder / n), on=True) for n in (W2, W2B, INT, DIV)]
    old["ut_path"] = ""
    # work an older file could hold: a corrected amount, a tick and a note on the inventory, a form-tab correction
    old["edits"] = {f"w2|{W2}|ADP (payroll) — {W2[:-4]}": {"cy": 700000.0}}
    old["marks"][f"inc|w2|{W2}|ADP (payroll) — {W2[:-4]}"] = True
    old["invstate"] = dict(verified={str(folder / INT): True}, amt={}, notes={str(folder / DIV): "note on 6"}, free=[])
    old["formview"] = {"w2": {f"{folder / W2B}#0": {"b1": 66000.0}}}
    old["to_ai"] = {str(folder / DIV): True}
    return folder, old


def _did(r, name):
    return next(d["did"] for d in r["inv"]["docs"] if d["file"] == name)


def test_old_wip_converted(case):
    folder, old = case
    r, snap, _ = _run(folder, [W2, W2B, INT, DIV], old)
    w2, w2b, i5, d6 = (_did(r, n) for n in (W2, W2B, INT, DIV))
    assert snap["version"] == 2 and set(snap["fps"]) >= {w2, w2b, i5, d6}
    assert r["edits"] == {f"w2|{w2}": {"cy": 700000.0}}
    m = r["marks"]
    assert m.get(f"inc|w2|{w2}") and m.get(f"v|interest|{i5}|main") and m.get(f"v|dividends|{d6}|div_7")
    assert m.get(f"n|v|interest|{i5}|main") == "adffg" and m.get(f"n|v|dividends|{d6}|div_7") == "sdfg"
    assert r["invstate"]["verified"] == {i5: True} and r["invstate"]["notes"] == {d6: "note on 6"}
    assert r["formview"] == {"w2": {f"{w2b}#0": {"b1": 66000.0}}}
    assert r["to_ai"].get(str(folder / DIV)) is True and snap["to_ai"].get(d6) is True
    assert not r.get("docnotes")
    # the corrected amount and the form-tab correction reach the income summary under the new keys
    inc, _ = h._app()._summaries(r)
    rows = {x["id"]: x for s in inc["sections"] for x in s["rows"]}
    assert rows[f"w2|{w2}"]["cy"] == 700000.0 and rows[f"w2|{w2b}"]["cy"] == 66000.0
    case[1].clear()
    case[1].update(snap)                                  # the converted file is the starting point of the next tests


def test_renamed_file_keeps_its_work(case):
    folder, wip = case
    (folder / W2).rename(folder / "W-2 renamed.pdf")
    r, snap, _ = _run(folder, ["W-2 renamed.pdf", W2B, INT, DIV], wip)
    w2 = _did(r, "W-2 renamed.pdf")
    assert r["edits"] == {f"w2|{w2}": {"cy": 700000.0}} and r["marks"].get(f"inc|w2|{w2}")
    assert not r.get("docnotes")
    (folder / "W-2 renamed.pdf").rename(folder / W2)


def test_resaved_file_matched_by_name(case):
    import pymupdf
    folder, wip = case
    old_did = next(k for k, v in wip["fps"].items() if v["file"] == INT)
    doc = pymupdf.open(folder / INT)
    doc.save(folder / "tmp.pdf", garbage=4, deflate=True)       # other bytes, same text
    doc.close()
    (folder / "tmp.pdf").replace(folder / INT)
    r, snap, c = _run(folder, [W2, W2B, INT, DIV], wip)
    new = _did(r, INT)
    assert new != old_did
    assert r["marks"].get(f"v|interest|{new}|main") and r["marks"].get(f"n|v|interest|{new}|main") == "adffg"
    assert "matched by name" in r["docnotes"][new]
    assert new not in r["invstate"]["verified"]                  # verify it again
    html = c.get(f"/summary/{r['token']}").get_data(as_text=True)
    assert "matched by name" in html and "Documents changed since your work was saved" in html
    wip.clear()
    wip.update(snap)


def test_replaced_file_starts_clean(case):
    folder, wip = case
    shutil.copy2(SRC / "3. Anonymus_2025_FORM 1099-R (FIDELITY IRA)_sample.pdf", folder / DIV)   # same name, other document
    r, snap, c = _run(folder, [W2, W2B, INT, DIV], wip)
    new = _did(r, DIV)
    assert "was replaced" in r["docnotes"][new]
    assert not any(new in k for k in r["marks"]) and new not in r["invstate"]["notes"]
    old_did = next(k for k, v in wip["fps"].items() if v["file"] == DIV)
    assert old_did in snap["fps"] and any(old_did in k for k in snap["marks"])     # the old version's work stays in the file
    # ticking the document Verified takes the note away
    st = dict(verified={new: True}, amt={}, notes={}, free=[])
    c.post(f"/inventory/{r['token']}", json=st)
    assert new not in r["docnotes"]

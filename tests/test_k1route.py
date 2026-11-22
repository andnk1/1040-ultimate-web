"""test_k1route.py - K-1s: one route (pending item 5, 2026-11-03), on copies of the Sample K-1 PDFs.
Nothing reaches the income summary until "Add to Income Summary"; the K-1 page is opened from the 1040 (?for=<run>); the package
and the K-1 page's work are saved (WIP + K-1 work file) and come back when the client is opened again."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import harness as h

# The desktop's tests (archive python-final), unchanged in what they check: the addresses now go through the browser app's
# route table (tests/harness.py Client - the page frame's way).

SRC = h.SAMPLES / "Sample"


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    k1s = sorted(p.name for p in SRC.glob("*.pdf") if "K-1" in p.name)
    if len(k1s) < 2:
        pytest.skip("the Sample K-1 PDFs aren't there")
    folder = tmp_path_factory.mktemp("k1route")
    for n in k1s:
        shutil.copy2(SRC / n, folder / n)
    a = h._app()
    c = a.app.test_client()
    resp = c.post("/run", data=dict(mode="summary", pyret="", utscreens="", karbon="", clientsum="", wip="",
                                    docs=json.dumps([dict(path=str(folder / n), on=True) for n in k1s])))
    tok = resp.headers["Location"].rsplit("/", 1)[-1]
    r = a.RUNS[tok]
    r["wip_path"] = str(folder / "1040 Ultimate WIP 2025 - Test.json")        # the K-1 work file goes next to it
    return dict(folder=folder, files=k1s, r=r, c=c, a=a)


def _k1_rows(r):
    inc, _ = h._app()._summaries(r)
    return {x["id"]: x for s in inc["sections"] for x in s["rows"] if x["id"].startswith("k1|")}


def test_nothing_counts_before_add(case):
    r, a = case["r"], case["a"]
    assert r.get("k1") is None and not _k1_rows(r)
    st = a.k1_status(r)
    assert st["found"] and not st["pkg"]
    html = case["c"].get(f"/summary/{r['token']}").get_data(as_text=True)
    assert "K-1 documents found, review K-1's tab" in html and f"/k1v/?for={r['token']}" in html and "k1frame" not in html
    assert html.count("K-1 documents found") == 1          # in the K-1 box only - not a problem, so not in the box at the top
    assert all("K-1 section" in (d.get("note") or "") for d in r["inv"]["docs"] if d.get("route") == "k1v")


def test_k1_page_opened_from_the_1040(case):
    r, c, a = case["r"], case["c"], case["a"]
    html = c.get(f"/k1v/?for={r['token']}").get_data(as_text=True)
    assert "Add K-1 PDFs" in html and all(n in html for n in case["files"])
    tok, run = a.k1v_web.run_for(r["token"])
    assert tok == r["k1v_token"] and run["owner"] == r["token"]
    page = c.get(f"/k1v/k1/{tok}").get_data(as_text=True)
    assert "Add to Income Summary" in page and "Upload to 1040" not in page


def test_add_to_income_summary(case):
    r, c, a = case["r"], case["c"], case["a"]
    tok, run = a.k1v_web.run_for(r["token"])
    k1s = [k for k in run["k1s"] if k.get("form") == "1065"]
    from core.k1v.k1_summary import build_summary
    rid = next(x["rid"] for s in build_summary(k1s)["sections"] for x in s["rows"] if x["amt"])
    state = {"corr": {rid: "12345"}, "items": {"x": {"v": True, "c": "seen"}}}
    j = c.post(f"/k1v/add/{tok}", json=dict(k1s=k1s, state=state)).get_json()
    assert j["ok"] and r["k1"]["n"] == len(k1s)
    rows = _k1_rows(r)
    assert rows and all(k.startswith("k1|") for k in rows)
    assert not any(n in k for k in rows for n in case["files"])                   # never by file name (rename-proof)
    hit = next(x for x in rows.values() if x["cy"] == 12345.0)
    assert hit["doc_cy"] != 12345.0 and hit["differs"]                            # read = per document, K-1 page correction wins
    # saved: the K-1 work file next to the WIP (files + the page's work)
    k1w = json.loads(Path(r["wip_path"].replace("1040 Ultimate WIP", "1040 Ultimate K-1 WIP")).read_text(encoding="utf-8"))
    assert k1w["state"]["corr"] == {rid: "12345"} and len(k1w["files"]) == len(case["files"])
    assert not a.k1_status(r)["changed"]
    # a change on the K-1 page after adding -> "changed since added"
    c.post(f"/k1v/state/{tok}", json=dict(state, corr={rid: "999"}))
    assert a.k1_status(r)["changed"]
    case["rid"] = rid


def test_saved_and_reopened(case):
    """The client opened again: the package comes back from the WIP, the K-1 page's work from the K-1 work file, and a
    correction typed on a K-1 line of the income summary (keyed by EIN + line) is still there."""
    r, c, a, folder = case["r"], case["c"], case["a"], case["folder"]
    rows = _k1_rows(r)
    key = next(iter(rows))
    r["edits"] = {key: {"cy": 1.0}}
    import core.wip as wip_mod
    snap = json.loads(json.dumps(wip_mod.snapshot(r), default=str))
    Path(r["wip_path"]).write_text(json.dumps(snap), encoding="utf-8")
    resp = c.post("/run", data=dict(mode="summary", pyret="", utscreens="", karbon="", clientsum="", wip=r["wip_path"], docs="[]"))
    r2 = a.RUNS[resp.headers["Location"].rsplit("/", 1)[-1]]
    assert r2["k1"]["rows"] == r["k1"]["rows"]
    run2 = a.k1v_web.RUNS[r2["k1v_token"]]
    assert run2["owner"] == r2["token"] and run2["state"]["corr"] == {case["rid"]: "999"}
    assert _k1_rows(r2)[key]["cy"] == 1.0
    case["r2"] = r2


def test_remove(case):
    r2, c, a = case["r2"], case["c"], case["a"]
    c.post(f"/k1/{r2['token']}/remove")
    assert r2["k1"] is None and not _k1_rows(r2) and not a.k1_status(r2)["pkg"]


def test_standalone_page_cannot_add():
    a = h._app()
    tok, _, _ = a.k1v_web.make_run([])
    j = a.app.test_client().post(f"/k1v/add/{tok}", json=dict(k1s=[{"form": "1065", "page": 1, "lines": []}]))
    assert j.status_code == 400

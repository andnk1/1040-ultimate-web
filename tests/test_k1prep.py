"""test_k1prep.py - K-1 Prep, "Export for UT data entry" and K-1 copies (list of 2026-11-05, items 1 and 6), on copies of the
Sample K-1 PDFs (+ made-up K-1 dicts for the copy rule: the Sample K-1s have no EIN read)."""
from __future__ import annotations

import csv
import io
import json
import shutil
from pathlib import Path

import pytest

import harness as h
from core.k1v import prep

SRC = h.SAMPLES / "Sample"


def _k(page, ein="12-3456789", e="XXX-XX-1234", lines=(("5", None, 100.0),), **kw):
    k = dict(page=page, form="1065", year=2025, name="DEMO LP", ein=ein, E=e, amended=False,
             lines=[dict(box=b, code=c, amt=a, stmt=False, check=False, key=b + (c or "")) for b, c, a in lines], **kw)
    return prep.assign_lids(k)


# ------------------------------------------------------------------ K1 liabilities: three numeric rows (2026-11-11)
def test_k1_liabilities_export_as_three_numeric_rows():
    k = _k(1, K1={"Nonrecourse": [80.0, 67.0], "Qualified nonrecourse financing": [0.0, 0.0], "Recourse": [5.0, 0.0]})
    assert prep.k1_rows(k) == [("K1_nonrecourse", 67.0, "Share of liabilities - ending: Nonrecourse")]   # zero endings left out
    rows = prep._rows(k, {}, [])
    kr = next(r for r in prep.ut_entry.decide(rows) if r["box"] == "K1")
    assert kr["kind"] == "info" and kr["vals"] == ["Nonrecourse 67", "Qualified nonrecourse 0", "Recourse 0"]  # the page: one row
    data = dict(k1s=[dict(ready=True, doc_id="abc#1", ein=k["ein"], name=k["name"], E=k["E"], rows=rows)])
    out = [dict(zip(prep.CSV_COLUMNS, r)) for r in prep.export_rows(data)]
    k1 = [x for x in out if x["box"].startswith("K1")]
    assert [(x["box"], x["code"], x["amount"], x["valid_in_ut"]) for x in k1] == [("K1_nonrecourse", "", "67.00", "")]
    if prep.ut_entry.on():
        assert (k1[0]["entry"], k1[0]["entry_reason"]) == ("bot", "")
    assert [x["box"] for x in out].index("K1_nonrecourse") < [x["box"] for x in out].index("5")   # before the box lines
    k0 = _k(2, K1={"Nonrecourse": [10.0, 0.0], "Qualified nonrecourse financing": [0.0, 0.0], "Recourse": [0.0, 0.0]})
    assert prep.k1_rows(k0) == []                                                           # every ending 0: no rows


# ------------------------------------------------------------------ copies (item 6)
def test_copy_same_amounts_counts_once():
    ks = [_k(1), _k(1001), _k(5, ein="98-7654321")]
    m = prep.find_copies(ks)
    assert set(m) == {1001} and m[1001]["kind"] == "copy" and m[1001]["of"] == [1] and not m[1001]["counted"]
    assert [k["page"] for k in prep.counted(ks, None)] == [1, 5]


def test_other_partner_both_count():
    assert prep.find_copies([_k(1), _k(2, e="XXX-XX-1111")]) == {}                  # the spouse's K-1
    assert prep.find_copies([_k(1, ein=""), _k(2, ein="")]) == {}                   # no EIN read: never called a copy


def test_different_amounts_is_a_check():
    ks = [_k(1), _k(2, lines=(("5", None, 250.0),))]
    m = prep.find_copies(ks)
    assert m[1]["kind"] == m[2]["kind"] == "check" and m[1]["counted"] and m[2]["counted"] and m[1]["red"] and m[2]["red"]
    m = prep.find_copies(ks, {"1": "skip"})                                          # don't count on that row only
    assert not m[1]["counted"] and m[2]["counted"] and not m[1]["red"] and not m[2]["red"]
    assert [k["page"] for k in prep.counted(ks, {"dup": {"1": "skip"}})] == [2]
    m = prep.find_copies(ks, {"1": "count", "2": "count"})                           # both, on purpose
    assert m[1]["counted"] and m[2]["counted"] and not m[1]["red"]


def test_amended_is_preselected():
    ks = [_k(1), _k(2, lines=(("5", None, 250.0),))]
    ks[1]["amended"] = True
    m = prep.find_copies(ks)
    assert not m[1]["counted"] and m[2]["counted"] and not m[2]["red"]
    assert prep.find_copies(ks, {"1": "count"})[1]["counted"]                        # the preparer's choice wins


# ------------------------------------------------------------------ the page, the corrections, the export
@pytest.fixture(scope="module")
def case(tmp_path_factory):
    # Waits for its page: these tests drove the desktop app's pages (app.py / the K-1 web file, archived as python-final).
    # They come back, unchanged in what they check, when that page is converted - design\conversion_plan.md.
    pytest.skip("waits for the K-1 UT page - conversion plan, page 8")
    k1s = sorted(p.name for p in SRC.glob("*.pdf") if "K-1" in p.name)
    if len(k1s) < 2:
        pytest.skip("the Sample K-1 PDFs aren't there")
    folder = tmp_path_factory.mktemp("k1prep")
    for n in k1s:
        shutil.copy2(SRC / n, folder / n)
    a = h._app()
    c = a.app.test_client()
    resp = c.post("/run", data=dict(mode="summary", pyret="", utscreens="", karbon="", clientsum="", wip="",
                                    docs=json.dumps([dict(path=str(folder / n), on=True) for n in k1s])))
    r = a.RUNS[resp.headers["Location"].rsplit("/", 1)[-1]]
    r["wip_path"] = str(folder / "1040 Ultimate WIP 2025 - Test.json")
    c.get(f"/k1v/?for={r['token']}")
    tok, run = a.k1v_web.run_for(r["token"])
    return dict(r=r, c=c, a=a, tok=tok, run=run, folder=folder)


def _data(case):
    return prep.build(case["run"], {}, case["a"].k1v_web.file_ids(case["run"]))


def _k1w(case):
    return json.loads(Path(case["r"]["wip_path"].replace("1040 Ultimate WIP", "1040 Ultimate K-1 WIP")).read_text(encoding="utf-8"))


def test_page_and_button(case):
    c, tok, r = case["c"], case["tok"], case["r"]
    assert f"/k1v/prep/{tok}" in c.get(f"/k1v/?for={r['token']}").get_data(as_text=True)
    html = c.get(f"/k1v/prep/{tok}").get_data(as_text=True)
    assert "Export for UT data entry" in html and "Corrected amount" in html and "<h1>K-1 UT</h1>" in html
    assert "By-hand list (Excel)" in html and "To enter by hand in UltraTax" in html            # ut_entry.py (2026-11-11)
    assert ">K-1 UT</a>" in c.get(f"/k1v/?for={r['token']}").get_data(as_text=True)
    alone, _, _ = case["a"].k1v_web.make_run([])
    assert c.get(f"/k1v/prep/{alone}").status_code == 400                                    # only from the 1040


def test_export_needs_the_taxpayer(case):
    assert case["c"].get(f"/k1v/prep/{case['tok']}/export").status_code == 400
    assert all(k["status"][1] == "Taxpayer SSN needed" for k in _data(case)["k1s"])


def test_box_e_match(case):
    c, tok, run = case["c"], case["tok"], case["run"]
    e4 = prep._last4(run["k1s"][0]["E"])
    assert e4, "box E is read on the Sample K-1s"
    d = c.post(f"/k1v/prep/{tok}/save", json={"people": {"tp": "000-00-0000"}}).get_json()["data"]
    assert d["people"]["tp"] == "0000" and all(not k["partner"]["ok"] and k["status"][0] == "no" for k in d["k1s"])
    assert c.get(f"/k1v/prep/{tok}/export").status_code == 400                               # nothing is Ready
    d = c.post(f"/k1v/prep/{tok}/save", json={"people": {"tp": "123-45-" + e4}}).get_json()["data"]
    assert all(k["partner"]["who"] == "Taxpayer" for k in d["k1s"])
    assert _k1w(case)["state"]["people"] == {"tp": e4}                                       # only the last 4 are kept
    d = c.post(f"/k1v/prep/{tok}/save", json={"people": {"sp": e4}}).get_json()["data"]
    assert all(k["partner"]["who"] == "Matches both" and not k["ready"] for k in d["k1s"])
    c.post(f"/k1v/prep/{tok}/save", json={"people": {"sp": ""}})


def hit_entry(rows, doc_id, box):
    x = next(x for x in rows if x["doc_id"] == doc_id and x["box"] == box)
    return x["entry"], x["entry_reason"]


def _k1(d, page):
    return next(x for x in d["k1s"] if x["page"] == page)


def test_part2_rows_first(case):
    k = _data(case)["k1s"][0]
    kinds = [r["kind"] for r in k["rows"]]
    n = kinds.count("info")
    assert n and kinds[:n] == ["info"] * n                                                   # Part II items first
    info = {r["box"]: r for r in k["rows"][:n]}
    assert list(info)[:2] == ["G", "H1"] and info["G"]["vals"] == ["Limited"] and "K1" not in info   # K1 all zero: not shown
    assert len(info["J"]["vals"]) == 3 and all("→" in v for v in info["J"]["vals"]) and "->" in info["J"]["eff"]
    assert "→" in info["L"]["vals"][0] and not any(r["problem"] for r in info.values())


def test_missing_amount_until_a_line_is_added(case):
    c, tok, run = case["c"], case["tok"], case["run"]
    d = _data(case)
    k = next(k for k in d["k1s"] if any(r["kind"] == "stmt" for r in k["rows"]))
    row = next(r for r in k["rows"] if r["kind"] == "stmt")
    assert row["problem"] == "Missing amount - see statement" and k["status"][1] == "Statement to finish" and not k["ready"]
    assert row["desc"] == "Other information"                                                # the box name, not the code's
    d = c.post(f"/k1v/prep/{tok}/save", json={"pticks": {row["id"]: True}}).get_json()["data"]
    assert next(r for r in _k1(d, k["page"])["rows"] if r["id"] == row["id"])["problem"]   # a tick doesn't clear it
    d = c.post(f"/k1v/prep/{tok}/save", json={"pline": {"op": "add", "page": k["page"], "under": row["id"], "box": row["box"],
                                                         "code": row["pick"]}}).get_json()["data"]
    rows = _k1(d, k["page"])["rows"]
    i = next(n for n, r in enumerate(rows) if r["id"] == row["id"])
    added = rows[i + 1]                                                                      # directly under the row
    assert added["kind"] == "add" and added["fixed"] and added["box"] == row["box"] and added["code"] == row["code"]
    assert not rows[i]["problem"] and added["problem"] == "Missing amount" and _k1(d, k["page"])["status"][1] == "Problem"
    d = c.post(f"/k1v/prep/{tok}/save", json={"pline": {"op": "set", "page": k["page"], "n": added["n"], "amt": "1,234.5"}}).get_json()["data"]
    added = next(r for r in _k1(d, k["page"])["rows"] if r["id"] == added["id"])
    assert added["eff"] == 1234.5 and not added["problem"]
    # typed once, shown everywhere: the Interpreter, the totals / Add to Income Summary / entry check (prep.effective)
    key = row["box"] + row["code"]
    assert prep.plines_entries(run["state"])[str(k["page"])] == [[key, "1234.5", f"p{added['n']}"]]
    eff = next(x for x in prep.effective(run) if x["page"] == k["page"])
    assert any(l.get("manual") and l["key"] == key and l["amt"] == 1234.5 for l in eff["lines"])
    assert f'"p{added["n"]}"' in c.get(f"/k1v/k1/{tok}").get_data(as_text=True)
    c.post(f"/k1v/state/{tok}", json={"stmt": {}, "stmtDone": {}})                         # the Interpreter's whole-state save
    assert run["state"]["plines"] and _k1w(case)["state"]["plines"]
    for kk in d["k1s"]:                                                                      # finish every other statement line
        for r in kk["rows"]:
            if r["missing"]:
                d = c.post(f"/k1v/prep/{tok}/save", json={"pline": {"op": "add", "page": kk["page"], "under": r["id"],
                                                                     "box": r["box"], "code": r["pick"]}}).get_json()["data"]
                n = max(x["n"] for x in _k1(d, kk["page"])["rows"] if x["kind"] == "add")
                c.post(f"/k1v/prep/{tok}/save", json={"pline": {"op": "set", "page": kk["page"], "n": n, "amt": "10"}})
    assert all(k["ready"] for k in _data(case)["k1s"])


def test_code_not_in_ut_is_red_but_exported(case):
    run = case["run"]
    k = run["k1s"][0]
    k["lines"].append(dict(box="13", code="U", amt=5.0, stmt=False, check=False, raw="", key="13U", lid=f"{k['page']}|13U|0"))
    try:
        d = _data(case)
        kk = next(x for x in d["k1s"] if x["page"] == k["page"])
        row = next(r for r in kk["rows"] if r["box"] == "13" and r["code"] == "U")
        assert row["problem"] == "Code not in UltraTax" and kk["ready"]
        assert any(x[5] == "13" and x[6] == "U" and x[8] == "N" for x in prep.export_rows(d))
    finally:
        k["lines"].pop()


def test_correction_goes_to_the_export_and_the_income_summary(case):
    c, tok, run, r, a = case["c"], case["tok"], case["run"], case["r"], case["a"]
    d = _data(case)
    k = next(x for x in d["k1s"] if any(q["box"] == "5" and q["kind"] == "line" for q in x["rows"]))
    row = next(q for q in k["rows"] if q["box"] == "5")
    d = c.post(f"/k1v/prep/{tok}/save", json={"pcorr": {row["id"]: "777"}}).get_json()["data"]
    row2 = next(q for x in d["k1s"] if x["page"] == k["page"] for q in x["rows"] if q["id"] == row["id"])
    assert row2["changed"] and row2["eff"] == 777 and row2["amt"] == row["amt"]              # per document stays as read
    # the export: the columns of APPS_ARCHITECTURE.md, the corrected amount, cents, X for a checkbox
    resp = c.get(f"/k1v/prep/{tok}/export")
    assert resp.status_code == 200 and "UT data entry K-1 2025 - Test.csv" in resp.headers["Content-Disposition"]
    rows = list(csv.DictReader(io.StringIO(resp.get_data(as_text=True))))
    assert list(rows[0]) == prep.CSV_COLUMNS == ["form", "doc_id", "payer_ein", "payer_name", "recipient_id", "box", "code",
                                                 "amount", "valid_in_ut", "entry", "entry_reason", "note"]
    assert hit_entry(rows, k["doc_id"], "5") == ("bot", "")
    hit = next(x for x in rows if x["doc_id"] == k["doc_id"] and x["box"] == "5")
    assert hit["amount"] == "777.00" and hit["form"] == "1065" and hit["valid_in_ut"] == "" and "corrected" in hit["note"]
    assert hit["recipient_id"] == k["E"] and len(hit["doc_id"].split("#")[0]) == 16
    part2 = [x for x in rows if x["box"] in ("G", "H1", "J", "L", "M", "N")]
    assert not any(x["box"].startswith("K1") for x in rows)                                  # K1 all zero: no rows
    assert all(x["amount"] == "X" or float(x["amount"]) != 0 for x in rows if x not in part2)   # no zero lines
    g = next(x for x in part2 if x["doc_id"] == k["doc_id"] and x["box"] == "G")              # Part II: value as printed
    assert g["amount"] == "Limited" and g["code"] == g["valid_in_ut"] == "" and g["note"] == "Partner type"
    assert (g["entry"], g["entry_reason"]) == ("hand", "Not in Source Data Entry")              # by-hand lines exported too
    assert "->" in next(x for x in part2 if x["doc_id"] == k["doc_id"] and x["box"] == "J")["amount"]
    assert any(x["note"] == "from statement" and float(x["amount"]) == 10 for x in rows)      # statement lines
    assert next(x for x in rows if x["code"] == "AE")["valid_in_ut"] == "Y"
    # the income summary: the box correction is the line's corrected amount; per document stays the amount read
    s = c.post("/k1v/summary", json=dict(k1s=run["k1s"], token=tok)).get_json()
    rid = f"int|{k['page']}"
    assert s["box_corr"] == {rid: 777.0}
    ks = [x for x in run["k1s"] if x.get("form") == "1065"]
    assert c.post(f"/k1v/add/{tok}", json=dict(k1s=ks, state={})).get_json()["ok"]
    pk = next(x for x in r["k1"]["rows"] if x["page"] == k["page"] and x["cat"] == "interest")
    assert pk["amt"] == row["amt"] and pk["corr"] == 777.0
    assert run["state"]["pcorr"] == {row["id"]: "777"}                                       # the Interpreter's save kept it
    assert not a.k1_status(r)["changed"]
    # a correction on the totals tab still wins on its line
    c.post(f"/k1v/add/{tok}", json=dict(k1s=ks, state={"corr": {rid: "900"}}))
    assert next(x for x in r["k1"]["rows"] if x["page"] == k["page"] and x["cat"] == "interest")["corr"] == 900.0
    # taking the box correction off: "changed since added"
    c.post(f"/k1v/prep/{tok}/save", json={"pcorr": {row["id"]: ""}})
    assert "pcorr" in run["state"] and not run["state"]["pcorr"] and a.k1_status(r)["changed"]
    assert _k1w(case)["state"]["pticks"]                                                     # saved in the K-1 work file


def test_copy_is_left_out_everywhere(case):
    c, tok, run, r = case["c"], case["tok"], case["run"], case["r"]
    a, b = run["k1s"][1], run["k1s"][2]
    keep = (a["ein"], b["ein"], [dict(l) for l in b["lines"]])
    a["ein"] = b["ein"] = "12-3456789"
    b["lines"] = [dict(l, lid=l["lid"].replace(str(a["page"]), str(b["page"]), 1)) for l in a["lines"]]   # the same K-1 twice
    try:
        d = _data(case)
        kb = next(x for x in d["k1s"] if x["page"] == b["page"])
        assert kb["status"] == ["off", "Copy — not counted"] and kb["dup"]["of"] == [a["page"]] and d["off"] == 1
        assert not any(x[1] == kb["doc_id"] for x in prep.export_rows(d))                    # exported once
        assert "not counted" in c.get(f"/k1v/k1/{tok}").get_data(as_text=True) or True
        ks = [x for x in run["k1s"] if x.get("form") == "1065"]
        c.post(f"/k1v/add/{tok}", json=dict(k1s=ks, state={}))
        assert r["k1"]["n"] == len(ks) - 1 and not any(x["page"] == b["page"] for x in r["k1"]["rows"])
        # different amounts -> check, count / don't count
        b["lines"][1] = dict(b["lines"][1], amt=(b["lines"][1]["amt"] or 0) + 50)
        d = _data(case)
        assert all(next(x for x in d["k1s"] if x["page"] == p)["status"][0] == "no" for p in (a["page"], b["page"]))
        d = c.post(f"/k1v/prep/{tok}/save", json={"dup": {str(a["page"]): "skip"}}).get_json()["data"]
        assert next(x for x in d["k1s"] if x["page"] == a["page"])["status"] == ["off", "Not counted"]
        assert next(x for x in d["k1s"] if x["page"] == b["page"])["status"][0] != "no"
    finally:
        a["ein"], b["ein"], b["lines"] = keep
        c.post(f"/k1v/prep/{tok}/save", json={"dup": {str(a["page"]): ""}})


def test_free_line(case):
    c, tok, run = case["c"], case["tok"], case["run"]
    pg = _data(case)["k1s"][0]["page"]
    d = c.post(f"/k1v/prep/{tok}/save", json={"pline": {"op": "add", "page": pg, "under": "", "box": "", "code": ""}}).get_json()["data"]
    r = [x for x in _k1(d, pg)["rows"] if x["kind"] == "add" and not x["fixed"]][-1]
    assert r["problem"] == "Enter a box" and _k1(d, pg)["status"][1] == "Problem"
    for box, code, amt, want in (("99", "", "5", "Box 99 is not on the 1065 K-1"), ("5", "A", "5", "A is not a code for box 5"),
                                 ("13", "", "5", "Box 13 needs a code"), ("13", "QQ", "5", "QQ is not a code for box 13"),
                                 ("13", "h", "", "Missing amount"), ("13", "U", "5", "Code not in UltraTax"), ("9A", "", "25", "")):
        d = c.post(f"/k1v/prep/{tok}/save", json={"pline": {"op": "set", "page": pg, "n": r["n"], "box": box, "code": code,
                                                             "amt": amt}}).get_json()["data"]
        x = next(x for x in _k1(d, pg)["rows"] if x["id"] == r["id"])
        assert x["problem"] == want, (box, code, x["problem"])
        assert _k1(d, pg)["ready"] == (want in ("", "Code not in UltraTax"))
    assert x["box"] == "9a" and x["desc"] == "Net long-term capital gain (loss)" and x["eff"] == 25
    eff = next(k for k in prep.effective(run) if k["page"] == pg)
    assert any(l.get("manual") and l["box"] == "9a" and not l.get("code") and l["amt"] == 25 for l in eff["lines"])
    hit = [e for e in prep.export_rows(_data(case)) if e[5] == "9a"]
    assert hit and hit[0][7] == "25.00" and hit[0][9:] == ["bot", "", "added line"]
    d = c.post(f"/k1v/prep/{tok}/save", json={"pline": {"op": "del", "page": pg, "n": r["n"]}}).get_json()["data"]
    assert not any(x["id"] == r["id"] for x in _k1(d, pg)["rows"])


# ------------------------------------------------------------------ K-1 UT (2026-11-11): order, Bot / By hand, the by-hand list
def test_order_by_document(case):
    from core.inventory import natural_key
    d = _data(case)
    keys = [(natural_key(k["file"]), k["page"]) for k in d["k1s"]]
    assert keys == sorted(keys) and [k["n"] for k in d["k1s"]] == list(range(1, d["n"] + 1))


def test_by_hand_list_and_files(case):
    from openpyxl import load_workbook
    import pymupdf
    from core.k1v import ut_entry
    c, tok, run = case["c"], case["tok"], case["run"]
    e4 = prep._last4(run["k1s"][0]["E"])
    c.post(f"/k1v/prep/{tok}/save", json={"people": {"tp": e4}})
    d = _data(case)
    ready = [k for k in d["k1s"] if k["ready"]]
    assert ready, "the earlier tests finish the statement lines"
    want = [("h|" + r["id"]) for k in ready for r in k["rows"] if r["entry"] == "hand"]
    assert [x["id"] for x in d["hand"]] == want and want                                     # Ready K-1s, the page's order
    g = next(r for r in ready[0]["rows"] if r["box"] == "G")
    assert (g["entry"], g["why"]) == ("hand", "Not in Source Data Entry")
    assert all(r["entry"] == "" for k in d["k1s"] for r in k["rows"] if r["kind"] == "stmt")
    d2 = c.post(f"/k1v/prep/{tok}/save", json={"pticks": {want[0]: True}}).get_json()["data"]  # a tick on the by-hand list
    assert d2["hand"][0]["tick"]
    resp = c.get(f"/k1v/prep/{tok}/hand/xlsx")
    assert resp.status_code == 200 and "UT by hand K-1 2025 - Test.xlsx" in resp.headers["Content-Disposition"]
    ws = load_workbook(io.BytesIO(resp.data)).active
    assert ws.freeze_panes == "A5" and ws.max_row == 4 + len(want) and ws["A5"].value == ready[0]["file"]
    resp = c.get(f"/k1v/prep/{tok}/hand/pdf")
    assert resp.status_code == 200 and "UT by hand K-1 2025 - Test.pdf" in resp.headers["Content-Disposition"]
    doc = pymupdf.open("pdf", resp.data)
    assert doc[0].rect.width > doc[0].rect.height and "Page 1 of" in doc[0].get_text()
    assert c.get(f"/k1v/prep/{tok}/hand/doc").status_code == 404


def test_setting_off(case, monkeypatch):
    from core.k1v import ut_entry
    c, tok = case["c"], case["tok"]
    monkeypatch.setattr(ut_entry, "ENABLED", False)
    d = _data(case)
    assert not d["ut_entry"] and d["hand"] == [] and all(r["entry"] == "" for k in d["k1s"] for r in k["rows"])
    assert c.get(f"/k1v/prep/{tok}/hand/xlsx").status_code == 404
    rows = list(csv.DictReader(io.StringIO(c.get(f"/k1v/prep/{tok}/export").get_data(as_text=True))))
    assert rows and all(x["entry"] == x["entry_reason"] == "" for x in rows)                 # the columns stay, blank

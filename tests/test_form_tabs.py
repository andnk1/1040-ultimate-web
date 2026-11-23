"""Form tabs for every document type (brief design/brief_2026-11-23_form_tabs.md, core/formview.py FAMILIES).

1. Made-up forms: a box corrected on the form tab gives the same result as the reader reading that value (the same PDF made
   again with the other value) - 1099-MISC, 1099-NEC, 1099-R, bank 1099-INT, 1098-E, SSA-1099, 1098-T, a "BOX n:" statement.
2. A made-up parsed result for the forms with no PDF here (1095-A, 1099-SA list values, a composite with Form 8949 box rows).
3. The Sample case: every document of a type with a tab has its columns; each column worked out again unchanged gives back
   exactly what the reader gave (so every value the summary uses is in the tab); a correction reaches the income summary.
"""
from __future__ import annotations

import pytest

import harness as h
from test_copies import _copy, _pdf
from core import formview as fv
from core import parsers as P

SAME = ("status", "amounts", "parts", "fit", "notes", "checks", "inv_note")


def _doc(fam, parsed, did="d1"):
    return dict(family=fam, did=did, route="program", file=f"{did}.pdf", path=f"/x/{did}.pdf", parsed=parsed)


def _corrected(fam, parsed, edits: dict) -> dict:
    """The document's result after the form-tab corrections edits = {column index: {row key: value}}."""
    d = _doc(fam, parsed)
    r = dict(inv=dict(docs=[d]), formview={fam: {f"d1#{i}": e for i, e in edits.items()}})
    return fv.effective_docs(r)[0]["parsed"]


def _same(a: dict, b: dict):
    for k in SAME:
        assert a.get(k) == b.get(k), (k, a.get(k), b.get(k))


# ---------------------------------------------------------------- 1. corrected = read
def test_misc_correction_equals_reader(tmp_path):
    form = lambda amt: [_copy(60, [("1 Rents", ""), ("3 Other income", amt), ("4 Federal income tax withheld", "100.00")])]
    a = P.parse_1099_form(_pdf(tmp_path / "a.pdf", form("1,000.00")), "misc")
    b = P.parse_1099_form(_pdf(tmp_path / "b.pdf", form("1,250.00")), "misc")
    assert fv.doc_columns(_doc("1099misc", a))[0]["misc_3"] == 1000.0
    _same(_corrected("1099misc", a, {0: {"misc_3": 1250.0}}), b)


def test_nec_correction_equals_reader(tmp_path):
    form = lambda amt: [_copy(60, [("1 Nonemployee compensation", amt), ("4 Federal income tax withheld", "")])]
    a = P.parse_1099_form(_pdf(tmp_path / "a.pdf", form("5,000.00")), "nec")
    b = P.parse_1099_form(_pdf(tmp_path / "b.pdf", form("4,000.00")), "nec")
    _same(_corrected("1099nec", a, {0: {"nec_1": 4000.0}}), b)


def _r(gross, taxable, code):
    from test_copies import _r as r_copy
    return [r_copy(60, gross, taxable, "100.00", "", code)]


def test_1099r_two_forms_two_columns_and_correction(tmp_path):
    """Two different 1099-Rs in one file = two columns (not added together on the tab); correcting form 2's taxable amount
    and code = the reader reading the corrected form."""
    a = P.parse_1099r(_pdf(tmp_path / "a.pdf", [_r("1,000.00", "1,000.00", "7")[0], _r("2,000.00", "500.00", "7")[0]]))
    b = P.parse_1099r(_pdf(tmp_path / "b.pdf", [_r("1,000.00", "1,000.00", "7")[0], _r("2,000.00", "800.00", "7")[0]]))
    cols = fv.doc_columns(_doc("1099r", a))
    assert [c["b2a"] for c in cols] == [1000.0, 500.0] and [c["code"] for c in cols] == ["7", "7"]
    _same(_corrected("1099r", a, {1: {"b2a": 800.0}}), b)


def test_int_rows_correction_equals_reader(tmp_path):
    from test_copies import _int_page
    a = P.parse_1099int_rows(_pdf(tmp_path / "a.pdf", [_int_page([("1 Interest income", "300.00"), ("6 Foreign tax paid", "5.00")])]))
    b = P.parse_1099int_rows(_pdf(tmp_path / "b.pdf", [_int_page([("1 Interest income", "350.00"), ("6 Foreign tax paid", "5.00")])]))
    _same(_corrected("1099int", a, {0: {"int_1": 350.0}}), b)


def test_1098e_correction_equals_reader(tmp_path):
    form = lambda amt: [_copy(60, [("1 Student loan interest received by lender", amt)])]
    a = P.parse_1098e(_pdf(tmp_path / "a.pdf", form("600.00")))
    b = P.parse_1098e(_pdf(tmp_path / "b.pdf", form("900.00")))
    assert a["amounts"] == {"student_loan": 600.0}
    _same(_corrected("1098e", a, {0: {"b1": 900.0}}), b)


def _ssa_page(net):
    return [(60, 100, "FORM SSA-1099 - SOCIAL SECURITY BENEFIT STATEMENT"), (60, 140, "Box 5. Net Benefits for 2025"), (300, 140, net)]


def test_ssa_correction_equals_reader_and_more_than_one(tmp_path):
    a = P.parse_ssa(_pdf(tmp_path / "a.pdf", [_ssa_page("20,000.00")]))
    b = P.parse_ssa(_pdf(tmp_path / "b.pdf", [_ssa_page("21,000.00")]))
    assert a["amounts"] == {"ss": 20000.0} and not any("more than one" in n for n in a["notes"])
    _same(_corrected("ssa", a, {0: {"b5": 21000.0}}), b)
    two = P.parse_ssa(_pdf(tmp_path / "two.pdf", [_ssa_page("20,000.00"), _ssa_page("9,000.00")]))
    assert two["amounts"] == {"ss": 20000.0}                     # still the first form, as before
    assert "This file seems to hold more than one SSA-1099 — check" in two["notes"]
    same_twice = P.parse_ssa(_pdf(tmp_path / "copy.pdf", [_ssa_page("20,000.00"), _ssa_page("20,000.00")]))
    assert not any("more than one" in n for n in same_twice["notes"])


def _t_page(b1, b5):
    return [_copy(60, [("1 Payments received for qualified tuition", b1), ("5 Scholarships or grants", b5)])]


def test_1098t_correction_equals_reader_and_more_than_one(tmp_path):
    a = P.parse_1098t(_pdf(tmp_path / "a.pdf", _t_page("10,000.00", "2,000.00")))
    b = P.parse_1098t(_pdf(tmp_path / "b.pdf", _t_page("10,000.00", "3,000.00")))
    assert "box 5 2,000.00" in a["inv_note"]
    _same(_corrected("1098t", a, {0: {"b5": 3000.0}}), b)
    two = P.parse_1098t(_pdf(tmp_path / "two.pdf", _t_page("10,000.00", "2,000.00") + _t_page("4,000.00", "0.00")))
    assert two["inv_note"].endswith("This file seems to hold more than one 1098-T — check")


def _box_rows_pdf(path, div_1a):
    return _pdf(path, [[(60, 100, "1099-DIV Dividends and Distributions"), (60, 130, "BOX 1A: Total ordinary dividends"),
                        (400, 130, div_1a), (60, 160, "BOX 2A: Total capital gain distributions"), (400, 160, "50.00"),
                        (60, 190, "BOX 4: Federal income tax withheld"), (400, 190, "10.00")]])


def test_statement_correction_equals_reader(tmp_path):
    a = P.parse_box_rows(_box_rows_pdf(tmp_path / "a.pdf", "100.00"))
    b = P.parse_box_rows(_box_rows_pdf(tmp_path / "b.pdf", "175.00"))
    col = fv.doc_columns(_doc("1099div", a))[0]
    assert col["div_1a"] == 100.0 and col["div_2a"] == 50.0 and col["fit"] == 10.0
    _same(_corrected("1099div", a, {0: {"div_1a": 175.0}}), b)


# ---------------------------------------------------------------- 2. made-up parsed results
def test_composite_8949_box_rows_add_up():
    """A composite with Form 8949 box rows: correcting box A changes the ST row (A) and the ST total = the box rows; DIV 2a
    still goes to LT; §1256 still splits 60 / 40."""
    f = dict(div_1a=500.0, div_2a=40.0, s1256_11=100.0)
    b = dict(st=dict(proceeds=1000.0, cost=800.0, md=0, wash=0, gain=200.0), lt=dict(proceeds=0, cost=0, md=0, wash=0, gain=0.0))
    boxes = {"st": [("A", 150.0, 600.0), ("B", 50.0, 400.0)]}
    p = P._amounts_1099(f, b, "", {}, boxes)
    p.update(fit=0.0, reader="1099_statement", redo_inputs=dict(missing={}, boxes=boxes))
    col = fv.doc_columns(_doc("composite", p))[0]
    assert col["b8949:st:A"] == 150.0 and col["b:st:gain"] == 200.0
    q = _corrected("composite", p, {0: dict(col, **{"b8949:st:A": 175.0})})
    assert dict(q["parts"]["st"])["(A)"] == 175.0
    assert q["amounts"]["st"] == pytest.approx(225.0 + 40.0)          # 175 + 50 + 40% of 100
    assert q["amounts"]["lt"] == pytest.approx(40.0 + 60.0)           # DIV 2a + 60% of 100
    assert q["detail"]["b_st"]["gain"] == 225.0
    _same(_corrected("composite", p, {0: col}), p)                     # unchanged column = the first read


def test_1095a_and_1099sa_made_up():
    a = P.a1095_result(1200.0)
    q = _corrected("1095a", a, {0: {"aptc": 1500.0}})
    assert q["inv_note"] == "1095-A: advance PTC 1,500.00 (line 33C)" and q["detail"]["aptc"] == 1500.0
    sa = P.sa_result([{"1": "450.49", "3": "1", "5": "HSA"}])
    col = fv.doc_columns(_doc("1099sa", sa))[0]
    assert col == {"b1": 450.49, "b3": "1", "b5": "HSA"}
    q = _corrected("1099sa", sa, {0: {"b1": 500.0}})
    assert q["detail"]["gross"] == 500.0 and "gross distribution 500.00" in q["inv_note"]


def test_list_tabs_and_others():
    """1099-G (no reader): its tab lists the document; a not-read 1099-R is listed under the 1099-R table."""
    g = dict(family="1099g", did="g", route="program", file="g.pdf", path="/x/g.pdf", parsed=None)
    r_none = dict(family="1099r", did="r", route="ai", file="r.pdf", path="/x/r.pdf",
                  parsed=dict(status="none", amounts={}, checks=["1099-R amounts not found"]))
    r = dict(inv=dict(docs=[g, r_none]))
    tabs = {t["key"]: t for t in fv.tabs(r, [])}
    assert tabs["1099g"]["defn"] is None and tabs["1099g"]["n"] == 1 and "no reader" in tabs["1099g"]["others"][0]["why"]
    assert tabs["1099r"]["cols"] == [] and tabs["1099r"]["others"][0]["why"].startswith("Not read by the program")


# ---------------------------------------------------------------- 3. the Sample case
CASE = h.SAMPLES / "Sample"


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if not (CASE / h.KEY_NAME).exists():
        pytest.skip("the Sample case isn't on this computer")
    from core import runcheck
    roles = h.load_key(CASE / h.KEY_NAME)["roles"]
    docs = [str(CASE / n) for n, x in roles.items() if x == "Document" and (CASE / n).is_file()]
    form = dict(pyret="", karbon="", clientsum="", utscreens="", wip="")
    return h.open_run(runcheck.run(form, docs, work_dir=tmp_path_factory.mktemp("work")))


def test_sample_every_form_has_its_columns(run):
    """Each read document of a type with a tab has columns, and its columns worked out again unchanged give back exactly what
    the reader gave - so every value the summary uses is on the tab. Sample: 1099-R, 1099-SA, 5 composites, W-2s, 1098."""
    seen = set()
    for d in run["inv"]["docs"]:
        if d.get("family") not in fv.FAMILIES or not fv._usable(d):
            continue
        cols = fv.doc_columns(d)
        assert cols, d["file"]
        seen.add(d["family"])
        again = fv.FAMILIES[d["family"]]["redo"](d, cols)
        for k in ("amounts", "parts", "fit", "notes", "checks", "inv_note"):
            assert again.get(k) == d["parsed"].get(k), (d["file"], k)
    assert {"1099r", "1099sa", "composite", "w2", "1098"} <= seen


def test_sample_tabs(run):
    from core import runcheck
    inc, ded = runcheck.summaries(run)
    fvd = runcheck.form_view_data(run, inc, runcheck.inventory_rows(run), ded)
    tabs = {t["key"]: t for t in fvd["tabs"]}
    assert tabs["composite"]["n"] == 5 and tabs["composite"]["defn"] == "1099"
    assert tabs["1099r"]["n"] == 1 and tabs["1099sa"]["n"] == 1
    assert not any(t.get("soon") for t in fvd["tabs"])


def test_sample_correction_reaches_the_summary(run):
    """A dividend corrected on a composite's column: the income summary's dividend line for that document follows."""
    from core import runcheck
    d = next(d for d in run["inv"]["docs"] if d.get("family") == "composite" and (d["parsed"].get("detail") or {}).get("div_1a"))
    old = d["parsed"]["detail"]["div_1a"]
    h.page("POST", f"/formview/{run['token']}/composite", {f'{d["did"]}#0': {"div_1a": round(old + 1000, 2)}})
    try:
        inc, _ = runcheck.summaries(run)
        row = next(x for s in inc["sections"] if s["key"] == "dividends" for x in s["rows"] if x.get("file") == d["file"])
        assert row["doc_cy"] == pytest.approx(old + 1000)
    finally:
        h.page("POST", f"/formview/{run['token']}/composite", {})
    inc, _ = runcheck.summaries(run)
    row = next(x for s in inc["sections"] if s["key"] == "dividends" for x in s["rows"] if x.get("file") == d["file"])
    assert row["doc_cy"] == pytest.approx(old)

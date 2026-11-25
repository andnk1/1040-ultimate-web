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
def _five(proceeds, cost, gain, md=0.0, wash=0.0):
    return dict(proceeds=proceeds, cost=cost, md=md, wash=wash, gain=gain)


def _composite(b, boxes):
    f = dict(div_1a=500.0, div_2a=40.0, s1256_11=100.0)
    p = P._amounts_1099(f, b, "", {}, boxes)
    p.update(fit=0.0, reader="1099_statement", redo_inputs=dict(missing={}, boxes=boxes))
    return p


def test_composite_8949_box_groups():
    """A composite with Form 8949 boxes A and B: each box keeps its five numbers on the tab. Correcting box A: the ST row (A)
    follows, the ST totals become the boxes' sums (all five), DIV 2a still goes to LT, §1256 still splits 60 / 40."""
    b = dict(st=_five(1000.0, 800.0, 200.0), lt=_five(0, 0, 0.0))
    boxes = {"st": [("A", 150.0, 600.0, _five(600.0, 450.0, 150.0)), ("B", 50.0, 400.0, _five(400.0, 350.0, 50.0))]}
    p = _composite(b, boxes)
    assert not any("don't add up" in n for n in p["notes"])
    col = fv.doc_columns(_doc("composite", p))[0]
    assert col["b8949:st:A:gain"] == 150.0 and col["b8949:st:A:cost"] == 450.0 and col["b:st:gain"] == 200.0
    q = _corrected("composite", p, {0: dict(col, **{"b8949:st:A:proceeds": 625.0, "b8949:st:A:gain": 175.0})})
    assert dict(q["parts"]["st"])["(A)"] == 175.0
    assert q["amounts"]["st"] == pytest.approx(225.0 + 40.0)          # 175 + 50 + 40% of 100
    assert q["amounts"]["lt"] == pytest.approx(40.0 + 60.0)           # DIV 2a + 60% of 100
    assert q["detail"]["b_st"] == _five(1025.0, 800.0, 225.0)          # the term's five totals = the boxes' sums
    _same(_corrected("composite", p, {0: col}), p)                     # unchanged column = the first read
    # a correction elsewhere (DIV 1a) leaves the printed term totals alone
    assert _corrected("composite", p, {0: dict(col, div_1a=600.0)})["detail"]["b_st"] == b["st"]


def test_box_groups_not_adding_up_get_a_note():
    """Boxes whose numbers don't add up to the term totals (here the cost): a note in the document's comment."""
    b = dict(st=_five(1000.0, 800.0, 200.0))
    boxes = {"st": [("A", 150.0, 600.0, _five(600.0, 400.0, 150.0)), ("B", 50.0, 400.0, _five(400.0, 350.0, 50.0))]}
    p = _composite(b, boxes)
    note = next(n for n in p["notes"] if "don't add up" in n)
    assert note == "1099-B Short-term: the Form 8949 box lines don't add up to the term totals (cost 750.00 vs 800.00) — check"
    assert "wash sale" not in note                                    # (the summary leaves notes naming a wash sale out)


def test_box_rows_keep_five_numbers(tmp_path):
    """_box_rows keeps all five numbers of each Form 8949 summary row (National / Fidelity layout)."""
    page = [(60, 100, "Short-term transactions for which basis is reported to the IRS"), (60, 112, "1,000.00 800.00 0.00 5.00 205.00")]
    rows = P._box_rows(P._texts(_pdf(tmp_path / "b.pdf", [page]), None, None)[0])
    assert rows == [("A", 1000.0, 205.0, _five(1000.0, 800.0, 205.0, wash=5.0))]


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
    assert list(tabs) == ["1099g", "1099r"]      # only the client's types - no empty W2 / 1099-B ... tabs (Lady, 2026-11-24)
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
    # a tab only for a type the client has a document of; W2 first, then alphabetical
    have = {d.get("family") for d in run["inv"]["docs"] if d.get("route") != "skipped"}
    assert {t["form"] for t in fvd["tabs"]} == have & {f for f, _ in fv.TABS}
    assert fvd["tabs"][0]["form"] == "w2"
    labels = [t["label"] for t in fvd["tabs"][1:] if "_" not in t["label"]]
    assert labels == sorted(labels, key=str.lower)


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


# ---------------------------------------------------------------- the recipient's SSN (core/ssn.py)
def test_ssn_search():
    from core import ssn
    text = ("Recipient TIN XXX-XX-1234  Payer EIN 12-3456789  spouse ***-**-5678  again 123 - 45 - 1234  "
            "full 987-65-4321  account 1123-45-6789-01  phone 555-123-4567")
    assert ssn.last4s([text]) == ["1234", "5678", "4321"]             # in the order found, each once; no EIN / phone
    assert ssn.shown("1234") == "***-**-1234"
    names = ssn.names_from_return([dict(role="Taxpayer", ssn="111-22-1234", first="JANE", last="DOE"),
                                   dict(role="Spouse", ssn="111-22-5678", first="John", last="Doe"),
                                   dict(role="Dependent 1", ssn="111-22-9999", first="Kid", last="Doe")])
    assert names == {"1234": "Jane Doe", "5678": "John Doe"}           # taxpayer / spouse only
    assert ssn.shown("5678", names) == "***-**-5678 · John Doe"


def test_ssn_on_documents_and_columns(tmp_path):
    """Run check's shared search: each document's SSNs; a W-2 with none printed in the text keeps its box a last 4; the form
    tab columns carry the SSN line and the page."""
    from core import runcheck
    pdf = _pdf(tmp_path / "r.pdf", [_r("1,000.00", "1,000.00", "7")[0] + [(300, 40, "RECIPIENT'S TIN ***-**-4321")]])
    d = _doc("1099r", P.parse_1099r(pdf))
    d["path"] = str(pdf)
    w2 = dict(family="w2", did="w", route="program", file="w.pdf", path=str(tmp_path / "w.txt"),
              parsed=dict(status="read", detail=dict(boxes=[{"1": 10.0, "ssn": "XXX-XX-2222"}])))
    inv = dict(docs=[d, w2])
    runcheck.read_ssns(inv)
    assert d["ssn4"] == ["4321"] and w2["ssn4"] == ["2222"]
    r = dict(inv=inv, ssn_names={"4321": "Jane Doe"})
    col = fv.columns(r, ["d1"], "1099r")[0]
    assert col["ssn"] == ["***-**-4321 · Jane Doe"] and col["page"] == 1
    assert fv.PER_TAB == 8


def test_ssn_only_on_form_pages(tmp_path):
    """The SSN is looked for only on the pages the reader took its amounts from: an SSN on another page (here page 2, no
    1099-R on it) is left out. A document with no reader: the first 3 pages the document scan read (ssn4_first)."""
    from core import runcheck
    pages = [_r("1,000.00", "1,000.00", "7")[0] + [(300, 40, "RECIPIENT'S TIN XXX-XX-4321")],
             [(60, 100, "Instructions for Recipient   example 123-45-9999")]]
    p = P.parse_1099r(_pdf(tmp_path / "r.pdf", pages))
    assert p["ssn4"] == ["4321"]
    other = dict(family="other", did="o", route="context", file="o.pdf", path="/x/o.pdf", parsed=None, ssn4_first=["7777"])
    k1 = dict(family="k1p", did="k", route="k1v", file="k.pdf", path="/x/k.pdf", ssn4_first=[])
    inv = dict(docs=[_doc("1099r", p), other, k1])
    runcheck.read_ssns(inv)
    assert [d["ssn4"] for d in inv["docs"]] == [["4321"], ["7777"], []]

"""test_ut_entry.py - UltraTax entry rules (core/k1v/ut_entry.py, 2026-11-11): Bot / By hand on the K-1 UT page, the row
limits per code box, the setting that turns it off, the by-hand list as Excel and PDF."""
from __future__ import annotations

import io

import pytest

import harness as h  # noqa: F401  (puts the app folder on the path)
from core.inventory import natural_key
from core.k1v import ut_entry as ue


def _r(box, code="", kind="line", block=False, valid=""):
    return dict(id=f"1|{box}{code}", kind=kind, box=box, code=code, block=block, valid=valid, problem="", desc="", eff=10.0)


def _decide(*rows):
    return [(r["entry"], r["why"]) for r in ue.decide(list(rows))]


@pytest.fixture(autouse=True)
def _on(monkeypatch):
    monkeypatch.setattr(ue, "ENABLED", True)


def test_fixed_rules():
    got = _decide(_r("G", kind="info"), _r("H1", kind="info"), _r("J", kind="info"), _r("K1", kind="info"), _r("L", kind="info"),
                  _r("M", kind="info"), _r("N", kind="info"), _r("9c"), _r("12"), _r("16", kind="check"), _r("22", kind="check"),
                  _r("23", kind="check"), _r("13", "AE"), _r("1"), _r("13", "A"))
    nsde, grey, chk = "Not in Source Data Entry", "Grey in Source Data Entry", "Checkbox – Tab can't reach it"
    assert got == [("hand", nsde)] * 3 + [("bot", "")] + [("hand", nsde)] * 3 + [("hand", grey)] * 2 + [("hand", chk)] * 3 \
        + [("hand", "By hand"), ("bot", ""), ("bot", "")]


def test_row_limits_in_k1_order():
    # box 13 has 3 rows: the 4th and 5th bot lines are by hand; 13 AE (by hand anyway) uses no row
    got = _decide(_r("13", "A"), _r("13", "AE"), _r("13", "B"), _r("13", "C"), _r("13", "D"), _r("13", "E"))
    assert got == [("bot", ""), ("hand", "By hand"), ("bot", ""), ("bot", ""),
                   ("hand", "Only 3 rows in Source Data Entry"), ("hand", "Only 3 rows in Source Data Entry")]
    assert ue.RULES["1065"]["ROWS"] == {"11": 3, "13": 3, "14": 2, "15": 2, "17": 3, "18": 3, "19": 2, "20": 8}
    rows = [_r("20", c) for c in "ABCDEFGHIJ"]
    assert [e for e, _ in _decide(*rows)] == ["bot"] * 8 + ["hand"] * 2
    assert _decide(_r("14", "A"), _r("14", "B"), _r("14", "C"))[2] == ("hand", "Only 2 rows in Source Data Entry")
    assert _decide(_r("5"), _r("5"), _r("5"), _r("5")) == [("bot", "")] * 4                  # no limit on a box without codes


def test_code_not_in_ut_problem_lines_and_statement_rows():
    assert _decide(_r("13", "U", valid="N")) == [("hand", "Code not in UltraTax")]          # the bot can't pick it
    assert _decide(_r("13", "QQ", block=True), _r("20", kind="stmt")) == [("", ""), ("", "")]  # fixed first / its lines below
    # a line with a red problem uses no row
    assert _decide(_r("19", "A", block=True), _r("19", "A"), _r("19", "B"))[1:] == [("bot", ""), ("bot", "")]


def test_setting_off(monkeypatch):
    monkeypatch.setattr(ue, "ENABLED", False)
    assert _decide(_r("G", kind="info"), _r("13", "AE"), _r("1")) == [("", "")] * 3
    assert ue.hand_items(dict(k1s=[dict(ready=True, rows=[dict(_r("12"), entry="hand", why="x")])])) == []


def test_number_order():
    names = ["b.pdf", "10 K-1.pdf", "A K-1.pdf", "2 K-1.pdf", "1.pdf"]
    assert sorted(names, key=natural_key) == ["1.pdf", "2 K-1.pdf", "10 K-1.pdf", "A K-1.pdf", "b.pdf"]


ITEMS = [dict(id="h|1|II|G", n=1, file="2 K-1.pdf", name="DEMO LP", ein="12-3456789", box="G", code="", desc="Partner type",
              amt="Limited", why="Not in Source Data Entry"),
         dict(id="h|1|12|0", n=1, file="2 K-1.pdf", name="DEMO LP", ein="12-3456789", box="12", code="", desc="Section 179",
              amt=-1234.56, why="Grey in Source Data Entry")]


def test_xlsx():
    from openpyxl import load_workbook
    ws = load_workbook(io.BytesIO(ue.hand_xlsx(ITEMS, ue.head("Test 1234", "2025", ITEMS)))).active
    assert ws.freeze_panes == "A5"
    assert [c.value for c in ws[4]] == ["Document", "Partnership", "EIN", "Box", "Code", "Description", "Amount", "Why", "Done"]
    assert "Test 1234" in ws["A2"].value and "Tax year 2025" in ws["A2"].value and "2 items" in ws["A2"].value
    assert ws["G5"].value == "Limited" and ws["G6"].value == -1235 and ws["G6"].number_format == "#,##0;-#,##0"
    assert ws["I5"].value in (None, "")


def test_print_page():
    """The by-hand list as a page to print (the desktop's PDF; Chrome prints it - conversion plan, question 5)."""
    t = ue.hand_html(ITEMS * 40, ue.head("Test 1234", "2025", ITEMS * 40))
    assert "size: letter landscape" in t and 'counter(page) " of " counter(pages)' in t        # landscape, page n of N
    assert "Not in Source Data Entry" in t and "-1,235" in t and "Tax year 2025" in t and "Test 1234" in t
    assert t.count("<tr>") == 1 + 2 * 40                                                       # the header + every item

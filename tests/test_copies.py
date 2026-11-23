"""Copies vs different forms (Lady, 2026-11-23): two forms in one file are the same form when their federal key boxes match
(core/parsers.py KEY_BOXES); state / local boxes never count. A copy fills in the boxes the first copy missed.
Made-up forms only (drawn here with PyMuPDF), no client file."""
from __future__ import annotations

import pymupdf

from core import parsers as P


def _pdf(path, pages):
    """pages = [[(x, y, text), ...], ...] -> a PDF with that text at those spots (y = baseline)."""
    doc = pymupdf.open()
    for items in pages:
        pg = doc.new_page(width=612, height=792)
        for x, y, t in items:
            pg.insert_text((x, y), t, fontsize=9)
    doc.save(str(path))
    doc.close()
    return path


def _copy(y0, boxes, x=60):
    """One IRS-layout copy: each box label on its own row, its amount under it. boxes = [(label, amount text)]. The first box's
    label is always printed (as on the real forms): the reader finds where each copy starts by it."""
    out = []
    for i, (lab, amt) in enumerate(boxes):
        y = y0 + i * 40
        out.append((x, y, lab))
        if amt:
            out.append((x + 4, y + 14, amt))
    return out


# ---------------------------------------------------------------- 1099-MISC
def test_misc_state_copy_counts_once(tmp_path):
    """Copy B and Copy 2 with the same boxes 1-4 but another state tax: one form (before: two, other income doubled).
    Box 18 only on Copy 2: filled in; box 16 differs: the first copy's amount stays."""
    b = [("1 Rents", ""), ("3 Other income", "1,000.00"), ("4 Federal income tax withheld", "100.00"), ("16 State tax withheld", "50.00")]
    c2 = [("1 Rents", ""), ("3 Other income", "1,000.00"), ("4 Federal income tax withheld", "100.00"), ("16 State tax withheld", "20.00"),
          ("18 State income", "1,000.00")]
    p = _pdf(tmp_path / "misc.pdf", [_copy(60, b) + _copy(420, c2)])
    r = P.parse_1099_form(p, "misc")
    assert r["status"] == "read"
    assert r["detail"]["forms"] == 1
    assert r["amounts"] == {"other": 1000.0}
    assert r["detail"]["boxes"]["16"] == 50.0 and r["detail"]["boxes"]["18"] == 1000.0
    assert r["fit"] == 100.0
    assert not any("different forms" in n for n in r["notes"])


def test_misc_different_forms_add_up(tmp_path):
    a = [("1 Rents", ""), ("3 Other income", "1,000.00"), ("4 Federal income tax withheld", "100.00")]
    b = [("1 Rents", ""), ("3 Other income", "500.00"), ("4 Federal income tax withheld", "100.00")]
    p = _pdf(tmp_path / "misc2.pdf", [_copy(60, a), _copy(60, b)])
    r = P.parse_1099_form(p, "misc")
    assert r["detail"]["forms"] == 2
    assert r["amounts"] == {"other": 1500.0}
    assert r["fit"] == 200.0
    assert any("2 different forms" in n for n in r["notes"])


# ---------------------------------------------------------------- 1099-NEC
def test_nec_state_copy_counts_once(tmp_path):
    b = [("1 Nonemployee compensation", "5,000.00"), ("4 Federal income tax withheld", "0.00"), ("5 State tax withheld", "200.00")]
    c2 = [("1 Nonemployee compensation", "5,000.00"), ("4 Federal income tax withheld", "0.00"), ("5 State tax withheld", "75.00")]
    p = _pdf(tmp_path / "nec.pdf", [_copy(60, b), _copy(60, c2)])
    r = P.parse_1099_form(p, "nec")
    assert r["detail"]["forms"] == 1
    assert r["amounts"] == {"schc": 5000.0}


# ---------------------------------------------------------------- 1099-R
def _r(y0, gross, taxable, fit, state, code):
    return _copy(y0, [("1 Gross distribution", gross), ("2a Taxable amount", taxable),
                      ("4 Federal income tax withheld", fit), ("14 State tax withheld", state),
                      ("7 Distribution code(s)", "")]) + [(64, y0 + 4 * 40 + 20, code)]


def test_1099r_state_copy_counts_once(tmp_path):
    p = _pdf(tmp_path / "r.pdf", [_r(60, "10,000.00", "10,000.00", "1,000.00", "300.00", "7"),
                                 _r(60, "10,000.00", "10,000.00", "1,000.00", "120.00", "7")])
    r = P.parse_1099r(p)
    assert r["amounts"] == {"pension": 10000.0}
    assert r["fit"] == 1000.0
    assert r["detail"]["boxes"]["14"] == 300.0
    assert r["detail"]["code"] == "7"
    assert not any("different 1099-Rs" in n for n in r["notes"])


def test_1099r_another_code_is_another_form(tmp_path):
    """Same amounts, another box 7 code: a different 1099-R (the code is a key box)."""
    p = _pdf(tmp_path / "r2.pdf", [_r(60, "10,000.00", "10,000.00", "1,000.00", "", "7"),
                                  _r(60, "10,000.00", "10,000.00", "1,000.00", "", "G")])
    r = P.parse_1099r(p)
    assert r["amounts"] == {"pension": 20000.0}
    assert any("2 different 1099-Rs" in n for n in r["notes"])


# ---------------------------------------------------------------- 1099-INT (bank layout: label and amount on one row)
def _int_page(rows):
    return [(60, 100 + i * 30, lab) for i, (lab, _) in enumerate(rows)] + \
           [(450, 100 + i * 30, amt) for i, (_, amt) in enumerate(rows)]


def test_int_copy_fills_missing_box(tmp_path):
    """Two pages with the same boxes 1, 3, 4; box 6 only on the first: one form, box 6 kept (before: interest doubled)."""
    p = _pdf(tmp_path / "int.pdf", [_int_page([("1 Interest income", "300.00"), ("6 Foreign tax paid", "5.00")]),
                                    _int_page([("1 Interest income", "300.00")])])
    r = P.parse_1099int_rows(p)
    assert r["amounts"] == {"interest": 300.0}
    assert not any("different 1099-INTs" in n for n in r["notes"])
    assert any("Foreign tax paid 5.00" in n for n in r["notes"])


# ---------------------------------------------------------------- 1099-SA (list layout)
def test_sa_copy_fills_missing_box(tmp_path):
    """Same box 1 and 2 on two pages, the code and account type only on the second: one form, code filled in."""
    p = _pdf(tmp_path / "sa.pdf", [[(60, 100, "1 Gross distribution ........ 450.49")],
                                   [(60, 100, "1 Gross distribution ........ 450.49"), (60, 130, "3 Distribution code ...... 1"),
                                    (60, 160, "5 HSA ...... HSA")]])
    r = P.parse_1099sa(p)
    assert r["detail"]["gross"] == 450.49
    assert len(r["detail"]["forms"]) == 1
    assert r["detail"]["forms"][0].get("3") == "1"

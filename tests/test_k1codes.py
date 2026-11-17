"""test_k1codes.py - the one K-1 (1065) code list (list of 2026-11-05, item 3): core/k1v/k1_codes.py is the source; the copy
reference\\K-1 1065 statement codes.csv must be the same (refresh it with:  python -m core.k1v.k1_codes)."""
from __future__ import annotations

import csv

from core.k1v import k1_codes as kc


def test_reference_csv_is_the_same_as_the_list():
    assert kc.REFERENCE_CSV.is_file(), "reference CSV missing - run: python -m core.k1v.k1_codes"
    with kc.REFERENCE_CSV.open(encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.reader(fh)]
    assert rows == kc.csv_rows(), "the code list changed - refresh the CSV: python -m core.k1v.k1_codes"


def test_list_is_consistent():
    keys = [(b, c) for b, c, *_ in kc.CODES]
    assert len(keys) == len(set(keys))                                   # no box / code twice
    assert all(r[4] in ("Active", "Reserved") and r[5] in ("Y", "?", "N", "") for r in kc.CODES)
    assert all((r[5] == "") == (r[1] == "") for r in kc.CODES)             # "in UT" only on codes
    assert kc.CODE_BOXES == ["11", "13", "14", "15", "17", "18", "19", "20"]
    assert all(kc.known(b) for b in kc.CODE_BOXES)                         # every code box has its heading row


def test_ut_wins():
    assert kc.valid_in_ut("13", "AE") == "Y" and kc.valid_in_ut("20", "A") == "Y"      # "?" (not checked yet) counts as valid
    assert kc.valid_in_ut("13", "Q") == "Y"                                # reserved by the IRS, listed in UT
    assert kc.valid_in_ut("13", "U") == "N" and kc.valid_in_ut("19", "E") == "N"       # reserved in UT
    assert kc.valid_in_ut("20", "QQ") == "N"                               # not on the list at all
    assert kc.valid_in_ut("5") == "" and kc.valid_in_ut("16") == ""        # boxes without codes
    assert kc.desc("19", "D").startswith("Deemed dist of money")           # UT wording where it is known
    assert kc.desc("11", "A") == "Other portfolio income (loss)"           # else the IRS wording
    dd = {(b, c) for b, c, _ in kc.dropdown()}
    assert ("17", "A") in dd and ("13", "U") not in dd and all(c for _, c in dd)

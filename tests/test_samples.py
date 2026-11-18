r"""test_samples.py - every test case in tests\samples against its answer key (run_tests.bat).

One test per case and sheet (Documents, Summary, UT check). A failure lists every row that differs: a fix (update the key)
or a breakage (fix the code)."""
from __future__ import annotations

import functools

import pytest

import harness as h

CASES = [c for c in h.case_dirs() if (c / h.KEY_NAME).exists()]


@functools.lru_cache(maxsize=None)
def _case(name: str):
    case = h.SAMPLES / name
    key = h.load_key(case / h.KEY_NAME)
    return key, h.read_all(case, key["roles"])


@pytest.mark.parametrize("sheet", [s for s, _ in h.SHEETS])
@pytest.mark.parametrize("case", [c.name for c in CASES])
def test_case(case, sheet):
    key, now = _case(case)
    new_files = [p.name for p in h.case_files(h.SAMPLES / case) if p.name not in key["roles"]]
    diffs = h.compare(key[sheet], now[sheet], now.get("labels"))     # (labels: the intended differences, harness.py)
    msg = h.report(diffs) if diffs else ""
    if new_files:
        msg += ("\n" if msg else "") + "Files not in the key yet (run make_key): " + "; ".join(new_files)
    assert not diffs and not new_files, msg


def test_cases_found():
    folders = h.case_dirs()
    assert folders, f"no test cases in {h.SAMPLES}"
    missing = [c.name for c in folders if not (c / h.KEY_NAME).exists()]
    assert not missing, "cases with no answer key yet (run make_key): " + ", ".join(missing)

"""test_archive.py - every sample client gives the same results as the retired desktop app (python-final).

The reference is tests/samples/<case>/archive_reference.json, written by tools/parity/make_reference.py from the archive's own
code. Here the case runs through this app's engine on this computer's Python; the page's "Check against the archive" button
runs the same check inside the browser (MuPDF.js). A case without a reference is skipped (run make_reference.py).
"""
from __future__ import annotations

import pytest

import harness as h

CASES = [c for c in h.case_dirs() if (c / h.REF_NAME).exists()]


@pytest.mark.parametrize("case", [c.name for c in CASES] or ["(no reference yet)"])
def test_same_as_the_archive(case):
    if not CASES:
        pytest.skip("no archive_reference.json yet - run python tools/parity/make_reference.py")
    res = h.check_reference(h.SAMPLES / case)
    lines = [f"{s['name']}: " + " | ".join(d) for s in res["sheets"] for d in s["differences"][:30]]
    assert res["ok"], f"{case} differs from {res['archive']}:\n" + "\n".join(lines)

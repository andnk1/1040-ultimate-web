"""keycheck.py - the test answer keys on the browser app's engine (design\\web_version.md, "Checks for every phase").

A test case = a folder of tests\\samples with its answer_key.xlsx. The case goes through the same Run check and the same rows
and compare as the tests on this computer (tests\\harness.py, one copy) - here with MuPDF.js as the PDF engine.
In the page: pick a folder that has an answer_key.xlsx -> the button "Check against the answer key"; a folder that has
an archive_reference.json -> "Check against the archive" (the retired desktop app's results, python-final).
(Not under Node: the cryptography library pdfplumber needs doesn't start there - the PDF door alone is compared under
Node, tools\\web_check\\compare_pdf.bat.)
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]


def _harness():
    if not (APP / "tests" / "harness.py").is_file():
        raise RuntimeError("tests\\harness.py isn't here - the answer keys can't be checked")
    if str(APP / "tests") not in sys.path:
        sys.path.insert(0, str(APP / "tests"))
    import harness
    return harness


def check(case_dir: str, step=None) -> dict:
    """{case, sheets: [{name, rows, checked, differences: [[kind, file, form, what, key, now]]}], ok}"""
    h = _harness()
    case = Path(case_dir)
    key = h.load_key(case / h.KEY_NAME)
    if step:
        step(f"Run check on {case.name}")
    r = h.run_case(case, key["roles"])
    out = dict(case=case.name, sheets=[], ok=True)
    with contextlib.redirect_stdout(io.StringIO()):
        for name, fn in h.SHEETS:
            now = fn(r)
            diffs = h.compare(key.get(name) or [], now)
            out["sheets"].append(dict(name=name, rows=len(now), checked=sum(1 for x in key.get(name) or [] if x["checked"]),
                                      differences=[[str(v) for v in d] for d in diffs]))
            out["ok"] = out["ok"] and not diffs
    return out


def check_archive(case_dir: str, step=None) -> dict:
    """The case compared with what the retired desktop app (python-final) read for it (archive_reference.json in the folder,
    written by tools/parity/make_reference.py) - the same check as tests/test_archive.py, here with MuPDF.js."""
    h = _harness()
    if step:
        step(f"Run check on {Path(case_dir).name}")
    return h.check_reference(Path(case_dir))

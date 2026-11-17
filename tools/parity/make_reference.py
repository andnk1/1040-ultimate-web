"""make_reference.py - what the retired desktop app (git tag python-final) reads for each sample client: the reference the
browser app is checked against ("same results as the archive" - design/conversion_plan.md).

    python tools/parity/make_reference.py                 every case folder in tests/samples
    python tools/parity/make_reference.py Sample K-1_Sample

How: a clean copy of python-final is taken from the old repository (`git archive`, into a temporary folder - the old
repository is not changed), the archive's own test harness runs each case through the archive's own code, and the rows it
reads (the three answer-key sheets: Documents, Summary, UT check) are written to tests/samples/<case>/archive_reference.json.
Per converted page more is kept ("pages"): the Summary's saves (tools/parity/scenario.py - the same edits in both apps), what
the archive keeps after them, and again after the saved work is opened.
That file holds client data: it stays in the case folder, which never goes to GitHub.

Needs the desktop app's libraries on this computer's Python (Flask, PyMuPDF, pdfplumber, openpyxl, python-docx).
The archive's test harness (tests/harness.py of the old folder) was never in git: it is taken from the old folder as it is.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import date
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
SAMPLES = APP / "tests" / "samples"
OLD = Path(r"C:\dev\1040_ultimate")                     # the old repository (the archive)
TAG = "python-final"

# runs inside the archive copy: the archive's harness reads the case with the archive's code
_RUN = r"""
import json, re, sys, tempfile
from pathlib import Path
sys.path[:0] = [sys.argv[1], str(Path(sys.argv[1]) / "tests"), sys.argv[4]]
import harness as h
import scenario                                        # tools/parity/scenario.py of the new app: the same edits
import core.wip as wip_mod
case = Path(sys.argv[2])
key = case / h.KEY_NAME
roles = h.load_key(key)["roles"] if key.exists() else h.guess_roles(case)
data = h.read_all(case, roles)
out = dict(roles=roles, sheets={name: [[f, n, w, h.norm(v)] for f, n, w, v in rows] for name, rows in data.items()}, pages={})

# the Summary's saves, through the desktop app's own addresses
app = h._app()
c = app.app.test_client()
r = h.run_case(case, roles)
inc, ded = app._summaries(r)
for url, body in scenario.edits(r, inc, ded):
    resp = c.post(url.format(token=r["token"]), json=body)
    assert resp.status_code == 200, (url, resp.status_code)
snap = wip_mod.snapshot(r)
inc, ded = app._summaries(r)
out["pages"]["summary_edits"] = scenario.normalize(dict(work=snap, income=inc, deductions=ded))

# the saved work opened again (Continue where you left off)
wp = Path(tempfile.mkdtemp()) / "1040 Ultimate WIP test.json"
wp.write_text(json.dumps(snap, default=str), encoding="utf-8")
pick = lambda role: next((str(case / n) for n, x in roles.items() if x == role and (case / n).is_file()), "")
docs = [dict(path=str(case / n), on=True) for n, x in roles.items() if x == "Document" and (case / n).is_file()]
resp = c.post("/run", data=dict(mode="summary", pyret=pick("Prior-year return"), utscreens=pick("UT input screens"),
                                karbon="", clientsum="", wip=str(wp), docs=json.dumps(docs)))
r2 = app.RUNS[re.search(r"/summary/([0-9a-f]+)", resp.headers["Location"]).group(1)]
inc2, ded2 = app._summaries(r2)
out["pages"]["summary_reopened"] = scenario.normalize(dict(work=wip_mod.snapshot(r2), income=inc2, deductions=ded2))
Path(sys.argv[3]).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
"""


def archive_copy(old: Path) -> tuple[Path, str]:
    """python-final, unpacked into a temporary folder, with the archive's test harness next to it -> (folder, commit)."""
    commit = subprocess.run(["git", "-C", str(old), "rev-parse", "--short", f"{TAG}^{{commit}}"], capture_output=True,
                            text=True, check=True).stdout.strip()
    tar = subprocess.run(["git", "-C", str(old), "archive", TAG], capture_output=True, check=True).stdout
    dst = Path(tempfile.mkdtemp(prefix="u1040_archive_"))
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        t.extractall(dst, filter="data")
    (dst / "tests").mkdir(exist_ok=True)
    shutil.copy2(old / "tests" / "harness.py", dst / "tests" / "harness.py")
    return dst, commit


def main() -> None:
    ap = argparse.ArgumentParser(description="The archive's results for each sample client (archive_reference.json).")
    ap.add_argument("cases", nargs="*", help="case folder names in tests/samples (default: all)")
    ap.add_argument("--old", default=str(OLD), help="the old repository (default: %(default)s)")
    a = ap.parse_args()
    cases = [SAMPLES / c for c in a.cases] or sorted(p for p in SAMPLES.iterdir() if p.is_dir())
    arch, commit = archive_copy(Path(a.old))
    harness_sha = hashlib.sha1((arch / "tests" / "harness.py").read_bytes()).hexdigest()[:12]
    try:
        for case in cases:
            print(f"{case.name}: reading with {TAG} ({commit}) ...", flush=True)
            tmp = arch / f"_{case.name}.json"
            subprocess.run([sys.executable, "-c", _RUN, str(arch), str(case), str(tmp), str(Path(__file__).parent)],
                           check=True, cwd=arch, stdout=subprocess.DEVNULL)
            ref = json.loads(tmp.read_text(encoding="utf-8"))
            ref = dict(archive=f"{TAG} {commit}", made=date.today().isoformat(), archive_harness=harness_sha, **ref)
            (case / "archive_reference.json").write_text(json.dumps(ref, ensure_ascii=False), encoding="utf-8")
            print(f"   -> {case.name}/archive_reference.json: "
                  + ", ".join(f"{k} {len(v)} rows" for k, v in ref["sheets"].items())
                  + "; pages: " + ", ".join(ref.get("pages") or {}), flush=True)
    finally:
        shutil.rmtree(arch, ignore_errors=True)


if __name__ == "__main__":
    main()

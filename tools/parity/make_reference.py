"""make_reference.py - what the retired desktop app (git tag python-final) reads for each sample client: the reference the
browser app is checked against ("same results as the archive" - design/conversion_plan.md).

    python tools/parity/make_reference.py                 every case folder in tests/samples
    python tools/parity/make_reference.py Sample K-1_Sample

How: a clean copy of python-final is taken from the old repository (`git archive`, into a temporary folder - the old
repository is not changed), the archive's own test harness runs each case through the archive's own code, and the rows it
reads (the three answer-key sheets: Documents, Summary, UT check) are written to tests/samples/<case>/archive_reference.json.
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
import json, sys
from pathlib import Path
sys.path[:0] = [sys.argv[1], str(Path(sys.argv[1]) / "tests")]
import harness as h
case = Path(sys.argv[2])
key = case / h.KEY_NAME
roles = h.load_key(key)["roles"] if key.exists() else h.guess_roles(case)
data = h.read_all(case, roles)
out = dict(roles=roles, sheets={name: [[f, n, w, h.norm(v)] for f, n, w, v in rows] for name, rows in data.items()})
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
            subprocess.run([sys.executable, "-c", _RUN, str(arch), str(case), str(tmp)], check=True, cwd=arch,
                           stdout=subprocess.DEVNULL)
            ref = json.loads(tmp.read_text(encoding="utf-8"))
            ref = dict(archive=f"{TAG} {commit}", made=date.today().isoformat(), archive_harness=harness_sha, **ref)
            (case / "archive_reference.json").write_text(json.dumps(ref, ensure_ascii=False), encoding="utf-8")
            print(f"   -> {case.name}/archive_reference.json: "
                  + ", ".join(f"{k} {len(v)} rows" for k, v in ref["sheets"].items()), flush=True)
    finally:
        shutil.rmtree(arch, ignore_errors=True)


if __name__ == "__main__":
    main()

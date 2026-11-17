"""get_vendor.py - downloads what the browser version runs on into web\\vendor (once; needs internet).

    python web\\get_vendor.py            (run_web.bat runs it when web\\vendor is missing or incomplete)

After that the browser version works offline: the page loads everything from web\\vendor, never from an outside site.
  vendor\\pyodide\\   Pyodide (Python in the browser) + the libraries that come with it (Pillow, lxml, cryptography, Jinja2 ...)
  vendor\\wheels\\    the libraries from PyPI (pdfplumber, pdfminer.six, pypdfium2, openpyxl, python-docx ...)
  vendor\\mupdf\\     MuPDF.js (the PDF engine - PyMuPDF has no browser version)
  vendor\\manifest.json   what the page loads, in order

The versions are fixed here (the ones tested, design\\web_version.md). Change one -> delete web\\vendor and run this again.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

PYODIDE = "314.0.7"
MUPDF = "1.28.6"
PYODIDE_URL = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE}/full/"
MUPDF_URL = f"https://cdn.jsdelivr.net/npm/mupdf@{MUPDF}/dist/"
CORE = ["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]
# libraries that come with Pyodide (built for the browser) - by their name in pyodide-lock.json; their own needs are added
FROM_PYODIDE = ["pillow", "lxml", "cryptography", "charset-normalizer", "jinja2", "typing-extensions"]
# libraries from PyPI: plain Python, or (pypdfium2) with an official browser wheel
FROM_PYPI = ["pdfminer.six==20260107", "pdfplumber==0.11.10", "pypdfium2==5.15.2", "openpyxl==3.1.5", "et-xmlfile==2.0.0",
             "python-docx==1.2.0"]
MUPDF_FILES = ["mupdf.js", "mupdf-wasm.js", "mupdf-wasm.wasm"]

HERE = Path(__file__).resolve().parent
VENDOR = HERE / "vendor"


def fetch(url: str, dst: Path, sha256: str | None = None) -> None:
    if dst.is_file() and dst.stat().st_size and (not sha256 or hashlib.sha256(dst.read_bytes()).hexdigest() == sha256):
        return
    print(f"  {dst.name}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "python-urllib"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = resp.read()
    if sha256 and hashlib.sha256(data).hexdigest() != sha256:
        raise SystemExit(f"{dst.name}: the download doesn't match its checksum - try again")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)


def main() -> None:
    pyo, wheels, mu = VENDOR / "pyodide", VENDOR / "wheels", VENDOR / "mupdf"
    print(f"Pyodide {PYODIDE}")
    for f in CORE:
        fetch(PYODIDE_URL + f, pyo / f)
    lock = json.loads((pyo / "pyodide-lock.json").read_text(encoding="utf-8"))["packages"]
    need, todo = [], list(FROM_PYODIDE)
    while todo:                                               # each library + what it needs
        n = todo.pop(0)
        if n not in need:
            need.append(n)
            todo += lock[n]["depends"]
    for n in need:
        fetch(PYODIDE_URL + lock[n]["file_name"], pyo / lock[n]["file_name"], lock[n]["sha256"])
    info = json.loads((pyo / "pyodide-lock.json").read_text(encoding="utf-8"))["info"]
    print("Libraries from PyPI")
    wheels.mkdir(parents=True, exist_ok=True)
    tag = "pyemscripten_" + info["abi_version"] + "_wasm32"
    pyver = "".join(info["python"].split(".")[:2])
    for spec in FROM_PYPI:
        name = spec.split("==")[0].replace("-", "_").replace(".", "_").lower()
        ver = spec.split("==")[1]
        if any(w.name.lower().startswith(f"{name}-{ver}-") for w in wheels.glob("*.whl")):
            continue
        print(f"  {spec}", flush=True)
        subprocess.run([sys.executable, "-m", "pip", "download", "-q", "--disable-pip-version-check", "--no-deps",
                        "--only-binary=:all:", "--platform", tag, "--platform", "any", "--python-version", pyver,
                        "--implementation", "cp", "--abi", f"cp{pyver}", "--abi", "abi3", "--abi", "none",
                        "-d", str(wheels), spec], check=True)
    print(f"MuPDF.js {MUPDF}")
    for f in MUPDF_FILES:
        fetch(MUPDF_URL + f, mu / f)
    manifest = dict(pyodide=PYODIDE, mupdf=MUPDF, python=info["python"], packages=need,
                    wheels=sorted(w.name for w in wheels.glob("*.whl")))
    (VENDOR / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    size = sum(p.stat().st_size for p in VENDOR.rglob("*") if p.is_file())
    print(f"Done - web\\vendor is ready ({size / 1e6:.0f} MB).")


if __name__ == "__main__":
    main()

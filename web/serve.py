"""serve.py - the tiny local server of the browser version (run_web.bat). It only hands out files: the page, Pyodide,
the libraries, MuPDF.js and the program itself. All reading and calculating happens in the browser tab; client documents
are never sent here (the server has no upload address at all).

    python web\\serve.py          -> http://127.0.0.1:5070   (port: environment variable U1040_WEB_PORT)

  /                 web\\index.html
  /<file>           web\\<file>        (worker.js, mupdf_bridge.mjs, vendor\\...)
  /static/<file>    static\\<file>     (the desktop's own CSS / JS - one copy)
  /app.zip          the program for the tab: core\\, templates\\, web\\py\\ ... built from this folder at each request
Later (phase 4) the same files go to Cloudflare Pages: bundle() below writes the same app.zip.
"""
from __future__ import annotations

import io
import os
import sys
import threading
import webbrowser
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB = Path(__file__).resolve().parent
ROOT = WEB.parent
PORT = int(os.environ.get("U1040_WEB_PORT", "5070"))
if "--port" in sys.argv:                                 # python web\serve.py --port 5072  (a second copy next to a running one)
    PORT = int(sys.argv[sys.argv.index("--port") + 1])
# never in the bundle: the office settings (local_settings.json) and any API key (.env) - they are simply not listed here
LEAVE_OUT: set = set()
EXTRA = ["ai_settings.json", "reference/K-1 1065 statement codes.csv", "tests/harness.py"]      # taken when they exist
NOT_YET = ("<!doctype html><meta charset='utf-8'><title>1040 Ultimate</title><link rel='stylesheet' href='/static/style.css'>"
           "<div class='wrap narrow'><h1>1040 Ultimate</h1><div class='banner'>This page isn't in the browser version yet "
           "(it comes with its own step - design/conversion_plan.md). <a href='javascript:history.back()'>← Back</a></div></div>")


def bundle() -> bytes:
    """The program as one zip: the engine (core), the pages' templates, the browser front door's Python (web/py)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, pattern in (("core", "*.py"), ("templates", "*"), ("web/py", "*.py")):
            for p in sorted((ROOT / folder).rglob(pattern)):
                rel = p.relative_to(ROOT).as_posix()
                if p.is_file() and "__pycache__" not in rel and rel not in LEAVE_OUT:
                    z.write(p, rel)
        for rel in EXTRA:
            if (ROOT / rel).is_file():
                z.write(ROOT / rel, rel)
    return buf.getvalue()


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".mjs": "text/javascript", ".js": "text/javascript",
                      ".wasm": "application/wasm", ".whl": "application/zip", ".json": "application/json"}

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WEB), **kw)

    def translate_path(self, path):
        clean = path.split("?", 1)[0].split("#", 1)[0]
        if clean.startswith("/static/"):
            return str(ROOT / "static" / clean[len("/static/"):].replace("..", ""))
        return super().translate_path(path)

    def end_headers(self):
        vendor = self.path.startswith("/vendor/")
        self.send_header("Cache-Control", "public, max-age=604800" if vendor else "no-store")
        super().end_headers()

    def do_GET(self):
        clean = self.path.split("?", 1)[0]
        if clean == "/app.zip":
            data = bundle()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if clean != "/" and not Path(self.translate_path(self.path)).is_file():
            data = NOT_YET.encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()

    def do_POST(self):                                   # nothing is ever uploaded
        self.send_error(405, "The browser version sends nothing to this server")

    def log_message(self, fmt, *args):
        if "--quiet" not in sys.argv:
            super().log_message(fmt, *args)


def main() -> None:
    if not (WEB / "vendor" / "manifest.json").is_file():
        raise SystemExit("web\\vendor is missing - run:  python web\\get_vendor.py   (needs internet once)")
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"1040 Ultimate - browser version:  {url}\nKeep this window open while working. Nothing is uploaded: "
          "the documents are read inside the browser tab.", flush=True)
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

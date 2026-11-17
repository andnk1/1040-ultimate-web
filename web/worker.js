// worker.js - Python (Pyodide) + MuPDF.js for the browser version, in a Web Worker so the page never freezes.
// Everything is loaded from this site's own vendor/ folder (no outside download site); the picked documents are copied
// onto Pyodide's in-memory drive (/client) and read there - nothing leaves the computer.
//   page -> worker:  {type: "run", files: [{path, file}], pyret, clientsum, docs}      {type: "keycheck", files, folder}
//   worker -> page:  load (start-up step) / ready / step (Run check progress) / done {html, seconds} / keys / problem / error
import { loadPyodide } from "./vendor/pyodide/pyodide.mjs";
import { makeBridge } from "./mupdf_bridge.mjs";

const say = (type, extra) => postMessage({ type, ...(extra || {}) });
const here = name => new URL(name, self.location).href;
let py = null;

async function init() {
  const t0 = performance.now();
  say("load", { msg: "Python (Pyodide)" });
  const manifest = await (await fetch(here("vendor/manifest.json"))).json();
  py = await loadPyodide({ indexURL: here("vendor/pyodide/") });
  say("load", { msg: "the libraries (pdfplumber, openpyxl, Word, Jinja2 …)" });
  await py.loadPackage([...manifest.packages, ...manifest.wheels.map(w => here("vendor/wheels/" + w))], { messageCallback() {} });
  say("load", { msg: "the PDF reader (MuPDF.js)" });
  const mupdf = await import("./vendor/mupdf/mupdf.js");
  py.registerJsModule("mupdf_bridge", makeBridge(mupdf));
  py.registerJsModule("webhost", { step: m => say("step", { msg: String(m) }) });
  say("load", { msg: "the program" });
  const zip = await (await fetch(here("app.zip"), { cache: "no-store" })).arrayBuffer();
  py.FS.mkdirTree("/app");
  py.unpackArchive(zip, "zip", { extractDir: "/app" });
  await py.runPythonAsync(`
import sys, os
sys.path[:0] = ["/app", "/app/web/py"]
os.makedirs("/client", exist_ok=True)
os.chdir("/app")
import webapp
`);
  say("ready", { seconds: (performance.now() - t0) / 1000, pyodide: manifest.pyodide, mupdf: manifest.mupdf, python: manifest.python });
}

// the picked files -> the in-memory drive (the old ones are removed first)
async function copyFiles(files) {
  py.runPython(`
import shutil, os
shutil.rmtree("/client", ignore_errors=True); shutil.rmtree("/work", ignore_errors=True)
os.makedirs("/client", exist_ok=True)
`);
  for (const f of files) {
    const dir = f.path.slice(0, f.path.lastIndexOf("/"));
    py.FS.mkdirTree(dir);
    py.FS.writeFile(f.path, new Uint8Array(await f.file.arrayBuffer()));
  }
}

async function call(code, args) {
  py.globals.set("ARGS", py.toPy(args));
  try {
    return await py.runPythonAsync(code);
  } finally {
    py.globals.delete("ARGS");
  }
}

const ready = init().catch(e => { say("error", { msg: "Couldn't start: " + (e && e.message || e) }); throw e; });

onmessage = async e => {
  const m = e.data;
  try {
    await ready;
    const t0 = performance.now();
    if (m.type === "run") {
      await copyFiles(m.files);
      const out = await call(`
import json, webapp, webhost
from core.runcheck import Problem
try:
    _token = webapp.run_check(ARGS["pyret"], list(ARGS["docs"]), webhost.step, clientsum=ARGS["clientsum"])
    _out = json.dumps(dict(html=webapp.summary_html(_token), token=_token))
except Problem as _e:
    _out = json.dumps(dict(problem=str(_e)))
_out
`, { pyret: m.pyret || "", clientsum: m.clientsum || "", docs: m.docs });
      const res = JSON.parse(out);
      if (res.problem) say("problem", { msg: res.problem });
      else say("done", { html: res.html, token: res.token, seconds: (performance.now() - t0) / 1000 });
    } else if (m.type === "keycheck") {
      await copyFiles(m.files);
      const out = await call(`
import json, keycheck, webhost
json.dumps(keycheck.check(ARGS["folder"], webhost.step))
`, { folder: m.folder });
      say("keys", { result: JSON.parse(out), seconds: (performance.now() - t0) / 1000 });
    }
  } catch (err) {
    say("error", { msg: String(err && err.message || err) });
  }
};

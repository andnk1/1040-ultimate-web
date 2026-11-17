// worker.js - Python (Pyodide) + MuPDF.js for the browser app, in a Web Worker so the page never freezes.
// Everything is loaded from this site's own vendor/ folder (no outside download site); the picked documents are copied
// onto Pyodide's in-memory drive (/client) and read there - nothing leaves the computer.
//
//   page -> worker
//     {type: "run", files: [{path, file}], pyret, clientsum, docs, stuck}   Run check, then the Summary page
//     {type: "request", id, method, url, body}    one address of a page (a link, a save, a download) - web/py/routes.py
//     {type: "call", id, fn, args}                one of the start's helpers in web/py/webapp.py (passwords, stuck text)
//     {type: "keycheck" | "archivecheck", files, folder}   the test checks (web/py/keycheck.py)
//   worker -> page
//     load (start-up step) / ready / step (Run check progress) / done {token, page, seconds} / reply {id, ...} /
//     save {name, bytes} (a file for the client folder) / keys {result} / problem / error
import { loadPyodide } from "./vendor/pyodide/pyodide.mjs";
import { makeBridge } from "./mupdf_bridge.mjs";

const say = (type, extra, transfer) => postMessage({ type, ...(extra || {}) }, transfer || []);
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
  // what Python can ask of the page: a progress line, and a file to keep in the client folder (web/index.html saveFile)
  py.registerJsModule("webhost", {
    step: m => say("step", { msg: String(m) }),
    save: (name, data) => { const bytes = data.toJs(); say("save", { name: String(name), bytes }, [bytes.buffer]); },
  });
  say("load", { msg: "the program" });
  const zip = await (await fetch(here("app.zip"), { cache: "no-store" })).arrayBuffer();
  py.FS.mkdirTree("/app");
  py.unpackArchive(zip, "zip", { extractDir: "/app" });
  await py.runPythonAsync(`
import sys, os
sys.path[:0] = ["/app", "/app/web/py"]
os.makedirs("/client", exist_ok=True)
os.chdir("/app")
import webapp, routes
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

// a Python value -> a plain JavaScript one (dicts become objects, bytes become Uint8Array)
function toJs(value) {
  if (!value || typeof value.toJs !== "function") return value;
  const out = value.toJs({ dict_converter: Object.fromEntries, create_pyproxies: false });
  value.destroy();
  return out;
}

// one address of a page -> routes.handle (web/py/routes.py)
function request(m) {
  const reply = toJs(py.globals.get("routes").handle(m.method, m.url, m.body || ""));
  const transfer = reply.body instanceof Uint8Array ? [reply.body.buffer] : [];
  say("reply", { id: m.id, ...reply }, transfer);
}

// the start's helpers that the page may call (nothing else is callable this way)
const CALLS = new Set(["password_candidates", "stuck_message"]);
function call(m) {
  if (!CALLS.has(m.fn)) throw new Error("not callable: " + m.fn);
  const fn = py.globals.get("webapp")[m.fn];
  say("reply", { id: m.id, kind: "value", body: toJs(fn(...m.args.map(a => py.toPy(a)))) });
}

async function runPython(code, args) {
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
    if (m.type === "request") return request(m);
    if (m.type === "call") return call(m);
    if (m.type === "run") {
      await copyFiles(m.files);
      const out = await runPython(`
import json, webapp, webhost, routes
from core.runcheck import Problem
try:
    _token = webapp.run_check(ARGS["pyret"], list(ARGS["docs"]), webhost.step, clientsum=ARGS["clientsum"],
                              stuck=list(ARGS["stuck"]))
    _out = json.dumps(dict(token=_token, page=routes.handle("GET", "/summary/" + _token)["body"]))
except Problem as _e:
    _out = json.dumps(dict(problem=str(_e)))
_out
`, { pyret: m.pyret || "", clientsum: m.clientsum || "", docs: m.docs, stuck: m.stuck || [] });
      const res = JSON.parse(out);
      if (res.problem) say("problem", { msg: res.problem });
      else say("done", { token: res.token, page: res.page, seconds: (performance.now() - t0) / 1000 });
    } else if (m.type === "keycheck" || m.type === "archivecheck") {
      await copyFiles(m.files);
      const fn = m.type === "keycheck" ? "check" : "check_archive";
      const out = await runPython(`
import json, keycheck, webhost
json.dumps(keycheck.${fn}(ARGS["folder"], webhost.step))
`, { folder: m.folder });
      say("keys", { result: JSON.parse(out), seconds: (performance.now() - t0) / 1000 });
    }
  } catch (err) {
    if (m.id) say("reply", { id: m.id, kind: "error", status: 500, body: String(err && err.message || err) });
    else say("error", { msg: String(err && err.message || err) });
  }
};

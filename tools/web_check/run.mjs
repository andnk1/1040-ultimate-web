// run.mjs - runs a Python script on the browser version's engine (Pyodide + MuPDF.js from web/vendor), outside a browser.
//   node tools/web_check/run.mjs <script.py> [name=folder ...] [-- script arguments]
// The app folder is at /app; each name=folder is at /<name> (e.g. data=tests/samples/Sample -> /data).
// Same Pyodide, same wheels, same MuPDF.js and the same bridge (web/mupdf_bridge.mjs) as the page uses.
import fs from "fs";
import path from "path";
import { fileURLToPath, pathToFileURL } from "url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..", "..");
const vendor = path.join(root, "web", "vendor");
const { loadPyodide } = await import(pathToFileURL(path.join(vendor, "pyodide", "pyodide.mjs")));
const mupdf = await import(pathToFileURL(path.join(vendor, "mupdf", "mupdf.js")));
const { makeBridge } = await import(pathToFileURL(path.join(root, "web", "mupdf_bridge.mjs")));

const args = process.argv.slice(2);
const script = args.shift();
const cut = args.indexOf("--");
const mounts = (cut < 0 ? args : args.slice(0, cut)).filter(a => a.includes("="));
const rest = cut < 0 ? [] : args.slice(cut + 1);
const manifest = JSON.parse(fs.readFileSync(path.join(vendor, "manifest.json"), "utf8"));

const t0 = Date.now();
const py = await loadPyodide({ indexURL: path.join(vendor, "pyodide") + path.sep });
await py.loadPackage([...manifest.packages, ...manifest.wheels.map(w => path.join(vendor, "wheels", w).split(path.sep).join("/"))], { messageCallback() {} });
py.registerJsModule("mupdf_bridge", makeBridge(mupdf));
const mount = (name, dir) => { py.FS.mkdirTree("/" + name); py.FS.mount(py.FS.filesystems.NODEFS, { root: path.resolve(dir) }, "/" + name); };
mount("app", root);
for (const m of mounts) mount(m.slice(0, m.indexOf("=")), m.slice(m.indexOf("=") + 1));
console.error(`engine ready in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
py.globals.set("ARGV", py.toPy(["/app/" + script.split(path.sep).join("/"), ...rest]));
py.runPython(`
import sys, os, runpy
sys.argv = list(ARGV)
sys.path[:0] = ["/app", "/app/web/py"]
os.chdir("/app")
runpy.run_path(sys.argv[0], run_name="__main__")
`);

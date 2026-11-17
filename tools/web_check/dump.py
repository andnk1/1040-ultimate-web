"""dump.py - what the PDF door gives for every PDF of a folder: text, words, blocks, "dict" lines, filled shapes.
Run it on the desktop engine and on the browser engine, then compare (compare.py):
    python tools/web_check/dump.py <folder> <out.json>
    node tools/web_check/run.mjs tools/web_check/dump.py data=<folder> out=<out folder> -- /data /out/web.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core import pdfengine                      # noqa: E402
from core.pdfutil import open_pdf               # noqa: E402

folder, out = Path(sys.argv[1]), sys.argv[2]
r1 = lambda v: round(v, 1)
res = {"engine": pdfengine.NAME, "files": {}}
for p in sorted(folder.rglob("*")):
    if p.suffix.lower() != ".pdf":
        continue
    rel = p.relative_to(folder).as_posix()
    try:
        doc, pw = open_pdf(p)
    except Exception as e:                      # noqa: BLE001
        res["files"][rel] = {"error": f"{type(e).__name__}: {e}"}
        continue
    pages = []
    with doc:
        producer = (doc.metadata or {}).get("producer") or ""
        for page in doc:
            words = [[r1(w[0]), r1(w[1]), r1(w[2]), r1(w[3]), w[4], w[5], w[6], w[7]] for w in page.get_text("words")]
            blocks = [[r1(b[0]), r1(b[1]), r1(b[2]), r1(b[3]), b[4]] for b in page.get_text("blocks", sort=True) if b[6] == 0]
            lines = [[r1(l["bbox"][1]), "".join(s["text"] for s in l["spans"])]
                     for b in page.get_text("dict")["blocks"] for l in b.get("lines", [])]
            fills = sorted([[round(c, 2) for c in d["fill"][:3]], [r1(v) for v in d["rect"]]]
                           for d in page.get_drawings() if d.get("fill"))
            pages.append(dict(width=r1(page.rect.width), text=page.get_text(), words=words, blocks=blocks, lines=lines, fills=fills))
    res["files"][rel] = dict(pages=pages, producer=producer, password=bool(pw))
    print(f"read  {rel}  ({len(pages)} pages)", file=sys.stderr)
Path(out).write_text(json.dumps(res), encoding="utf-8")

"""compare.py - two dump.py results side by side:  python tools/web_check/compare.py desktop.json web.json
Per file: SAME, or the first difference of each kind (text / words / blocks / dict lines / filled shapes) per page."""
import json
import sys

a, b = (json.load(open(f, encoding="utf-8")) for f in sys.argv[1:3])
print(f'{a["engine"]}  vs  {b["engine"]}')
same = diff = 0
kinds = dict.fromkeys(("width", "text", "words", "blocks", "lines", "fills"), 0)
for rel in sorted(a["files"]):
    fa, fb = a["files"][rel], b["files"].get(rel)
    notes = []
    if fb is None:
        notes.append("not in the second file")
    elif "error" in fa or "error" in fb:
        if fa.get("error") != fb.get("error"):
            notes.append(f'error: {fa.get("error")} vs {fb.get("error")}')
    else:
        for k in ("producer", "password"):
            if fa[k] != fb[k]:
                notes.append(f"{k}: {fa[k]!r} vs {fb[k]!r}")
        if len(fa["pages"]) != len(fb["pages"]):
            notes.append(f'pages: {len(fa["pages"])} vs {len(fb["pages"])}')
        for i, (pa, pb) in enumerate(zip(fa["pages"], fb["pages"])):
            for k in kinds:
                if pa[k] != pb[k]:
                    kinds[k] += 1
                    x, y = pa[k], pb[k]
                    if isinstance(x, list):
                        j = next((n for n, (u, v) in enumerate(zip(x, y)) if u != v), min(len(x), len(y)))
                        notes.append(f"page {i + 1} {k}: {len(x)} vs {len(y)}; first at #{j}: {str(x[j:j + 1])[:110]} vs {str(y[j:j + 1])[:110]}")
                    elif isinstance(x, str):
                        j = next((n for n, (u, v) in enumerate(zip(x, y)) if u != v), min(len(x), len(y)))
                        notes.append(f"page {i + 1} {k}: at character {j}: {x[max(0, j - 20):j + 30]!r} vs {y[max(0, j - 20):j + 30]!r}")
                    else:
                        notes.append(f"page {i + 1} {k}: {x} vs {y}")
    if notes:
        diff += 1
        print(f"DIFFERENT  {rel}")
        for n in notes[:8]:
            print("   " + n)
        if len(notes) > 8:
            print(f"   ... and {len(notes) - 8} more")
    else:
        same += 1
print(f"\nRESULT: {same} same, {diff} different   (pages that differ, by kind: {kinds})")

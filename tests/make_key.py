"""make_key.py - writes the draft answer key (answer_key.xlsx) of every test case in tests\\samples from what the program
reads now, for the preparer to check against the PDFs, correct and initial (Checked column).

    python tests\\make_key.py            every case
    python tests\\make_key.py Sample     only these cases (folder names)

A case with no key gets a new one. A case that has a key only gets rows for files that have none yet (a document added to the
folder); no row already in a key is ever changed - a checked key stays as it is. A file taken out of the folder loses its rows,
unless one of them is checked (then they stay and the tests report them). To start a key over, delete the answer_key.xlsx
(only when nothing in it was checked).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness as h  # noqa: E402


def make(case: Path) -> str:
    key_path = case / h.KEY_NAME
    existing = h.load_key(key_path) if key_path.exists() else None
    roles = dict(existing["roles"]) if existing else {}
    files = [p.name for p in h.case_files(case)]
    new = [f for f in files if f not in roles]
    gone = [f for f in roles if f not in files]
    kept = [f for f in gone if any(x["file"] == f and x["checked"] for s, _ in h.SHEETS for x in existing[s])] if existing else []
    drop = [f for f in gone if f not in kept]
    if existing and not new and not drop:
        return "key up to date (no new files)" + (f"; checked rows kept for files no longer in the folder: {'; '.join(kept)}"
                                                  if kept else "")
    if new:
        guess = h.guess_roles(case)
        roles.update({f: guess.get(f, "Document") for f in new})
    for f in drop:
        roles.pop(f, None)
    data = h.read_all(case, roles)
    try:
        added = h.write_key(key_path, {f: roles[f] for f in files if f in roles}, data, existing, drop)
    except PermissionError:
        return f"couldn't write {h.KEY_NAME} — close it in Excel and run again"
    if not existing:
        return f"new draft key: " + ", ".join(f"{s} {n} rows" for s, n in added.items())
    msg = ("rows added / removed: " + ", ".join(f"{s} {n}" for s, n in added.items())) if added else "new files have nothing to add"
    return msg + (f"; checked rows kept for files no longer in the folder: {'; '.join(kept)}" if kept else "")


def main(names: list[str]) -> None:
    cases = [c for c in h.case_dirs() if not names or c.name in names]
    if not cases:
        print("No test cases found in", h.SAMPLES)
        return
    for c in cases:
        print(f"{c.name}: ", end="", flush=True)
        try:
            print(make(c))
        except Exception as e:  # noqa: BLE001
            print(f"FAILED — {type(e).__name__}: {e}")


if __name__ == "__main__":
    main(sys.argv[1:])

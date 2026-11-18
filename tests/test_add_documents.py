"""test_add_documents.py - Add more documents… (Document inventory, brief 2026-11-17): documents added to a run that is open.

On the Sample case: Run check with half of the documents, a correction and a tick, then the other half added
(web/py/webapp.py add_documents). The correction and the tick must still be there, the income and deduction summary must
be the same as a run with every document from the start (with the same correction and tick), and only the new files may be
read during the add.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import harness as h

CASE = h.SAMPLES / "Sample"


def _sc():
    return h._scenario()


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    if not (CASE / h.KEY_NAME).exists():
        pytest.skip("the Sample case isn't on this computer")
    import webapp
    from core import runcheck
    webapp.WORK = tmp_path_factory.mktemp("work")          # (in the browser: the tab's in-memory drive)
    roles = h.load_key(CASE / h.KEY_NAME)["roles"]
    pick = lambda role: next((str(CASE / n) for n, x in roles.items() if x == role and (CASE / n).is_file()), "")
    docs = [str(CASE / n) for n, x in roles.items() if x == "Document" and (CASE / n).is_file()]
    form = dict(pyret=pick("Prior-year return"), karbon="", clientsum="", utscreens=pick("UT input screens"), wip="")
    first, later = docs[: len(docs) // 2], docs[len(docs) // 2:]

    def edits(r):
        """A correction on the first income line read from a document of the first half, and a tick on it."""
        inc, _ = runcheck.summaries(r)
        row = next(x for s in inc["sections"] for x in s["rows"] if x.get("doc_cy") is not None and x.get("id"))
        h.page("POST", f"/edits/{r['token']}", {row["id"]: {"cy": round(row["doc_cy"] + 100, 2), "note": "corrected"}})
        h.page("POST", f"/marks/{r['token']}", {"inc|" + row["id"]: True})
        return row["id"]

    # 1. half of the documents, the edits, then the rest added - counting which files the readers open during the add
    from core import inventory, readcache
    readcache.clear()                                   # (earlier tests may have read the same files)
    r1 = h.open_run(runcheck.run(form, first, work_dir=webapp.WORK / "a"))
    rid = edits(r1)
    opened = []
    real_scan, real_parse, real_py = inventory._what_it_is, runcheck.parse_document, runcheck.read_prior_return
    inventory._what_it_is = lambda p, *a: (opened.append(("type", Path(p).name)), real_scan(p, *a))[1]
    runcheck.parse_document = lambda d: (opened.append(("amounts", d["file"])), real_parse(d))[1]
    runcheck.read_prior_return = lambda p: (opened.append(("prior-year return", Path(p).name)), real_py(p))[1]
    try:
        token = webapp.add_documents(r1["token"], first + later)
    finally:
        inventory._what_it_is, runcheck.parse_document, runcheck.read_prior_return = real_scan, real_parse, real_py
    added = h.open_run(__import__("pages").RUNS[token])
    # 2. every document from the start, the same edits
    r2 = h.open_run(runcheck.run(form, docs, work_dir=webapp.WORK / "b"))
    edits(r2)
    return dict(added=added, whole=r2, rid=rid, first=first, later=later, opened=opened)


def test_work_kept(runs):
    r, rid = runs["added"], runs["rid"]
    assert rid in r["edits"] and r["edits"][rid]["note"] == "corrected"
    assert r["marks"].get("inc|" + rid) is True


def test_new_documents_are_read(runs):
    names = {d["file"] for d in runs["added"]["inv"]["docs"]}
    assert all(p.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] in names for p in runs["later"])


def test_same_as_all_documents_from_the_start(runs):
    from core import runcheck
    sc = _sc()
    a = sc.normalize(dict(zip(("income", "deductions"), runcheck.summaries(runs["added"]))))
    b = sc.normalize(dict(zip(("income", "deductions"), runcheck.summaries(runs["whole"]))))
    diffs = sc.differences(b, a)
    assert not diffs, "\n".join(diffs)


def test_new_documents_get_their_ai_tick(runs):
    from core import runcheck
    r = runs["added"]
    defaults = runcheck.default_to_ai(r)
    for p in runs["later"]:
        assert r["to_ai"].get(p) == defaults.get(p), json.dumps({p: [r["to_ai"].get(p), defaults.get(p)]})


def test_only_the_new_files_are_read(runs):
    """Lady, 2026-11-17: Add more documents reads only the new files (core/readcache.py keeps what was read)."""
    new = {Path(p).name for p in runs["later"]}
    read = {name for _, name in runs["opened"]}
    assert read, "nothing was read during the add - the new documents must be"
    assert read <= new, f"old files read again: {sorted(read - new)}"
    assert not any(kind == "prior-year return" for kind, _ in runs["opened"])

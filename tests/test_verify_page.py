"""test_verify_page.py - page 2 · Verify return in the browser app (web/py/pages/verify.py).

What the archive check (test_archive.py, "Page: verify") can't see, because the desktop had no such thing:
- the review Excel goes into the client folder when Chrome lets the app write there, else it is downloaded;
- the master checklist is a file on the shared drive: its text comes from the page; a new file gets the list as it is;
  a checklist not changed yet starts again from it; a file that isn't a master checklist is refused;
- a PDF the stuck-PDF guard couldn't open is reported with the desktop's message and not read;
- the prior-year return picked again (another copy of the same file) is refused.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import harness as h

CASE = h.SAMPLES / "Sample"


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if not (CASE / h.KEY_NAME).exists():
        pytest.skip("the Sample case isn't on this computer")
    import core.verify as verify_mod
    from core import runcheck
    tmp = tmp_path_factory.mktemp("verify")
    old, verify_mod.MASTER = verify_mod.MASTER, tmp / "checklist_master.json"
    roles = h.load_key(CASE / h.KEY_NAME)["roles"]
    pick = lambda role: next((str(CASE / n) for n, x in roles.items() if x == role and (CASE / n).is_file()), "")
    docs = [str(CASE / n) for n, x in roles.items() if x == "Document" and (CASE / n).is_file()]
    form = dict(pyret=pick("Prior-year return"), karbon="", clientsum="", utscreens="", wip="")
    r = h.open_run(runcheck.run(form, docs, work_dir=tmp / "work"))
    r["wip_path"] = (tmp / "client" / "1040 Ultimate WIP test.json").as_posix()   # (the in-memory drive's / paths)
    (tmp / "client").mkdir()
    r["_ut"], r["_tmp"] = pick("UT input screens"), tmp
    yield r
    verify_mod.MASTER = old


def _post(r, url, body):
    rep = h.page("POST", url.format(token=r["token"]), body)
    assert rep["status"] == 200, rep
    return rep["body"]


def test_stuck_pdf_is_not_read(run):
    j = _post(run, "/verify/{token}/run", {"path": "", "ut": run["_ut"], "stuck": "the PDF reader got stuck"})
    assert j == {"ok": False, "error": "the PDF reader got stuck"} and run["ut_scr"] is None


def test_prior_year_return_again_is_refused(run, tmp_path):
    copy = tmp_path / "another copy.pdf"
    shutil.copy2(run["form"]["pyret"], copy)
    j = _post(run, "/verify/{token}/run", {"path": str(copy), "ut": ""})
    assert j["error"] == "That's the prior-year return — choose the 2025 return."


def test_review_excel_folder_or_download(run):
    assert _post(run, "/verify/{token}/run", {"path": "", "ut": run["_ut"]})["ok"]
    run["places"] = []                                   # Chrome lets the app write nowhere: a download
    j = _post(run, "/verify/{token}/save", {})
    assert j["download"] == f"/verify/{run['token']}/review.xlsx" and j["file"].startswith("Review ")
    f = h.page("GET", j["download"])
    assert f["kind"] == "file" and f["filename"] == j["file"] and f["body"][:2] == b"PK"
    run["places"] = [(run["_tmp"] / "client").as_posix() + "/"]  # the client folder Chrome lets the app edit: written there
    j = _post(run, "/verify/{token}/save", {})
    assert "download" not in j and (run["_tmp"] / "client" / j["saved"].rsplit("/", 1)[-1]).is_file()


def test_master_checklist_file(run):
    from pages import verify
    import core.verify as verify_mod
    run["checklist"] = None
    assert h.page("GET", f"/verify/{run['token']}")["status"] == 200       # the checklist starts from the built-in list
    assert run["_cl_fresh"] and len(run["checklist"]) == len(verify_mod.DEFAULT_CHECKLIST)
    assert _post(run, "/verify/{token}/master", {"name": "notes.json", "text": "[1, 2]"})["ok"] is False
    shared = json.dumps({"items": ["Shared line 1", "Shared line 2"]})
    assert _post(run, "/verify/{token}/master", {"name": "checklist_master.json", "text": shared})["items"] == 2
    assert verify.MASTER["connected"] and run["checklist"] is None          # not changed yet: starts again from it
    h.page("GET", f"/verify/{run['token']}")
    assert [x["text"] for x in run["checklist"]] == ["Shared line 1", "Shared line 2"]
    cl = run["checklist"] + [dict(text="Every client", done=False, stays=True, master=False, note="")]
    assert _post(run, "/verify/{token}/checklist", cl) == {"ok": True, "master": 3, "kept": True}
    assert json.loads(verify_mod.MASTER.read_text(encoding="utf-8"))["items"][-1] == "Every client"
    # connected again to a checklist the preparer changed: kept, but only the shared list's lines are master lines, so a
    # line from another list never reaches the office's list; the shared lines missing are added
    run["checklist"][0]["note"] = "typed"
    run["checklist"].append(dict(text="Built-in line", done=True, stays=True, master=True, note=""))
    _post(run, "/verify/{token}/master", {"name": "checklist_master.json",
                                          "text": json.dumps({"items": ["Shared line 1", "Shared line 3"]})})
    got = {x["text"]: (x["master"], x["stays"]) for x in run["checklist"]}
    assert got == {"Shared line 1": (True, True), "Shared line 2": (False, False), "Every client": (False, False),
                   "Built-in line": (False, False), "Shared line 3": (True, True)}
    assert run["checklist"][0]["note"] == "typed"
    assert _post(run, "/verify/{token}/checklist", run["checklist"])["master"] == 2
    verify_mod.MASTER.unlink()
    assert _post(run, "/verify/{token}/master", {"name": "new.json", "text": ""})["items"] == len(verify_mod.DEFAULT_CHECKLIST)
    assert verify_mod.MASTER.is_file()                                        # a new file gets the list as it is
    _post(run, "/verify/{token}/master", {"name": "checklist_master.json", "waiting": True})
    assert verify.MASTER == dict(name="checklist_master.json", connected=False, waiting=True)
    verify.MASTER.update(name="", connected=False, waiting=False)


def test_digital_assets_misaligned_print():
    """UT's "Digital Assets Transactions" section prints its first line one column off: the units sold ("1") under
    "1=S,2=L", the term under "Force", the price cut off. Only the AMT Gain -Loss (second line) and the term are read, so
    the units never show up as an amount (made-up words laid out like the real print)."""
    from core.utscreens import _digital_assets

    def row(*words, y=0):                                # (x0, y0, x1, y1, text)
        return [(x, y, x + len(t) * 5, y + 8, t) for x, t in words]
    head = [row((47, "8949"), (82, "Transaction"), (253, "Units"), (593, "Date"), (777, "Sale")),
            row((20, "TSJ"), (49, "Box"), (254, "Sold"), (679, "1=S,2=L"), (726, "Force"), (778, "Pric")),
            row((54, "AMT"), (75, "Adj"), (91, "G/L"), (128, "AMT"), (149, "Gain"), (201, "Fed"), (258, "State")),
            row((69, "If"), (77, "Diff"), (136, "-Loss"), (199, "W/H"), (260, "W/H"))]
    body = [row((18, "T"), (45, "H/K"), (403, "DIGITAL"), (441, "ASSETS"), (584, "VARIOUS"), (629, "VARIOUS"), (712, "1"),
                (759, "$"), (778, "210")),
            row((58, "$"), (120, "$"), (158, "648"), (180, "$")),
            row((18, "T"), (45, "I/L"), (403, "DIGITAL"), (441, "ASSETS"), (712, "1"), (788, "4")),
            row((153, "-140")),
            row((18, "T"), (45, "I/L"), (403, "DIGITAL"), (441, "ASSETS"), (712, "1"), (747, "2")),
            row((168, "5")),
            row((42, "TOTAL"), (759, "$"), (778, "215")),
            row((58, "$"), (106, "0"), (158, "513"))]
    got = [(e["amount"], e["cat"], e["box"], e["label"]) for e in _digital_assets(head, body, "Digital Assets Transactions", 20)]
    assert got == [(648.0, "st", "H", "DIGITAL ASSETS"), (-140.0, "st", "I", "DIGITAL ASSETS"), (5.0, "lt", "L", "DIGITAL ASSETS")]

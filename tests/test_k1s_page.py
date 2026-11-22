"""test_k1s_page.py - the K-1s page (brief 2026-11-21, step 3), on copies of the Sample K-1 PDFs.
One tab per K-1 form (the count = K-1s, not files), each file name opens the PDF, no banner / entry check button, the
stand-alone reader is gone, and Add K-1 PDFs… reads only the new file (the others come from core/readcache.py)."""
from __future__ import annotations

import json
import shutil

import pytest

import harness as h

SRC = h.SAMPLES / "Sample"


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    k1s = sorted(p.name for p in SRC.glob("*.pdf") if "K-1" in p.name)
    if len(k1s) < 2:
        pytest.skip("the Sample K-1 PDFs aren't there")
    folder = tmp_path_factory.mktemp("k1s_page")
    for n in k1s:
        shutil.copy2(SRC / n, folder / n)
    from core import readcache
    readcache.clear()                                         # as a new Run check does (web/py/webapp.py)
    a = h._app()
    c = a.app.test_client()
    first = k1s[:-1]                                          # the last K-1 PDF is added later with Add K-1 PDFs…
    resp = c.post("/run", data=dict(mode="summary", pyret="", utscreens="", karbon="", clientsum="", wip="",
                                    docs=json.dumps([dict(path=str(folder / n), on=True) for n in first])))
    r = a.RUNS[resp.headers["Location"].rsplit("/", 1)[-1]]
    r["wip_path"] = str(folder / "1040 Ultimate WIP 2025 - Test.json")        # the K-1 work file goes next to it
    html = c.get(f"/k1v/?for={r['token']}").get_data(as_text=True)
    tok, run = a.k1v_web.run_for(r["token"])
    return dict(folder=folder, files=k1s, first=first, r=r, c=c, a=a, tok=tok, run=run, html=html)


def test_the_page(case):
    html, run, r = case["html"], case["run"], case["r"]
    assert "<title>K-1s</title>" in html and "<h1>K-1s</h1>" in html
    assert f"&larr; 1040 Ultimate (this client)</a>" in html and f'href="/summary/{r["token"]}"' in html
    n1065 = sum(1 for k in run["k1s"] if k["form"] == "1065")
    n1120 = sum(1 for k in run["k1s"] if k["form"] == "1120-S")
    assert f"K-1 1065 ({n1065})" in html and f"K-1 1120-S ({n1120})" in html          # K-1s, not files
    assert html.count("/open?path=") >= len(case["first"])                         # each file name opens the PDF
    assert all(n in html for n in case["first"])
    assert ">K-1 Verification</a>" in html and ">K-1 UT</a>" in html and "K-1 UT — not built yet" in html
    for gone in ("K-1 entry check", "Input Screens", "1 &middot; Read", "2 &middot; Open", "<form", "K-1 Interpreter"):
        assert gone not in html, gone
    assert "Schedule K-1 (Form 1120-S) &mdash; boxes and codes" in html              # the 1120-S code table stays


def test_k1_verification_by_form(case):
    """Each tab's K-1 Verification shows only that form's K-1s (Lady, 2026-11-21): the others stay on the page, hidden,
    so its saves / totals / Add to Income Summary are unchanged. 1120-S: no totals, Excel or Add (1065 only)."""
    c, tok, html = case["c"], case["tok"], case["html"]
    assert f"/k1v/k1/{tok}?form=1065" in html and f"/k1v/k1/{tok}?form=1120-S" in html
    p1065 = c.get(f"/k1v/k1/{tok}?form=1065").get_data(as_text=True)
    assert 'const FORM = "1065"' in p1065 and 'id="upbtn"' in p1065 and 'id="calc"' in p1065
    p1120 = c.get(f"/k1v/k1/{tok}?form=1120-S").get_data(as_text=True)
    assert 'const FORM = "1120-S"' in p1120 and 'id="upbtn"' not in p1120 and 'id="calc"' not in p1120
    assert "&amp;tab=s1120" in p1120 or "&tab=s1120" in p1120                    # "← K-1s" back to the 1120-S tab
    assert 'const FORM = ""' in c.get(f"/k1v/k1/{tok}?form=W-2").get_data(as_text=True)   # anything else: every K-1
    assert all(f'"page": {k["page"]}' in p1120 for k in case["run"]["k1s"])        # every K-1 is still on the page


def test_k1_verification_name_links(case):
    """Step 4: the page is called K-1 Verification; each K-1's name opens its PDF at its page - the page knows the run's PDFs in
    order (a K-1's page 1003 = the 2nd PDF's page 3) and shows the real page, never the file-coded number."""
    import re
    p = case["c"].get(f"/k1v/k1/{case['tok']}?form=1065").get_data(as_text=True)
    assert "<title>K-1 Verification</title>" in p and ">K-1 Verification</h1>" in p and "K-1 Interpretation" not in p
    docs = json.loads(re.search(r"const DOCS = (\[.*?\]);\n", p).group(1))
    assert [n for _, n in docs] == [n for _, n in case["run"]["files"]]
    assert "nameLink(k)" in p and "PDF page ${k.page}" not in p and "pageLbl(k)" in p
    assert "/open?path=${encodeURIComponent(d[0])}&page=${k.page % 1000}" in p


def test_no_k1_screens_reason_is_kept(monkeypatch, tmp_path):
    """Step 6: a UT print without K-1 screens - the reason is kept in the K-1 run and in the 1040 run (for Verify return)."""
    from core import runcheck
    from core.k1v import runs
    tok, _, _ = runs.make_run([])
    monkeypatch.setattr(runs, "parse_screens", lambda path: {"units": []})
    err = runs.attach_screens(tok, tmp_path / "print.pdf")
    assert err.startswith("No K-1 input screens") and runs.RUNS[tok]["scr_error"] == err
    r = {"token": "t-noscr", "k1v_token": tok}
    monkeypatch.setattr(runcheck, "read_ut_screens", lambda path: {"entries": [1]})
    runcheck.load_ut(r, str(tmp_path / "print.pdf"))
    assert r["k1_scr_error"] == err


def test_a_file_goes_to_the_tab_of_its_k1s():
    from pages.k1 import _form_tabs
    run = dict(files=[("/c/a.pdf", "a.pdf"), ("/c/b.pdf", "b.pdf"), ("/c/c.pdf", "c.pdf")],
               k1s=[dict(form="1065", page=1), dict(form="1120-S", page=1001), dict(form="1065", page=1003)])
    t1065, t1120 = _form_tabs(run)
    assert t1065["count"] == 2 and t1120["count"] == 1
    assert [f["name"] for f in t1065["files"]] == ["a.pdf", "b.pdf", "c.pdf"]       # c.pdf: no K-1 read -> on both tabs
    assert [f["name"] for f in t1120["files"]] == ["b.pdf", "c.pdf"]                # b.pdf has both kinds
    assert [f["k1s"] for f in t1065["files"]] == [1, 1, 0] and t1065["files"][2]["none_read"]


def test_no_reader_on_its_own(case):
    html = case["c"].get("/k1v/").get_data(as_text=True)
    assert "Open the K-1s from a client's Summary (K-1 box &rarr; Open K-1 Tab)." in html and "<form" not in html
    import routes
    from pages import k1
    assert not hasattr(k1, "read_on_its_own")
    assert not any(m == "POST" and a == "/k1v/" for m, a, *_ in routes.ROUTES)


def test_add_reads_only_the_new_file(case, monkeypatch):
    from core.k1v import runs
    read = []
    real = runs.parse_pdf
    monkeypatch.setattr(runs, "parse_pdf", lambda path, **kw: (read.append(path), real(path, **kw))[1])
    new = case["folder"] / case["files"][-1]
    j = case["c"].post(f"/k1v/files/{case['tok']}", json={"paths": [str(new)]}).get_json()
    assert j["ok"] and j["added"] == 1
    assert [p.replace("\\", "/").rsplit("/", 1)[-1] for p in read] == [new.name]   # only the new file was read
    html = case["c"].get(f"/k1v/?for={case['r']['token']}").get_data(as_text=True)
    assert new.name in html

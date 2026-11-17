"""test_ut_export_format.py - the UT data entry export matches its written format (design\\ut_export_format.md).

The format document is the contract with the separate UT Data Entry app. This test reads the document's two tables (the
columns, the Part II items) and checks every row the export writes against them and against "Rules per column".
Two exports are checked: a made-up K-1 (always) and the K-1 test samples (when tests\\samples\\K-1_Sample is on this computer).
"""
from __future__ import annotations

import collections
import csv
import io
import re
from pathlib import Path

import pytest

import harness as h
from core.k1v import prep, runs, ut_entry

FORMAT = h.APP_DIR / "design" / "ut_export_format.md"


# ---------------------------------------------------------------- what the document says
def _table(title: str) -> list[list[str]]:
    """The rows of the markdown table under the heading `## <title>` (first cell without its `backticks`)."""
    text = FORMAT.read_text(encoding="utf-8")
    part = text.split(f"## {title}", 1)[1].split("\n## ", 1)[0]
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in part.splitlines() if line.strip().startswith("|")]
    return [[r[0].strip("`")] + r[1:] for r in rows[2:]]          # skip the header and the |---| line


COLUMNS = [r[0] for r in _table("Columns")]
ITEMS = {r[0]: r[1] for r in _table("Part II items (K-1 1065)")}   # item -> its entry (bot / hand)


def test_document_and_code_agree_on_the_columns():
    assert COLUMNS == prep.CSV_COLUMNS, "design\\ut_export_format.md and core\\k1v\\prep.py list different columns"


# ---------------------------------------------------------------- the rules, row by row
def check_export(data: bytes) -> list[dict]:
    """Reads an export the way UT Data Entry does and checks every row against the rules. Returns the rows."""
    rows = list(csv.reader(io.StringIO(data.decode("utf-8"))))
    assert rows and rows[0] == COLUMNS, "rule 1: the header row"
    out = [dict(zip(COLUMNS, r)) for r in rows[1:]]
    who = collections.defaultdict(set)
    for n, x in enumerate(out, start=2):
        where = f"row {n} ({x['box']} {x['code']})"
        assert len(rows[n - 1]) == len(COLUMNS), f"{where}: wrong number of fields"
        assert x["form"] == "1065", f"{where}: rule 2"
        assert re.fullmatch(r"[0-9a-f]{16}#\d+", x["doc_id"]), f"{where}: rule 3 - doc_id {x['doc_id']!r}"
        if x["box"] in ITEMS:                                             # a Part II item
            assert x["code"] == "" and x["valid_in_ut"] == "", f"{where}: rule 5"
            if x["box"].startswith("K1_"):
                assert re.fullmatch(r"-?\d+\.\d\d", x["amount"]) and float(x["amount"]) != 0, f"{where}: rule 5 - K1 amount"
            if x["entry"]:
                assert x["entry"] == ITEMS[x["box"]], f"{where}: rule 7 - {x['box']} is {ITEMS[x['box']]}"
        else:                                                             # a box line
            assert re.fullmatch(r"\d+[A-Za-z]?", x["box"]), f"{where}: rule 4 - box {x['box']!r}"
            assert x["amount"] == "X" or re.fullmatch(r"-?\d+\.\d\d", x["amount"]), f"{where}: rule 6 - amount {x['amount']!r}"
            if x["code"]:
                assert x["valid_in_ut"] in ("Y", "N"), f"{where}: rule 6 - valid_in_ut"
            else:
                assert x["valid_in_ut"] == "", f"{where}: rule 6 - no code, valid_in_ut blank"
        assert x["entry"] in ("bot", "hand", ""), f"{where}: rule 7"
        if x["entry"] == "hand":
            assert x["entry_reason"], f"{where}: rule 7 - a hand row says why"
        if x["entry"] == "bot":
            assert x["entry_reason"] == "", f"{where}: rule 7 - a bot row has no reason"
        who[x["doc_id"]].add((x["payer_ein"], x["payer_name"], x["recipient_id"]))
    for doc_id, v in who.items():
        assert len(v) == 1, f"rule 8: {doc_id} has different payer / recipient values"
    return out


# ---------------------------------------------------------------- a made-up K-1 (no client data)
def _k(page, **kw):
    lines = [("1", None, 1500.0), ("5", None, 100.0), ("11", "ZZ", -40.0), ("20", "A", 63.0), ("13", "AE", 12.0)]
    k = dict(page=page, form="1065", year=2025, name="DEMO, LP", ein="12-3456789", E="XXX-XX-1234", amended=False,
             G="Limited", H1="Domestic", M="No",
             lines=[dict(box=b, code=c, amt=a, stmt=False, check=False, key=b + (c or "")) for b, c, a in lines], **kw)
    return prep.assign_lids(k)


def test_made_up_k1_export_matches_the_format():
    k = _k(3, K1={"Nonrecourse": [80.0, 67.0], "Qualified nonrecourse financing": [0.0, 0.0], "Recourse": [5.0, 12.5]})
    rows = prep._rows(k, {}, [])
    data = dict(k1s=[dict(ready=True, doc_id="0123456789abcdef#3", ein=k["ein"], name=k["name"], E=k["E"],
                          rows=ut_entry.decide(rows))])
    out = check_export(prep.export_csv(data))
    boxes = [x["box"] for x in out]
    assert "K1_nonrecourse" in boxes and "K1_recourse" in boxes and "K1_qualified" not in boxes    # a 0 is left out
    assert boxes.index("K1_nonrecourse") < boxes.index("1")                                        # items before box lines
    assert any(x["payer_name"] == "DEMO, LP" for x in out)                                         # a comma survives (quoted)


# ---------------------------------------------------------------- the K-1 test samples (local only)
def test_sample_k1s_export_matches_the_format():
    src = h.SAMPLES / "K-1_Sample"
    files = sorted(p for p in src.glob("*") if p.suffix.lower() == ".pdf") if src.is_dir() else []
    if not files:
        pytest.skip("tests\\samples\\K-1_Sample isn't on this computer")
    tok, problems, _ = runs.make_run([(str(p), p.name) for p in files])
    run = runs.RUNS[tok]
    # box E of the samples ends in the same 4 digits: that is the taxpayer, so the K-1s can be Ready
    last4 = collections.Counter(re.sub(r"\D", "", k.get("E") or "")[-4:] for k in run["k1s"]).most_common(1)[0][0]
    data = prep.build(run, {"tp": last4}, runs.file_ids(run))
    out = check_export(prep.export_csv(data))
    assert data["ready"] and out, "no Ready K-1 in the samples - nothing was checked"
    assert {x["doc_id"] for x in out} == {k["doc_id"] for k in data["k1s"] if k["ready"]}       # every Ready K-1, nothing else

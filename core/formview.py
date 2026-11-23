"""formview.py - the form tabs of the Document inventory: W2 = every W-2 side by side, box by box, 6 per tab; 1098-M = every
mortgage 1098 the same way; 1099-R, 1099-SA, 1098-E, SSA-1099, 1098-T, 1095-A one column per form; every
brokerage-style 1099 (composite, INT, DIV, B, OID, DA, MISC, NEC) in one layout, a statement = one column (brief 2026-11-23).

The parsed values are never changed. The preparer's corrections are kept apart in r["formview"][form][<doc id>#<form index>]
= {row key: value}; the effective value = the correction if there is one, else the parsed value. effective_docs() gives the
document list with the corrections applied - everything downstream (income summary, Verify, AI report, Excel) uses it.
Row keys: b1 ... b11 (boxes), ssn / ein / er / er_addr / ctl / ee / ee_addr (boxes a-f), b13stat / b13ret / b13sick, b12:<code>,
b14:<label>, st:<state>:15|16|17 (15 = state ID), lc:<locality>:18|19.
1098 row keys (parse_1098 gives them as they are): b1 ... b9, b11, b10:<description>, ln (lender), br (borrower), acct.
"""
from __future__ import annotations

import re

# Social Security wage base by tax year (SSA)
WAGE_BASE = {2024: 168600, 2025: 176100, 2026: 184500}
SS_RATE = 0.062

W2_12 = {
    "A": "Uncollected social security or RRTA tax on tips",
    "B": "Uncollected Medicare tax on tips",
    "C": "Taxable cost of group-term life insurance over $50,000",
    "D": "Elective deferrals to a section 401(k) cash or deferred arrangement",
    "E": "Elective deferrals under a section 403(b) salary reduction agreement",
    "F": "Elective deferrals under a section 408(k)(6) salary reduction SEP",
    "G": "Elective deferrals and employer contributions to a section 457(b) deferred compensation plan",
    "H": "Elective deferrals to a section 501(c)(18)(D) tax-exempt organization plan",
    "J": "Nontaxable sick pay",
    "K": "20% excise tax on excess golden parachute payments",
    "L": "Substantiated employee business expense reimbursements",
    "M": "Uncollected social security or RRTA tax on taxable cost of group-term life insurance over $50,000 (former employees)",
    "N": "Uncollected Medicare tax on taxable cost of group-term life insurance over $50,000 (former employees)",
    "P": "Excludable moving expense reimbursements paid directly to a member of the U.S. Armed Forces",
    "Q": "Nontaxable combat pay",
    "R": "Employer contributions to an Archer MSA",
    "S": "Employee salary reduction contributions under a section 408(p) SIMPLE plan",
    "T": "Adoption benefits",
    "V": "Income from exercise of nonstatutory stock option(s)",
    "W": "Employer contributions (including employee contributions through a cafeteria plan) to an employee's health savings account (HSA)",
    "Y": "Deferrals under a section 409A nonqualified deferred compensation plan",
    "Z": "Income under a nonqualified deferred compensation plan that fails to satisfy section 409A",
    "AA": "Designated Roth contributions under a section 401(k) plan",
    "BB": "Designated Roth contributions under a section 403(b) plan",
    "DD": "Cost of employer-sponsored health coverage",
    "EE": "Designated Roth contributions under a governmental section 457(b) plan",
    "FF": "Permitted benefits under a qualified small employer health reimbursement arrangement",
    "GG": "Income from qualified equity grants under section 83(i)",
    "HH": "Aggregate deferrals under section 83(i) elections as of the close of the calendar year",
    "II": "Medicaid waiver payments excluded from gross income",
}


def _m(k, box, label):
    return dict(k=k, box=box, label=label, t="money")


# one definition per form: sections of fixed rows, or repeatable groups ("dyn": key prefix) that get one row per key found;
# head=False: no title row (the Box column says it)
DEFS = {
    "w2": dict(label="W-2", sections=[
        dict(title="Boxes 1–20", head=False, rows=[
            _m("b1", "1", "Wages, tips, other compensation"), _m("b2", "2", "Federal income tax withheld"),
            _m("b3", "3", "Social security wages"), _m("b4", "4", "Social security tax withheld"),
            _m("b5", "5", "Medicare wages and tips"), _m("b6", "6", "Medicare tax withheld"),
            _m("b7", "7", "Social security tips"), _m("b8", "8", "Allocated tips"),
            _m("b10", "10", "Dependent care benefits"), _m("b11", "11", "Nonqualified plans")]),
        dict(title="Box 12", head=False, dyn="b12:", box="12", t="money", kind="code12", add="Box 12 code (A … II)",
             none="Box 12 — no codes"),
        dict(title="Box 13", head=False, rows=[dict(k="b13stat", box="13", label="Statutory employee", t="check"),
                                   dict(k="b13ret", box="13", label="Retirement plan", t="check"),
                                   dict(k="b13sick", box="13", label="Third-party sick pay", t="check")]),
        dict(title="Box 14 — Other", head=False, dyn="b14:", box="14", t="money", kind="label", add="Box 14 label",
             none="Box 14 — Other: none"),
        dict(title="State", head=False, dyn="st:", t="money", kind="state", add="State (2 letters)",
             pair={"16": "State wages, tips, etc.", "17": "State income tax"}),
        dict(title="Local", head=False, dyn="lc:", t="money", kind="local", add="Locality name",
             pair={"18": "Local wages, tips, etc.", "19": "Local income tax"}),
    ],
        # column header = person (box e) · first word of the payer (box c); what a change re-calculates; the banners' words
        head=dict(who="ee", payer="er", id="ein", who_miss="Employee name not found on the W-2",
                  payer_miss="Employer name not found on the W-2", payer_lbl="Employer", id_lbl="EIN"),
        feeds=r"^(b1|b2|b12:.*)$", summary="income summary", typed="wages"),
    "1098": dict(label="1098", sections=[
        dict(title="Boxes 1–9", head=False, rows=[
            _m("b1", "1", "Mortgage interest received from payer(s)/borrower(s)"),
            _m("b2", "2", "Outstanding mortgage principal"),
            dict(k="b3", box="3", label="Mortgage origination date", t="text"),
            _m("b4", "4", "Refund of overpaid interest"), _m("b5", "5", "Mortgage insurance premiums"),
            _m("b6", "6", "Points paid on purchase of principal residence"),
            dict(k="b7", box="7", label="Property address same as borrower's address", t="check"),
            dict(k="b8", box="8", label="Address or description of property securing mortgage", t="text"),
            dict(k="b9", box="9", label="Number of properties securing the mortgage", t="text")]),
        dict(title="Box 10 — Other", head=False, dyn="b10:", box="10", t="money", kind="label", add="Box 10 description",
             none="Box 10 — Other: none"),
    ],
        head=dict(who="br", payer="ln", id="acct", who_miss="Borrower name not found on the 1098",
                  payer_miss="Lender name not found on the 1098", payer_lbl="Lender", id_lbl="Account"),
        feeds=r"^(b1|b2|b4|b5|b6|b7|b8|b10:.*)$", summary="deduction summary", typed="mortgage interest"),
}


# ---------------------------------------------------------------- parsed W-2 -> row keys and back
TEXT_KEYS = ("ssn", "ein", "er", "er_addr", "ctl", "ee", "ee_addr")
B13 = (("stat", "b13stat"), ("ret", "b13ret"), ("sick", "b13sick"))


def w2_rows(f: dict) -> dict:
    """One W-2 as parse_w2 gives it ({'1': .., '12': [(code, amt)], 'states': [..], ..}) -> {row key: value}."""
    out = {}
    for k, v in f.items():
        if k == "12":
            for code, a in v or []:
                out[f"b12:{code}"] = round(out.get(f"b12:{code}", 0) + (a or 0), 2)
        elif k == "13":
            out.update({rk: bool(v.get(pk)) for pk, rk in B13})
        elif k == "14":
            for lab, a in v or []:
                out[f"b14:{lab}"] = round(out.get(f"b14:{lab}", 0) + (a or 0), 2)
        elif k == "states":
            for s in v or []:
                g = s.get("st") or "-"
                for b, sk in (("15", "id"), ("16", "w"), ("17", "t")):
                    if s.get(sk) is not None:
                        out[f"st:{g}:{b}"] = s[sk]
        elif k == "locals":
            for s in v or []:
                g = s.get("name") or "-"
                for b, sk in (("18", "w"), ("19", "t")):
                    if s.get(sk) is not None:
                        out[f"lc:{g}:{b}"] = s[sk]
        elif k in ("16", "17"):
            if not f.get("states"):                  # list layout: no state code
                out[f"st:-:{k}"] = v
        elif k in ("18", "19"):
            if not f.get("locals"):
                out[f"lc:-:{k}"] = v
        elif k in TEXT_KEYS:
            out[k] = v
        elif re.fullmatch(r"\d{1,2}", k):
            out["b" + k] = v
    return out


def _back(f: dict, eff: dict) -> dict:
    """Effective row values -> the parse_w2 box dict (what income / Verify read)."""
    g = dict(f)
    for k, v in eff.items():
        m = re.fullmatch(r"b(\d{1,2})", k)
        if m:
            g[m.group(1)] = v
        elif k in TEXT_KEYS:
            g[k] = v
    g["12"] = [(k[4:], v) for k, v in eff.items() if k.startswith("b12:") and v]
    g["14"] = [(k[4:], v) for k, v in eff.items() if k.startswith("b14:") and v]
    if any(rk in eff for _, rk in B13):
        g["13"] = {pk: bool(eff.get(rk)) for pk, rk in B13}
    for pre, name, boxes in (("st", "st", (("15", "id"), ("16", "w"), ("17", "t"))), ("lc", "name", (("18", "w"), ("19", "t")))):
        groups = sorted({k.split(":")[1] for k in eff if k.startswith(pre + ":")})
        rows = [dict({name: None if s == "-" else s}, **{sk: eff.get(f"{pre}:{s}:{b}") for b, sk in boxes}) for s in groups]
        g["states" if pre == "st" else "locals"] = rows
        for b, sk in boxes[-2:]:
            vs = [r[sk] for r in rows if isinstance(r[sk], (int, float))]
            g[b] = round(sum(vs), 2) if vs else None
    return g


def forms_of(d: dict, form: str = "w2") -> list:
    """The forms the program read in one document (detail["boxes"]: one dict per W-2 / 1098)."""
    p = d.get("parsed")
    if d.get("family") != form or d.get("route") in ("skipped", "excluded") or not isinstance(p, dict) or p.get("status") == "none":
        return []
    return (p.get("detail") or {}).get("boxes") or []


def w2_forms(d: dict) -> list:
    return forms_of(d, "w2")


def _w2_redo(d: dict, new: list) -> dict:
    """A W-2 document's parse result again, from its corrected W-2s."""
    p = dict(d["parsed"])
    p["detail"] = dict(p.get("detail") or {}, boxes=new, w2=[(f.get("1") or 0, f.get("2")) for f in new])
    p["amounts"] = dict(p.get("amounts") or {}, w2=round(sum(f.get("1") or 0 for f in new), 2))
    p["fit"] = round(sum(f.get("2") or 0 for f in new), 2)
    p["notes"] = [n for n in p.get("notes") or [] if not n.startswith("Box 12 ")] + \
        [f"Box 12 {c} {v:,.2f}" + (" (employer health coverage — not taxable)" if c == "DD" else "") for f in new for c, v in f.get("12") or []]
    return p


def _m_redo(d: dict, new: list) -> dict:
    """A 1098 document's parse result again (box 1 -> mortgage interest, the comment), from its corrected 1098s."""
    from core.parsers import m1098_result
    return m1098_result([{k: v for k, v in f.items() if v is not None} for f in new])


# ================================================================ the other forms (brief 2026-11-23): one column per form
# Each form type: its definition in DEFS (the rows), an entry in FAMILIES (the columns of a document, and the document's result
# worked out again from corrected columns - by the reader's own result function, so a correction gives the same income
# summary as if the reader had read that value).
def _t(k, box, label, **kw):
    return dict(k=k, box=box, label=label, t="text", **kw)


def _c(k, box, label, **kw):
    return dict(k=k, box=box, label=label, t="check", **kw)


def _o(k, box, label, **kw):
    """A row shown only when a form in the tab has a value on it (opt)."""
    return dict(_m(k, box, label), opt=True, **kw)


DOC_HEAD = dict(doc=True)          # no person / payer names read: the column header = the issuer (or the file name)

DEFS.update({
    "1099r": dict(label="1099-R", sections=[dict(title="1099-R", head=False, rows=[
        _m("b1", "1", "Gross distribution"), _m("b2a", "2a", "Taxable amount"),
        _c("nd", "2b", "Taxable amount not determined"), _c("td", "2b", "Total distribution"),
        _m("b3", "3", "Capital gain (included in box 2a)"), _m("b4", "4", "Federal income tax withheld"),
        _m("b5", "5", "Employee contributions / Designated Roth contributions or insurance premiums"),
        _t("code", "7", "Distribution code(s)"), _c("ira", "7", "IRA/SEP/SIMPLE"),
        _o("b9b", "9b", "Total employee contributions"), _m("b14", "14", "State tax withheld"),
        _m("b16", "16", "State distribution")])],
        head=DOC_HEAD, feeds=".*", summary="income summary", typed="the taxable amount"),
    "1099sa": dict(label="1099-SA", sections=[dict(title="1099-SA", head=False, rows=[
        _m("b1", "1", "Gross distribution"), _m("b2", "2", "Earnings on excess contributions"),
        _t("b3", "3", "Distribution code"), _m("b4", "4", "FMV on date of death"),
        _t("b5", "5", "HSA / Archer MSA / MA MSA")])],
        head=DOC_HEAD, feeds=".*", summary="Document inventory note", typed=""),
    "1098e": dict(label="1098-E", sections=[dict(title="1098-E", head=False, rows=[
        _m("b1", "1", "Student loan interest received by lender"),
        _c("b2", "2", "Box 1 does not include loan origination fees and/or capitalized interest")])],
        head=DOC_HEAD, feeds=".*", summary="deduction summary", typed="student loan interest"),
    "ssa": dict(label="SSA-1099", sections=[dict(title="SSA-1099", head=False, rows=[
        _m("b5", "5", "Net benefits"), _m("b6", "6", "Voluntary federal income tax withheld")])],
        head=DOC_HEAD, feeds=".*", summary="income summary", typed="Social Security"),
    "1098t": dict(label="1098-T", sections=[dict(title="1098-T", head=False, rows=[
        _m("b1", "1", "Payments received for qualified tuition and related expenses"),
        _m("b4", "4", "Adjustments made for a prior year"), _m("b5", "5", "Scholarships or grants"),
        _m("b6", "6", "Adjustments to scholarships or grants for a prior year"),
        _o("b10", "10", "Ins. contract reimb./refund"),
        _c("c7", "7", "Box 1 includes amounts for an academic period beginning January–March of next year"),
        _c("c8", "8", "At least half-time student"), _c("c9", "9", "Graduate student")])],
        head=DOC_HEAD, feeds=".*", summary="Document inventory note", typed=""),
    "1095a": dict(label="1095-A", sections=[dict(title="1095-A", head=False, rows=[
        _m("aptc", "33C", "Annual totals — monthly advance payment of premium tax credit")])],
        head=DOC_HEAD, feeds=".*", summary="Document inventory note", typed=""),
    # every brokerage-style 1099 (composite, 1099-INT / DIV / B / OID / DA, IRS-layout MISC / NEC, bank 1099-INT): one layout,
    # a section shows only when a form in the tab has it (opt); totals, not transactions (Lady, 2026-11-23)
    "1099": dict(label="1099", sections=[
        dict(title="1099-INT", opt=True, rows=[
            _m("int_1", "1", "Interest income"), _o("int_2", "2", "Early withdrawal penalty"),
            _m("int_3", "3", "Interest on U.S. Savings Bonds and Treasury obligations"), _o("int_5", "5", "Investment expenses"),
            _m("int_6", "6", "Foreign tax paid"), _m("int_8", "8", "Tax-exempt interest"),
            _o("int_9", "9", "Specified private activity bond interest"), _o("int_10", "10", "Market discount"),
            _o("int_11", "11", "Bond premium"), _o("int_12", "12", "Bond premium on Treasury obligations"),
            _o("int_13", "13", "Bond premium on tax-exempt bond")]),
        dict(title="1099-OID", opt=True, rows=[_m("oid_1", "1", "Original issue discount")]),
        dict(title="1099-DIV", opt=True, rows=[
            _m("div_1a", "1a", "Total ordinary dividends"), _m("div_1b", "1b", "Qualified dividends"),
            _m("div_2a", "2a", "Total capital gain distributions"), _m("div_3", "3", "Nondividend distributions"),
            _o("div_5", "5", "Section 199A dividends"), _m("div_7", "7", "Foreign tax paid"),
            _m("div_12", "12", "Exempt-interest dividends")]),
        dict(title="1099-MISC", opt=True, rows=[
            _o("misc_1", "1", "Rents"), _m("misc_2", "2", "Royalties"), _m("misc_3", "3", "Other income"),
            _o("misc_5", "5", "Fishing boat proceeds"), _o("misc_6", "6", "Medical and health care payments"),
            _m("misc_8", "8", "Substitute payments in lieu of dividends or interest"),
            _o("misc_9", "9", "Crop insurance proceeds"), _o("misc_10", "10", "Gross proceeds paid to an attorney"),
            _o("misc_11", "11", "Fish purchased for resale"), _o("misc_12", "12", "Section 409A deferrals"),
            _o("misc_15", "15", "Nonqualified deferred compensation"), _o("misc_16", "16", "State tax withheld"),
            _o("misc_18", "18", "State income")]),
        dict(title="1099-NEC", opt=True, rows=[
            _o("nec_1a", "1a", "Nonemployee compensation"), _o("nec_1", "1", "Nonemployee compensation"),
            _o("nec_1b", "1b", "Cash tips"), _o("nec_1d", "1d", "Overtime compensation"),
            _o("nec_3", "3", "Excess golden parachute payments"), _o("nec_5", "5", "State tax withheld"),
            _o("nec_7", "7", "State income")]),
        # a term's five rows show together (grp); its gain is the sum of its Form 8949 box rows when it has them (sumof)
        dict(title="1099-B totals", opt=True, rows=[
            _o(f"b:{t}:{f}", tb, f"{tl} — {fl}", grp=t, **({"sumof": f"b8949:{t}:"} if f == "gain" else {}))
            for t, tb, tl in (("st", "ST", "Short-term"), ("lt", "LT", "Long-term"), ("und", "?", "Term unknown"))
            for f, fl in (("proceeds", "Proceeds"), ("cost", "Cost or other basis"), ("md", "Accrued market discount"),
                          ("wash", "Wash sale loss disallowed"), ("gain", "Gain or (loss)"))]),
        dict(title="1099-B by Form 8949 box", opt=True, dyn="b8949:", t="money", kind="b8949", hide_none=True),
        dict(title="§1256 contracts (Form 6781)", opt=True, rows=[
            _m("s1256_11", "11", "Aggregate profit or (loss) on contracts")]),
        dict(title="Withholding", rows=[_m("fit", "4", "Federal income tax withheld")]),
    ], head=DOC_HEAD, feeds=".*", summary="income summary", typed="amounts"),
})


# ---------------------------------------------------------------- simple forms: the reader's form <-> row keys
def _map_rows(f: dict, names: dict) -> dict:
    """A form as the reader keeps it -> row keys (names: reader key -> row key; keys not listed are left out)."""
    return {rk: f[k] for k, rk in names.items() if k in f}


def _map_back(f: dict, eff: dict, names: dict) -> dict:
    """Row values -> the reader's form again (a blank box is left out, as the reader leaves out what it didn't read)."""
    g = {k: v for k, v in f.items() if k not in names}
    for k, rk in names.items():
        v = eff.get(rk)
        if v is not None and v != "":
            g[k] = v
    return g


R_NAMES = {"1": "b1", "2a": "b2a", "3": "b3", "4": "b4", "5": "b5", "9b": "b9b", "14": "b14", "16": "b16",
           "code": "code", "ira": "ira", "not_determined": "nd", "total_dist": "td"}
MISC_NAMES = {b: ("fit" if b == "4" else "misc_" + b) for b in ("1", "2", "3", "4", "5", "6", "8", "9", "10", "11", "12", "15", "16", "18")}
NEC_NAMES = {b: ("fit" if b == "4" else "nec_" + b) for b in ("1a", "1", "1b", "1d", "3", "4", "5", "7")}
E_NAMES = {"1": "b1", "2": "b2"}
SSA_NAMES = {"5": "b5", "6": "b6"}
T_NAMES = {"1": "b1", "4": "b4", "5": "b5", "6": "b6", "10": "b10"}
SA_MONEY, SA_TEXT = ("1", "2", "4"), ("3", "5")


def _sa_rows(f: dict) -> dict:
    """1099-SA: the reader keeps the values as printed (text) - amounts become numbers for the tab."""
    from core.parsers import _lnum
    out = {"b" + b: _lnum(f.get(b)) for b in SA_MONEY if f.get(b) not in (None, "")}
    out.update({"b" + b: f[b] for b in SA_TEXT if f.get(b)})
    return out


def _sa_back(f: dict, eff: dict) -> dict:
    g = {k: v for k, v in f.items() if k not in SA_MONEY + SA_TEXT}
    for b in SA_MONEY:
        if eff.get("b" + b) is not None:
            g[b] = f"{eff['b' + b]:.2f}"
    for b in SA_TEXT:
        if eff.get("b" + b):
            g[b] = eff["b" + b]
    return g


def _t_rows(f: dict) -> dict:
    out = _map_rows(f, T_NAMES)
    out.update({"c" + c: c in (f.get("checks") or []) for c in ("7", "8", "9")})
    return out


def _t_back(f: dict, eff: dict) -> dict:
    g = _map_back({}, eff, T_NAMES)
    g["checks"] = [c for c in ("7", "8", "9") if eff.get("c" + c)]
    return g


# ---------------------------------------------------------------- brokerage statements: the whole statement = one column
TERMS = ("st", "lt", "und")
B_FIELDS = ("proceeds", "cost", "md", "wash", "gain")
FORM_KEY = re.compile(r"^(int|div|misc|oid|nec|s1256)_\w+$")


def _stmt_rows(p: dict) -> dict:
    """A brokerage statement's result (parse_1099 / parse_box_rows / parse_box_list) -> row keys: the form boxes (int_1,
    div_1a ...), the withholding (fit), the 1099-B totals by term (b:st:gain ...) and the Form 8949 box rows (b8949:st:A)."""
    det = p.get("detail") or {}
    out = {k: v for k, v in det.items() if FORM_KEY.match(k)}
    out["fit"] = p.get("fit") or 0
    for t in TERMS:
        for fld, v in (det.get("b_" + t) or {}).items():
            out[f"b:{t}:{fld}"] = v
    for t, rows in ((p.get("redo_inputs") or {}).get("boxes") or {}).items():
        for bx, g, _ in rows:
            out[f"b8949:{t}:{bx}"] = g
    return out


def _stmt_redo(d: dict, effs: list) -> dict:
    """The statement worked out again from its corrected column (parsers.statement_again). A term's gain = the sum of its
    Form 8949 box rows when it has them (the box rows are what the preparer corrects), so the rows always add up."""
    from core.parsers import statement_again
    p = d["parsed"]
    eff = effs[0]
    if eff is None:
        return p
    f = {k: v for k, v in eff.items() if FORM_KEY.match(k) and v is not None}
    old_boxes = (p.get("redo_inputs") or {}).get("boxes") or {}
    boxes, b = {}, {}
    for t in TERMS:
        rows = [(bx, eff.get(f"b8949:{t}:{bx}") or 0, pr) for bx, _, pr in old_boxes.get(t) or []]
        if rows:
            boxes[t] = rows
        vals = {fld: eff.get(f"b:{t}:{fld}") for fld in B_FIELDS}
        if any(v is not None for v in vals.values()):
            r = {fld: v or 0 for fld, v in vals.items()}
            if rows:
                r["gain"] = round(sum(g for _, g, _ in rows), 2)
            b[t] = r
    return statement_again(p, f, b, eff.get("fit") or 0, boxes or None)


# ---------------------------------------------------------------- the forms of a document, and its result again
def _per_form(d: dict) -> list:
    p = d["parsed"]
    return (p.get("detail") or {}).get("forms") or [] if p.get("reader") == "1099sa" else p.get("per_form") or []


def _redo_simple(d: dict, effs: list, back) -> list:
    """The document's forms with the corrected ones put back into the reader's shape (an unchanged form stays as read)."""
    return [f if e is None else back(f, e) for f, e in zip(_per_form(d), effs)]


def _more(p: dict) -> bool:
    """The first read said "This file seems to hold more than one <form>" - kept after a correction."""
    return "more than one" in (p.get("inv_note") or "") + " ".join(p.get("notes") or [])


def _cols_1099(d: dict) -> list:
    p = d["parsed"]
    how = p.get("reader") or ""
    if how == "1099_statement":
        return [_stmt_rows(p)]
    if how.startswith("1099_form:"):
        names = MISC_NAMES if how.endswith("misc") else NEC_NAMES
        return [_map_rows(f, names) for f in p.get("per_form") or []]
    if how == "1099int_rows":
        return [dict(f) for f in p.get("per_form") or []]
    return []


def _redo_1099(d: dict, effs: list) -> dict:
    from core import parsers as P
    p = d["parsed"]
    how = p.get("reader") or ""
    if how == "1099_statement":
        return _stmt_redo(d, effs)
    if how.startswith("1099_form:"):
        kind = how.split(":")[1]
        names = MISC_NAMES if kind == "misc" else NEC_NAMES
        return P.form_1099_result(_redo_simple(d, effs, lambda f, e: _map_back({}, e, names)), kind, p.get("page"))
    if how == "1099int_rows":
        return P.int_rows_result(_redo_simple(d, effs, lambda f, e: {k: v for k, v in e.items() if v is not None}), p.get("page"))
    return p


def _redo_r(d, effs):
    from core.parsers import r1099_result
    return r1099_result(_redo_simple(d, effs, lambda f, e: _map_back({}, e, R_NAMES)), d["parsed"].get("page"))


def _redo_sa(d, effs):
    from core.parsers import sa_result
    return sa_result(_redo_simple(d, effs, _sa_back))


def _redo_e(d, effs):
    from core.parsers import e1098_result
    return e1098_result(_redo_simple(d, effs, lambda f, e: _map_back({}, e, E_NAMES)), d["parsed"].get("page"))


def _redo_ssa(d, effs):
    from core.parsers import ssa_result
    f = _redo_simple(d, effs, lambda f, e: _map_back({}, e, SSA_NAMES))[0]
    return ssa_result(f.get("5") or 0, f.get("6") or 0, d["parsed"].get("page"), _more(d["parsed"]))


def _redo_t(d, effs):
    from core.parsers import t1098_result
    f = _redo_simple(d, effs, _t_back)[0]
    return t1098_result({k: v for k, v in f.items() if k != "checks"}, f.get("checks") or [], _more(d["parsed"]))


def _redo_a(d, effs):
    from core.parsers import a1095_result
    f = _redo_simple(d, effs, lambda f, e: _map_back({}, e, {"aptc": "aptc"}))[0]
    return a1095_result(f.get("aptc") or 0, _more(d["parsed"]))


def _w2_redo_all(d, effs):
    return _w2_redo(d, [f if e is None else _back(f, e) for f, e in zip(forms_of(d, "w2"), effs)])


def _m_redo_all(d, effs):
    return _m_redo(d, [f if e is None else dict(e) for f, e in zip(forms_of(d, "1098"), effs)])


# family (the document type) -> its definition (DEFS), the columns of one document (row-key dicts, one per form) and the
# document's result again from the columns (effs[i] = the corrected column i, None = not corrected)
SPEC_1099 = dict(defn="1099", cols=_cols_1099, redo=_redo_1099)
FAMILIES = {
    "w2": dict(defn="w2", cols=lambda d: [w2_rows(f) for f in forms_of(d, "w2")], redo=_w2_redo_all),
    "1098": dict(defn="1098", cols=lambda d: [dict(f) for f in forms_of(d, "1098")], redo=_m_redo_all),
    "1099r": dict(defn="1099r", cols=lambda d: [_map_rows(f, R_NAMES) for f in _per_form(d)], redo=_redo_r),
    "1099sa": dict(defn="1099sa", cols=lambda d: [_sa_rows(f) for f in _per_form(d)], redo=_redo_sa),
    "1098e": dict(defn="1098e", cols=lambda d: [_map_rows(f, E_NAMES) for f in _per_form(d)], redo=_redo_e),
    "ssa": dict(defn="ssa", cols=lambda d: [_map_rows(f, SSA_NAMES) for f in _per_form(d)], redo=_redo_ssa),
    "1098t": dict(defn="1098t", cols=lambda d: [_t_rows(f) for f in _per_form(d)], redo=_redo_t),
    "1095a": dict(defn="1095a", cols=lambda d: [{"aptc": f.get("aptc")} for f in _per_form(d)], redo=_redo_a),
    **{fam: SPEC_1099 for fam in ("composite", "1099b", "1099da", "1099div", "1099oid", "1099int", "1099misc", "1099nec")},
}


def _usable(d: dict) -> bool:
    """A document the program read (its forms can be shown): not skipped / excluded, a result with something read."""
    p = d.get("parsed")
    return d.get("route") not in ("skipped", "excluded") and isinstance(p, dict) and p.get("status") not in (None, "none")


def doc_columns(d: dict) -> list:
    """The columns (row-key dicts, one per form) of one document - [] when it has none."""
    spec = FAMILIES.get(d.get("family"))
    return spec["cols"](d) if spec and _usable(d) else []


def effective(parsed: dict, edits: dict) -> dict:
    out = dict(parsed)
    out.update(edits or {})
    return out


def effective_docs(r: dict) -> list:
    """The document list with the form-view corrections applied (parsed values untouched in r): a corrected document's
    result is worked out again by the reader's own result function (FAMILIES redo)."""
    docs = r["inv"]["docs"]
    fvs = r.get("formview") or {}
    if not any(fvs.get(f) for f in FAMILIES):
        return docs
    out = []
    for d in docs:
        fam = d.get("family")
        fv = (fvs.get(fam) or {}) if fam in FAMILIES else {}
        cols = doc_columns(d) if fv else []
        if not cols or not any(fv.get(f'{d["did"]}#{i}') for i in range(len(cols))):
            out.append(d)
            continue
        effs = [effective(c, fv[f'{d["did"]}#{i}']) if fv.get(f'{d["did"]}#{i}') else None for i, c in enumerate(cols)]
        p = dict(FAMILIES[fam]["redo"](d, effs))
        p["formview_edited"] = True
        out.append(dict(d, parsed=p))
    return out


# ---------------------------------------------------------------- page data (the Form view section of the summary page)
PER_TAB = 6                                     # forms per tab: W2 = 1-6, W2_2 = 7-12 ... (always 6 columns + Total)
# the Document inventory's tabs after "Summary": W2 first, then these always (alphabetical; "(n)" = forms of that type)
TABS = [("1098", "1098-M"), ("1098t", "1098-T"), ("1099b", "1099-B"), ("composite", "1099-Comp"), ("1099da", "1099-DA"),
        ("1099div", "1099-DIV"), ("1099g", "1099-G"), ("1099int", "1099-INT"), ("1099nec", "1099-NEC"), ("1099r", "1099-R")]
# ... and these only when the client has one (they take their place in the alphabetical order)
TABS_IF = [("1099k", "1099-K"), ("1099misc", "1099-MISC"), ("1099oid", "1099-OID"), ("1099sa", "1099-SA"), ("ssa", "SSA-1099"),
           ("1098e", "1098-E"), ("1095a", "1095-A"), ("5498", "5498")]
# 1099-G, 1099-K, 5498: the program has no reader for them - their tabs list the documents (open the document) only


def columns(r: dict, order: list, form: str = "w2") -> list:
    """Every form of that type the program read, one column each, in the inventory's order: {id, form, defn, path, file, num,
    issuer, of, parsed}. The header (person · payer, or the issuer) is made on the page, so a correction there shows at once."""
    rank = {p: i for i, p in enumerate(order)}
    cols = []
    for d in sorted(r["inv"]["docs"], key=lambda d: rank.get(d.get("did"), len(rank))):
        if d.get("family") != form:
            continue
        forms = doc_columns(d)
        m = re.match(r"^\s*(\d+)", d["file"])
        n = m.group(1) if m else str(rank.get(d.get("did"), len(rank)) + 1)
        for i, f in enumerate(forms):
            cols.append(dict(id=f'{d["did"]}#{i}', form=form, defn=FAMILIES[form]["defn"], path=d["path"], file=d["file"],
                             num="#" + n + (chr(97 + i) if len(forms) > 1 else ""), issuer=d.get("issuer") or "",
                             of=len(forms), parsed=f))
    return cols


def w2_columns(r: dict, order: list) -> list:
    return columns(r, order, "w2")


def _why_no_column(d: dict) -> str:
    """Why a document of this type has no column on its tab."""
    p = d.get("parsed")
    if d.get("route") == "excluded":
        return "Excluded — " + (d.get("note") or "left out on purpose")
    if d.get("family") not in FAMILIES or p is None:
        return "Not read by the program (no reader for this form yet) — AI review"
    if not isinstance(p, dict) or p.get("status") == "none":
        return "Not read by the program — " + ("; ".join(p.get("checks") or []) if isinstance(p, dict) else "") + " — AI review"
    return "Read, but no form to show"


def tabs(r: dict, cols: list) -> list:
    """The Document inventory's form tabs (after "Summary"): W2 first, then the form types in alphabetical order. A form type
    with a reader gets 6 forms per tab (W2, W2_2 ... / 1099-R, 1099-R_2 ...); n = how many forms (documents for a type the
    program can't read); others = the documents of that type with no column (not read, excluded), listed under the table."""
    docs = [d for d in r["inv"]["docs"] if d.get("route") != "skipped"]

    def others(fam):
        have = {c["id"].rpartition("#")[0] for c in cols if c["form"] == fam}
        return [dict(file=d["file"], path=d["path"], why=_why_no_column(d)) for d in docs
                if d.get("family") == fam and d.get("did") not in have]

    def chunks(form, label):
        fc = [c for c in cols if c.get("form", "w2") == form]
        oth = others(form)
        out = []
        for k in range(0, max(len(fc), 1), PER_TAB):
            j = k // PER_TAB
            out.append(dict(key=form if j == 0 else f"{form}_{j + 1}", label=label if j == 0 else f"{label}_{j + 1}", form=form,
                            defn=FAMILIES[form]["defn"], cols=[c["id"] for c in fc[k:k + PER_TAB]], n=len(fc[k:k + PER_TAB]),
                            others=oth if j == 0 else []))
        return out
    out = chunks("w2", "W2")
    rest = TABS + [t for t in TABS_IF if any(d.get("family") == t[0] for d in docs)]
    for fam, label in sorted(rest, key=lambda t: t[1].lower()):
        if fam in FAMILIES:
            out += chunks(fam, label)
        else:
            oth = others(fam)
            out.append(dict(key=fam, label=label, form=fam, defn=None, cols=[], n=len(oth), others=oth))
    return out

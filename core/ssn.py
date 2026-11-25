"""ssn.py - the recipient's SSN (last 4 only) on every document (Lady, 2026-11-23).

One shared search (last4s), fed only with text already read - no page is read again for it (Lady, 2026-11-23): the pages
each reader took its amounts from (its form / summary pages), else the first 3 pages the document scan read; a W-2 uses its
box a (core/runcheck.py read_ssns). It finds an SSN printed as 123-45-6789, XXX-XX-6789 or
***-**-6789 (spaces allowed around the dashes). Only the last 4 digits are kept, shown as ***-**-6789 even when the whole
number is printed. An EIN (12-3456789) has another shape and is never matched. Several different ones in one file: all of
them, in the order found. The name next to it comes from the prior-year return: the taxpayer's / spouse's last 4 (just to
show the name - comparing them as a check comes later).
"""
from __future__ import annotations

import re

# 3 digits / XXX / *** - 2 digits / XX / ** - 4 digits; not inside a longer number or word (so never part of an account number)
SSN_RX = re.compile(r"(?<![\w*-])(?:\d{3}|[Xx]{3}|\*{3})\s*-\s*(?:\d{2}|[Xx]{2}|\*{2})\s*-\s*(\d{4})(?![\w-])")


def last4s(texts) -> list[str]:
    """Every SSN's last 4 in the texts, each once, in the order found."""
    out = []
    for t in texts:
        for m in SSN_RX.finditer(t or ""):
            if m.group(1) not in out:
                out.append(m.group(1))
    return out


def shown(last4: str, names: dict | None = None) -> str:
    """***-**-1234, with the person's name when the last 4 are the taxpayer's / spouse's on the prior-year return."""
    name = (names or {}).get(last4)
    return f"***-**-{last4}" + (f" · {name}" if name else "")


def names_from_return(people: list) -> dict:
    """The prior-year return's taxpayer / spouse (core.people.read_people): {last 4 of the SSN: "First Last"}."""
    out = {}
    for p in people or []:
        if p.get("role") not in ("Taxpayer", "Spouse"):
            continue
        digits = re.sub(r"\D", "", p.get("ssn") or "")
        name = " ".join(x for x in (p.get("first"), p.get("last")) if x).strip()
        if len(digits) >= 4 and name:
            out.setdefault(digits[-4:], name.title() if name.isupper() else name)
    return out

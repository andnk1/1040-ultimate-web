"""verify.py - page 2 · Verify return. Not converted yet (design/conversion_plan.md, step 4)."""
from __future__ import annotations

from . import get_run, not_yet


def show(token: str):
    get_run(token)
    return not_yet(token, "verify", "Verify return",
                   "Verify return (the UltraTax input screens and the finished return against the documents) comes with its "
                   "own step of the conversion plan.")

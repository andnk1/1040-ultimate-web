"""k1.py - the K-1 section's pages (K-1 Verification, Interpreter, entry check, K-1 UT). Not converted yet
(design/conversion_plan.md, pages 6-8). In the browser app they will open inside the app with ← Back to Summary."""
from __future__ import annotations

from urllib.parse import parse_qs

from . import RUNS, not_yet


def home(query: str = ""):
    owner = (parse_qs(query).get("for") or [""])[0]
    token = owner if owner in RUNS else ""
    return not_yet(token, "summary", "K-1 Verification",
                   "The K-1 pages (K-1 Verification, K-1 Interpreter, K-1 entry check, K-1 UT) come with their own steps of "
                   "the conversion plan. The K-1s are already read by Run check: the Document inventory lists them.")

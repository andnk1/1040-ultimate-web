"""ai.py - the three AI step tabs: 3 · AI Doc Review, 4 · AI Return Review, 5 · AI Advisory.

4 and 5 are description pages (nothing behind them yet) - the same text as the desktop app's.
3 (AI Doc Review) sends documents to Claude: in the browser app it waits until Lady decides how the API key is held
(rule: no API key in the web files - a Cloudflare Worker or a key each user enters).
"""
from __future__ import annotations

from . import get_run, not_yet, page, render

AI_PAGES = {
    "aireturn": dict(title="AI Return Review", what=[
        "The AI reviews the finished return for what the numbers can't show: Karbon answers vs the return, Client Summary items, "
        "prior year → current year (forms filed, payers, carryovers, filing status, dependents), and missed deductions and "
        "credits. It does not check amounts — Verify return (UT verification) does that."], how=[
        "Finish Verify return first.",
        "Run the review. Each finding shows: area, what was found, evidence (Karbon question or return page), action (20 words or "
        "less), severity.",
        "Tick a finding when it's handled; dismiss it with a comment when it doesn't apply.",
        "Findings that are wrong again and again → add a rule to the review instructions (.md)."]),
    "advisory": dict(title="AI Advisory", what=[
        "Planning ideas for the client, following a set of advisory instructions (to be written). Coming later."], how=[]),
}


def _ai_page(token: str, key: str):
    get_run(token)                                   # (the run must be open, as on the desktop)
    return page(render("ai_page.html", token=token, page=dict(AI_PAGES[key], key=key)))


def return_review(token: str):
    return _ai_page(token, "aireturn")


def advisory(token: str):
    return _ai_page(token, "advisory")


def doc_review(token: str):
    get_run(token)
    return not_yet(token, "ai", "AI Doc Review",
                   "Sending documents to Claude waits for one decision: how the API key is held. The rule is no API key in "
                   "the web files — either a Cloudflare Worker holds it, or each user enters their own key. "
                   "Lady decides before it is built.")

"""documents.py - opening a source document from the app (new in the browser app; the desktop had no "open" link).

Rule (Lady, 2026-11-17): PDFs open in a Chrome tab; other files use Google Drive links (how the Drive link is made is still
to decide - design/conversion_plan.md, question 1). The PDF is the copy already in this tab's memory - nothing is uploaded.
"""
from __future__ import annotations

from pathlib import Path

from . import NotFound, file


def open_document(path: str):
    """A PDF on the in-memory drive (a picked document, or one account of a split package) -> shown in a new tab."""
    p = Path(path)
    if p.suffix.lower() != ".pdf":
        raise NotFound(f"Only PDFs open from the app for now ({p.name}).")
    if not (p.is_file() and (str(p).startswith("/client/") or str(p).startswith("/work/"))):   # only the client's files
        raise NotFound(f"{p.name} isn't open in this run any more.")
    return file(p.read_bytes(), p.name, "application/pdf", inline=True)

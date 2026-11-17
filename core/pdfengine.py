"""pdfengine.py - the one PDF door: every use of the PDF engine in core\\ goes through this module.

In the browser (Pyodide): web\\py\\pymupdf_js.py, a stand-in built on MuPDF.js with the same names - PyMuPDF has no
browser version. On this computer's Python (the tests, tools\\web_check): the real PyMuPDF, so the tests can check the same
engine fast. Both give the same text and words (proven page by page: tools\\web_check\\compare_pdf.bat).
The rest of core\\ never writes "import pymupdf"; it writes

    from . import pdfengine
    doc = pdfengine.open(path)

What the engine's readers use - the list the browser stand-in has to cover:
  open(path) / open("pdf", bytes) / open() (a new, empty PDF)
  doc:   needs_pass, authenticate(pw), metadata["producer"], len(doc), doc[i], for page in doc, page_count,
         with doc: / close(), select(pages), insert_pdf(doc, from_page=, to_page=), save(path), tobytes(...)
  page:  rect.width, get_text(), get_text("words"), get_text("blocks", sort=True), get_text("dict"[, clip=rect]),
         get_drawings() (fill colour + rect), insert_text(...)
  the by-hand list PDF (k1v\\ut_entry.py): Story, DocumentWriter, paper_rect, get_text_length
"""
from __future__ import annotations

import sys

if sys.platform == "emscripten":          # in the browser tab (Pyodide)
    import pymupdf_js as _engine          # the MuPDF.js stand-in (web/py/pymupdf_js.py)
else:                                     # this computer's Python: the tests and the check tools
    import pymupdf as _engine

NAME = _engine.__name__
open = _engine.open                       # noqa: A001 - same name as PyMuPDF's, on purpose


def __getattr__(name):                    # Story, DocumentWriter, paper_rect, get_text_length ... - looked up when used
    return getattr(_engine, name)

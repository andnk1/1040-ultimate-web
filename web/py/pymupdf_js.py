"""pymupdf_js.py - the browser version's stand-in for PyMuPDF (which has no browser version), on MuPDF.js.

core\\pdfengine.py loads this module in the browser instead of PyMuPDF. It covers what the engine's readers use (the list in
pdfengine.py's header) with the same names and the same results; the work is done by MuPDF.js through web\\mupdf_bridge.mjs
(registered by the page as the JavaScript module "mupdf_bridge").

Not covered (not needed by the browser version yet): Story / DocumentWriter (the by-hand list PDF), insert_text, redaction.
"""
from __future__ import annotations

import builtins
import json

import mupdf_bridge as _js                     # web/mupdf_bridge.mjs
from pyodide.ffi import to_js

__version__ = "MuPDF.js stand-in"


class Rect:
    def __init__(self, *a):
        if len(a) == 1:
            a = tuple(a[0])
        self.x0, self.y0, self.x1, self.y1 = (float(v) for v in a)

    width = property(lambda s: s.x1 - s.x0)
    height = property(lambda s: s.y1 - s.y0)

    def __iter__(self):
        return iter((self.x0, self.y0, self.x1, self.y1))

    def __getitem__(self, i):
        return (self.x0, self.y0, self.x1, self.y1)[i]

    def __len__(self):
        return 4

    def __repr__(self):
        return f"Rect({self.x0}, {self.y0}, {self.x1}, {self.y1})"

    def contains(self, p) -> bool:
        p = tuple(p)
        if len(p) == 4:
            return self.x0 <= p[0] <= p[2] <= self.x1 and self.y0 <= p[1] <= p[3] <= self.y1
        return self.x0 <= p[0] <= self.x1 and self.y0 <= p[1] <= self.y1


class Page:
    def __init__(self, doc, number: int):
        self.parent, self.number, self._data = doc, number, None

    def _page(self) -> dict:
        if self._data is None:                 # one call to MuPDF.js per page: size, text and words together
            self._data = json.loads(_js.page(self.parent._id, self.number))
        return self._data

    @property
    def rect(self) -> Rect:
        d = self._page()
        return Rect(0, 0, d["w"], d["h"])

    def _dict(self, clip=None) -> dict:
        c = to_js([float(v) for v in clip]) if clip is not None else None
        blocks = json.loads(_js.dict(self.parent._id, self.number, c))
        for b in blocks:
            b["bbox"] = tuple(b["bbox"])
            for l in b["lines"]:
                l["bbox"] = tuple(l["bbox"])
                for s in l["spans"]:
                    s["bbox"] = tuple(s["bbox"])
        d = self._page()
        return dict(width=d["w"], height=d["h"], blocks=blocks)

    def get_text(self, option: str = "text", clip=None, sort: bool = False, **_kw):
        if option == "text" and clip is None:
            return self._page()["text"]
        if option == "words" and clip is None:
            words = [tuple(w) for w in self._page()["words"]]
            return sorted(words, key=lambda w: (w[3], w[0])) if sort else words
        if option == "dict":
            return self._dict(clip)
        if option == "blocks" and clip is None:
            out = [(*b[:5], b[5], 0) for b in json.loads(_js.blocks(self.parent._id, self.number))]
            return sorted(out, key=lambda b: (b[3], b[0])) if sort else out
        raise NotImplementedError(f'get_text("{option}") with these settings is not in the browser version yet')

    def get_drawings(self) -> list:
        return [dict(fill=tuple(d["fill"]), rect=Rect(d["rect"]), type="f") for d in json.loads(_js.drawings(self.parent._id, self.number))]


class Document:
    def __init__(self, data: bytes | None = None, name: str = ""):
        self.name = name
        self._id = _js.open(to_js(data) if data is not None else None)
        self._pages = {}

    # ---- password
    @property
    def needs_pass(self) -> bool:
        return bool(_js.needsPass(self._id))

    def authenticate(self, password: str) -> int:
        return int(_js.authenticate(self._id, str(password)))

    # ---- pages
    @property
    def page_count(self) -> int:
        return int(_js.pageCount(self._id))

    def __len__(self) -> int:
        return self.page_count

    def __getitem__(self, i: int) -> Page:
        n = self.page_count
        if i < 0:
            i += n
        if not 0 <= i < n:
            raise IndexError("page not in document")
        if i not in self._pages:
            self._pages[i] = Page(self, i)
        return self._pages[i]

    load_page = __getitem__

    def __iter__(self):
        return (self[i] for i in range(self.page_count))

    @property
    def metadata(self) -> dict:
        keys = dict(format="format", title="info:Title", author="info:Author", subject="info:Subject", keywords="info:Keywords",
                    creator="info:Creator", producer="info:Producer", creationDate="info:CreationDate", modDate="info:ModDate")
        return {k: str(_js.meta(self._id, v) or "") for k, v in keys.items()}

    # ---- closing
    def close(self) -> None:
        if self._id is not None:
            _js.close(self._id)
            self._id = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @property
    def is_closed(self) -> bool:
        return self._id is None

    # ---- changing / saving (splitting a brokerage package, the AI pages of a long PDF)
    def insert_pdf(self, src: "Document", from_page: int = 0, to_page: int = -1, **_kw) -> None:
        if to_page < 0:
            to_page = src.page_count - 1
        _js.insertPages(self._id, src._id, int(from_page), int(to_page))
        self._pages = {}

    def select(self, pages) -> None:
        _js.select(self._id, to_js([int(p) for p in pages]))
        self._pages = {}

    def tobytes(self, garbage: int = 0, deflate: bool = False, **_kw) -> bytes:
        opts = ["decrypt"] + ([f"garbage={garbage}"] if garbage else []) + (["compress"] if deflate else [])
        return bytes(_js.save(self._id, ",".join(opts)).to_py())

    def save(self, path, **kw) -> None:
        with builtins.open(str(path), "wb") as f:
            f.write(self.tobytes(**kw))


def open(filename=None, stream=None, filetype=None, **_kw) -> Document:   # noqa: A001 - PyMuPDF's name
    """open(path) / open("pdf", bytes) / open(stream=bytes, filetype="pdf") / open() = a new, empty PDF."""
    if filename is None and stream is None:
        return Document()
    if stream is None and isinstance(filename, (bytes, bytearray, memoryview)):
        filename, stream = None, filename
    if stream is not None:
        return Document(bytes(stream))
    with builtins.open(str(filename), "rb") as f:
        return Document(f.read(), str(filename))


def __getattr__(name):
    raise AttributeError(f"pymupdf.{name} is not in the browser version yet (web\\py\\pymupdf_js.py)")

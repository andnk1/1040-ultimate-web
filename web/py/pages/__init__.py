"""pages - the Python behind each page of the browser app (one file per page).

On the desktop, every click on a page went to a Python server at an address (/summary/<run>, /edits/<run> ...). In the browser
the Python runs inside the tab: the page frame hands each address to the worker, web/py/routes.py looks it up in its table, and
the function named there answers. The functions here are those answers.

What every page function gets and gives back:
    gets   the parts of the address (e.g. the run's token) and, for a save, the data the page sent
    gives  one of the replies below - a page (HTML), data (JSON for the page's script), or a file (a download / a new tab)

This file holds what all pages share: the runs kept while the app is open, the template drawing, and the reply kinds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

APP = Path(__file__).resolve().parents[3]            # the app folder on the in-memory drive (core, templates ...)
RUNS: dict = {}                                       # token -> the run (everything Run check read + the preparer's work)


# ---------------------------------------------------------------- replies
@dataclass
class Reply:
    """What a page function answers. kind = "html" (a page to show), "json" (data for the page's script) or "file"."""
    kind: str
    body: object = ""
    status: int = 200
    filename: str = ""                                # a file: its name
    mime: str = ""                                    # a file: its type (application/pdf ...)
    inline: bool = False                              # a file: open it in a new tab instead of downloading it
    note: str = ""                                    # a short message the app shows (e.g. "not saved yet")
    extra: dict = field(default_factory=dict)


def page(html: str, status: int = 200) -> Reply:
    return Reply("html", html, status)


def data(obj, note: str = "") -> Reply:
    return Reply("json", obj, note=note)


def file(content: bytes, filename: str, mime: str, inline: bool = False) -> Reply:
    return Reply("file", content, filename=filename, mime=mime, inline=inline)


class NotFound(Exception):
    """An address the app can't answer (a run that isn't open any more, a file that isn't there)."""


def get_run(token: str) -> dict:
    """The run with this token. A run lives only while the tab is open (nothing is saved yet)."""
    r = RUNS.get(token)
    if r is None:
        raise NotFound("This run isn't open any more (the page was reloaded). Go back and click Run check again.")
    return r


# ---------------------------------------------------------------- drawing the templates (templates/*.html, Jinja2)
def _url_for(endpoint: str, filename: str = "", **_kw) -> str:
    """The templates were written for the desktop's Flask; they only use url_for('static', filename=...)."""
    return "/static/" + filename if endpoint == "static" else "/" + endpoint


def _ai_tab_name() -> str:
    try:
        from core.ai import settings
        return settings.tab_name()
    except Exception:  # noqa: BLE001 - the AI settings file missing must never stop a page
        return "AI Doc Review"


_ENV = None


def render(template: str, **context) -> str:
    global _ENV
    if _ENV is None:
        _ENV = Environment(loader=FileSystemLoader(str(APP / "templates")), autoescape=select_autoescape(["html", "htm", "xml"]))
        _ENV.globals.update(url_for=_url_for, AI_TAB_NAME=_ai_tab_name())
    return _ENV.get_template(template).render(**context)


# ---------------------------------------------------------------- the work in progress (core/wip.py)
def save_work(r: dict) -> str | None:
    """Saves the run's work in progress (core/wip.py: the same file and the same .bak rule as the desktop app), then hands
    the file to the page, which writes it into the client folder Chrome let the app edit (web/index.html saveFile).
    Inside the browser the file is first written to the tab's in-memory drive at r["wip_path"]; on this computer's Python
    (the tests) only that write happens. Returns the path, or None when the run has no place to save yet."""
    from core import wip as wip_mod
    had_bak = bool(r.get("wip_bak_done"))
    path = wip_mod.save(r)
    if not path:
        return None
    try:
        import webhost                                   # only inside the browser (web/worker.js)
    except ImportError:
        return path
    p = Path(path)
    if not had_bak and p.with_suffix(".bak").is_file():  # the first save of the session kept the old file as .bak
        webhost.save(str(p.with_suffix(".bak")), p.with_suffix(".bak").read_bytes())
    webhost.save(str(p), p.read_bytes())
    return path


def save_k1_work(r: dict, files: list, state) -> str | None:
    """The K-1 page's own work -> '1040 Ultimate K-1 WIP ….json' next to the client's work in progress (core/wip.py save_k1),
    then into the client folder like save_work. Nothing is written while the client's work has no place to be saved."""
    from core import wip as wip_mod
    path = wip_mod.save_k1(r.get("wip_path"), files, state)
    if not path:
        return None
    try:
        import webhost                                   # only inside the browser (web/worker.js)
    except ImportError:
        return path
    webhost.save(path, Path(path).read_bytes())
    return path


def write_out(path: str) -> None:
    """A file Python just wrote on the in-memory drive -> the page writes it into the matching folder / file on the computer
    (web/index.html saveFile: only where Chrome let the app write). On this computer's Python (the tests) nothing more."""
    try:
        import webhost                                   # only inside the browser (web/worker.js)
    except ImportError:
        return
    webhost.save(path, Path(path).read_bytes())


def writable_folder(r: dict) -> str | None:
    """The work-in-progress folder when Chrome lets the app write in it (a folder added with Add a folder… or chosen with
    Choose a folder… - r["places"], see webapp.run_check), else None. A work in progress picked alone with Browse… gives
    write access to that one file only, not to its folder."""
    wip = r.get("wip_path")
    if wip and any(p.endswith("/") and wip.startswith(p) for p in r.get("places") or []):
        return str(Path(wip).parent)
    return None


def shown_folder(path: str) -> str:
    """Where a file is, as the preparer knows it: the client folder's name and sub-folders (not the in-memory drive)."""
    parts = Path(path).parent.parts
    for lead in (("/", "client", "docs"), ("/", "client", "save"), ("/", "client", "picked")):
        if parts[:3] == lead:
            return "/".join(parts[3:]) or parts[-1]
    return str(Path(path).parent)


def not_yet(token: str, on: str, title: str, why: str, lead: str = "Not in the browser app yet.") -> Reply:
    """A step tab whose page isn't in the browser app yet: says so, with the step tabs (templates/not_yet.html).
    lead = the banner's first words (blank for a plain message, e.g. a run that isn't open any more)."""
    return page(render("not_yet.html", token=token, on=on, title=title, why=why, lead=lead))

"""readcache.py - what was read from each file, kept while the app is open, so a file is read only once.

Why: *Add more documents…* (Document inventory) works the run out again with the old and the new documents, so that every
total, tab and check that depends on the documents is right - but only the new files may be read (Lady, 2026-11-17). Every
reader that opens a file asks here first: a file already read (the same content - its fingerprint, not its name) gives back
what was read the first time.

    remember(kind, path, read, *also)   read() once per (kind, file content, also) - later calls get a copy of the result
    clear()                             forget everything (a new Run check reads every file again)

`also` = anything besides the file the result depends on (e.g. the tax year a document is checked against, the form type a
reader was chosen for). The result is always handed out as a copy: changing it can never change what is kept.
"""
from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path

_RESULTS: dict = {}            # (kind, file fingerprint, also) -> what the reader gave
_FPRINTS: dict = {}            # (path, size, modified) -> the file's fingerprint (so a file isn't hashed twice either)


def fingerprint(path) -> str:
    """The file's content fingerprint (SHA-1). The same bytes under another name or folder = the same fingerprint."""
    p = Path(path)
    st = p.stat()
    key = (str(p), st.st_size, st.st_mtime_ns)
    if key not in _FPRINTS:
        _FPRINTS[key] = hashlib.sha1(p.read_bytes()).hexdigest()
    return _FPRINTS[key]


def remember(kind: str, path, read, *also):
    """What read() gives for this file - read only the first time; a copy every time."""
    if not enabled():
        return read()
    try:
        key = (kind, fingerprint(path), also)
    except OSError:                                     # a file that isn't there: nothing to keep, the reader says why
        return read()
    if key not in _RESULTS:
        _RESULTS[key] = read()
    return copy.deepcopy(_RESULTS[key])


def clear() -> None:
    _RESULTS.clear()
    _FPRINTS.clear()


def enabled() -> bool:
    """Off with the environment variable U1040_NO_READCACHE=1 (to time or check the readers themselves)."""
    return os.environ.get("U1040_NO_READCACHE") != "1"

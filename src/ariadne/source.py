"""Sources, lines, locations and caches."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from .span import Span, UNIT, normalize_span


#: The line separators recognised by ariadne (mirrors the Rust source).
_SEPARATORS = "\r\n\x0b\x0c\u0085\u2028\u2029"


@dataclass(frozen=True)
class Line:
    """A single line of a :class:`Source`."""

    offset: int
    char_len: int
    byte_offset: int
    byte_len: int

    def span(self):
        """The character-offset span of this line."""
        return self.offset, self.offset + self.char_len

    def byte_span(self):
        """The byte-offset span of this line (used to slice the raw text)."""
        return self.byte_offset, self.byte_offset + self.byte_len

    def len(self) -> int:
        return self.char_len

    def is_empty(self) -> bool:
        return self.char_len == 0

    def contains(self, offset: int) -> bool:
        return self.offset <= offset < self.offset + self.char_len


@dataclass(frozen=True)
class Location:
    """The line and column of an offset within a source."""

    line: Line
    line_idx: int
    col_idx: int


def _split_inclusive(text: str):
    """Split a string into lines, each including its terminator.

    Mirrors ``str::split_inclusive`` over the ariadne separator set, with
    CRLF treated as a single terminator.
    """
    if not text:
        yield ""
        return
    i = 0
    n = len(text)
    while i < n:
        start = i
        j = i
        while j < n and text[j] not in _SEPARATORS:
            j += 1
        if j >= n:
            yield text[start:j]
            return
        if text[j] == "\r" and j + 1 < n and text[j + 1] == "\n":
            end = j + 2
        else:
            end = j + 1
        yield text[start:end]
        i = end


def _first_ge(offsets, target: int) -> int:
    """First index whose offset equals `target`; otherwise the insert position."""
    lo, hi = 0, len(offsets)
    while lo < hi:
        mid = (lo + hi) // 2
        if offsets[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo


class Source:
    """A single source text that spans may refer to."""

    def __init__(self, text: str):
        self._text = str(text)
        self._lines: list = []
        self._display_line_offset = 0

        char_offset = 0
        byte_offset = 0
        for chunk in _split_inclusive(self._text):
            if not self._text:
                self._lines.append(Line(0, 0, 0, 0))
                break
            byte_len = len(chunk.encode("utf-8"))
            char_len = len(chunk)
            self._lines.append(
                Line(
                    offset=char_offset,
                    char_len=char_len,
                    byte_offset=byte_offset,
                    byte_len=byte_len,
                )
            )
            char_offset += char_len
            byte_offset += byte_len
        self._len = char_offset if self._text else 0
        self._byte_len = byte_offset if self._text else 0

    def text(self) -> str:
        return self._text

    def with_display_line_offset(self, offset: int) -> "Source":
        self._display_line_offset = offset
        return self

    def display_line_offset(self) -> int:
        return self._display_line_offset

    def len(self) -> int:
        return self._len

    def is_empty(self) -> bool:
        return self._len == 0

    def chars(self):
        return iter(self._text)

    def line(self, idx: int) -> Optional[Line]:
        if 0 <= idx < len(self._lines):
            return self._lines[idx]
        return None

    def lines(self):
        return iter(self._lines)

    def _binary_search_line(self, key: int, byte: bool) -> Optional[int]:
        offsets = [line.byte_offset if byte else line.offset for line in self._lines]
        limit = self._byte_len if byte else self._len
        if key > limit:
            return None
        pos = _first_ge(offsets, key)
        if pos < len(offsets) and offsets[pos] == key:
            return pos
        return max(0, pos - 1)

    def get_offset_line(self, offset: int) -> Optional[Location]:
        idx = self._binary_search_line(offset, byte=False)
        if idx is None:
            return None
        line = self._lines[idx]
        return Location(line=line, line_idx=idx, col_idx=offset - line.offset)

    def get_byte_line(self, byte_offset: int) -> Optional[Location]:
        idx = self._binary_search_line(byte_offset, byte=True)
        if idx is None:
            return None
        line = self._lines[idx]
        return Location(line=line, line_idx=idx, col_idx=byte_offset - line.byte_offset)

    def get_line_range(self, span) -> range:
        source, start, end = normalize_span(span)
        loc = self.get_offset_line(start)
        start_line = loc.line_idx if loc is not None else 0
        loc = self.get_offset_line(max(start, end - 1))
        end_line = loc.line_idx + 1 if loc is not None else len(self._lines)
        return range(start_line, end_line)

    def get_line_text(self, line: Line) -> Optional[str]:
        b0, b1 = line.byte_span()
        return self._text.encode("utf-8")[b0:b1].decode("utf-8")

    # Cache implementation for unit spans ------------------------------------

    def fetch(self, _id):
        if _id != UNIT:
            raise KeyError(f"Failed to fetch source '{_id}'")
        return self

    def display(self, _id):
        return None


def _as_source(value) -> Source:
    if isinstance(value, Source):
        return value
    return Source(value)


class Cache:
    """Base class for source caches.

    A cache must implement ``fetch(id) -> Source`` (raising on failure) and
    ``display(id) -> Optional[str]``.  :class:`Source`, :class:`FileCache`,
    :class:`FnCache` and ``(id, Source)`` tuples all act as caches.
    """

    def fetch(self, _id) -> Source:
        raise NotImplementedError

    def display(self, _id) -> Optional[str]:
        return None


class _TupleCache(Cache):
    """Cache for the ``(id, Source)`` tuple form."""

    def __init__(self, id, source: Source):
        self._id = id
        self._source = source

    def fetch(self, id) -> Source:
        if id == self._id:
            return self._source
        raise KeyError(f"Failed to fetch source '{id}'")

    def display(self, id) -> Optional[str]:
        return str(id)


class _DictCache(Cache):
    """Cache wrapping a plain ``{id: str|Source}`` mapping."""

    def __init__(self, mapping: dict):
        self._sources = {k: _as_source(v) for k, v in mapping.items()}

    def fetch(self, id) -> Source:
        try:
            return self._sources[id]
        except KeyError:
            raise KeyError(f"Failed to fetch source '{id}'")

    def display(self, id) -> Optional[str]:
        return str(id)


class FileCache(Cache):
    """A cache that fetches sources from the filesystem."""

    def __init__(self):
        self._files = {}

    def fetch(self, path) -> Source:
        key = os.fspath(path)
        if key not in self._files:
            with open(key, encoding="utf-8") as fh:
                self._files[key] = Source(fh.read())
        return self._files[key]

    def display(self, path) -> Optional[str]:
        return os.fspath(path)


class FnCache(Cache):
    """A cache that fetches sources using a provided callable."""

    def __init__(self, get):
        self._sources = {}
        self._get = get

    def with_sources(self, sources) -> "FnCache":
        for id, src in dict(sources).items():
            self._sources[id] = _as_source(src)
        return self

    def fetch(self, id) -> Source:
        if id not in self._sources:
            self._sources[id] = Source(self._get(id))
        return self._sources[id]

    def display(self, id) -> Optional[str]:
        return str(id)


def sources(iterable: Iterable) -> Cache:
    """Create a cache from a collection of id/source pairs.

    Accepts either a mapping or an iterable of ``(id, text)`` pairs.
    """
    if isinstance(iterable, dict):
        items = iterable.items()
    else:
        items = iterable

    def _missing(id):
        raise KeyError(f"Failed to fetch source '{id}'")

    cache = FnCache(_missing)
    for id, src in items:
        cache._sources[id] = _as_source(src)
    return cache


def as_cache(cache: Any) -> Cache:
    """Normalize the various accepted cache forms into a :class:`Cache`."""
    if isinstance(cache, Cache):
        return cache
    if isinstance(cache, Source):
        return cache
    if isinstance(cache, tuple) and len(cache) == 2 and isinstance(cache[1], Source):
        return _TupleCache(cache[0], cache[1])
    if isinstance(cache, dict):
        return _DictCache(cache)
    raise TypeError(
        f"Invalid cache: {cache!r}. Expected a Source, (id, Source) tuple, "
        "FileCache, FnCache, mapping, or a custom Cache object."
    )

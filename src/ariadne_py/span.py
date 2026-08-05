"""Span handling: a port of ariadne's ``Span`` trait and its implementations."""

from __future__ import annotations

from typing import Any, Tuple


class Span:
    """Base class for custom span types.

    Mirrors the ``Span`` trait: any object exposing ``source()``, ``start()``
    and ``end()`` behaves as a span.  Built-in span forms are plain ``(start,
    end)`` tuples (referring to a unit source) and ``(source_id, (start, end))``
    tuples.
    """

    def source(self):
        raise NotImplementedError

    def start(self) -> int:
        raise NotImplementedError

    def end(self) -> int:
        raise NotImplementedError

    def len(self) -> int:
        return max(0, self.end() - self.start())

    def is_empty(self) -> bool:
        return self.len() == 0

    def contains(self, offset: int) -> bool:
        return self.start() <= offset < self.end()


# The unit source id, equivalent to Rust's `()`.
UNIT = ()


def _is_span_like(value) -> bool:
    if isinstance(value, range):
        return True
    if isinstance(value, slice):
        return True
    if isinstance(value, Span):
        return True
    if hasattr(value, "source") and hasattr(value, "start") and hasattr(value, "end"):
        return True
    if isinstance(value, tuple) and len(value) == 2:
        return isinstance(value[0], int) and isinstance(value[1], int)
    return False


def normalize_span(span) -> Tuple[Any, int, int]:
    """Normalize any supported span form to a ``(source_id, start, end)`` tuple."""
    if isinstance(span, range):
        return UNIT, int(span.start), int(span.stop)
    if isinstance(span, slice):
        if span.step not in (None, 1):
            raise ValueError(f"Invalid span: {span!r}")
        return UNIT, int(span.start or 0), int(span.stop)
    if isinstance(span, tuple):
        if len(span) == 2:
            first, second = span
            if isinstance(first, int) and isinstance(second, int):
                return UNIT, first, second
            if _is_span_like(second):
                inner = normalize_span(second)
                return first, inner[1], inner[2]
        raise ValueError(f"Invalid span: {span!r}")
    if _is_span_like(span):
        return span.source(), int(span.start()), int(span.end())
    raise ValueError(f"Invalid span: {span!r}")


def span_source(span) -> Any:
    return normalize_span(span)[0]


def span_start(span) -> int:
    return normalize_span(span)[1]


def span_end(span) -> int:
    return normalize_span(span)[2]

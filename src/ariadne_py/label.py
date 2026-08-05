"""Labels: the labelled sections of source code shown by reports."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .color import Color
from .span import normalize_span


class LabelAttach(Enum):
    """Where inline label arrows attach to their spans."""

    START = "start"
    MIDDLE = "middle"
    END = "end"

    Start = START
    Middle = MIDDLE
    End = END


class LabelShowLines:
    """How many lines of a multi-line label should be shown."""

    def __init__(self, kind: str, value: int = 0):
        self.kind = kind
        self.value = value

    @classmethod
    def all(cls) -> "LabelShowLines":
        return cls("all")

    @classmethod
    def at_most(cls, n: int) -> "LabelShowLines":
        return cls("at_most", int(n))

    @classmethod
    def All(cls) -> "LabelShowLines":  # Rust-style alias
        return cls("all")

    @classmethod
    def AtMost(cls, n: int) -> "LabelShowLines":  # Rust-style alias
        return cls("at_most", int(n))

    @property
    def is_all(self) -> bool:
        return self.kind == "all"

    def __eq__(self, other):
        return isinstance(other, LabelShowLines) and self.kind == other.kind and self.value == other.value

    def __hash__(self):
        return hash((self.kind, self.value))

    def __repr__(self):
        if self.kind == "all":
            return "LabelShowLines.All"
        return f"LabelShowLines.AtMost({self.value})"


@dataclass
class _LabelDisplay:
    msg: Optional[str] = None
    color: Optional[Color] = None
    style: Optional[str] = None
    order: int = 0
    priority: int = 0
    show_lines: LabelShowLines = None

    def __post_init__(self):
        if self.show_lines is None:
            self.show_lines = LabelShowLines.at_most(2)

    def get_style(self, config):
        if self.style is not None:
            return config.get_style(self.style)
        if self.color is not None:
            return self.color.foreground()
        return None


class Label:
    """A labelled section of source code.

    Create one with ``Label(span)`` where ``span`` is ``(start, end)`` or
    ``(source_id, (start, end))``.  Builder methods mirror the Rust API
    (``with_message``, ``with_color``, ``with_style``, ``with_order``,
    ``with_priority``, ``with_show_lines``).
    """

    def __init__(self, span):
        source, start, end = normalize_span(span)
        if start > end:
            raise ValueError("Label start is after its end")
        self.span = (source, start, end)
        self._display = _LabelDisplay()

    # Span accessors ---------------------------------------------------------

    def source(self):
        return self.span[0]

    def start(self) -> int:
        return self.span[1]

    def end(self) -> int:
        return self.span[2]

    # Builder methods --------------------------------------------------------

    def with_message(self, msg) -> "Label":
        self._display.msg = str(msg)
        return self

    def with_color(self, color: Color) -> "Label":
        self._display.color = color
        return self

    def with_style(self, style: str) -> "Label":
        self._display.style = str(style)
        return self

    def with_order(self, order: int) -> "Label":
        self._display.order = int(order)
        return self

    def with_priority(self, priority: int) -> "Label":
        self._display.priority = int(priority)
        return self

    def with_show_lines(self, show_lines: LabelShowLines) -> "Label":
        self._display.show_lines = show_lines
        return self

    def __repr__(self):
        return f"Label({self.span!r}, msg={self._display.msg!r})"

"""Drawing primitives: character sets, color generation and formatting helpers."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import Enum

from .color import Color, Style


def _f32(x: float) -> float:
    return struct.unpack("f", struct.pack("f", x))[0]


def _f32_add(a: float, b: float) -> float:
    return _f32(_f32(a) + _f32(b))


def _f32_sub(a: float, b: float) -> float:
    return _f32(_f32(a) - _f32(b))


def _f32_mul(a: float, b: float) -> float:
    return _f32(_f32(a) * _f32(b))


def _f32_div(a: float, b: float) -> float:
    return _f32(_f32(a) / _f32(b))


@dataclass(frozen=True)
class Characters:
    """The set of characters used to draw boxes, arrows and underlines."""

    hbar: str = "─"
    vbar: str = "│"
    xbar: str = "┼"
    vbar_gap: str = "┆"
    uarrow: str = "▲"
    rarrow: str = "▶"
    ltop: str = "╭"
    lbot: str = "╰"
    mbot: str = "┴"
    rbot: str = "╯"
    lbox: str = "┤"
    rbox: str = "│"
    lcross: str = "├"
    rcross: str = "┤"
    lunderbar: str = "┌"
    runderbar: str = "┐"
    munderbar: str = "┬"
    underline: str = "─"
    underbar_single: str = "▲"

    @classmethod
    def unicode(cls) -> "Characters":
        return cls()

    @classmethod
    def ascii(cls) -> "Characters":
        return cls(
            hbar="-",
            vbar="|",
            xbar="+",
            vbar_gap=":",
            uarrow="^",
            rarrow=">",
            ltop=",",
            lbot="`",
            mbot="-",
            rbot="'",
            lbox="[",
            rbox="]",
            lcross="|",
            rcross="|",
            lunderbar="-",
            runderbar="-",
            munderbar="-",
            underline="-",
            underbar_single="^",
        )

    def arrow_bend(self, is_top: bool) -> str:
        return self.ltop if is_top else self.lbot

    def vbar_char(self, is_gap: bool) -> str:
        return self.vbar_gap if is_gap else self.vbar


class StreamType(Enum):
    """Which output stream styled items will be written to."""

    STDOUT = "stdout"
    STDERR = "stderr"

    Stdout = STDOUT
    Stderr = STDERR


class ColorGenerator:
    """Generates a sequence of distinct 8-bit colors.

    Faithful port of ariadne's ``ColorGenerator`` (including its exact f32
    arithmetic, so generated colors match the Rust crate byte-for-byte).
    """

    def __init__(self, state=(30000, 15000, 35000), min_brightness=0.5):
        self.state = [int(x) for x in state]
        self.min_brightness = max(0.0, min(1.0, float(min_brightness)))

    @classmethod
    def new(cls) -> "ColorGenerator":
        return cls()

    @classmethod
    def from_state(cls, state, min_brightness: float) -> "ColorGenerator":
        return cls(list(state), min_brightness)

    def next(self) -> Color:
        for i in range(3):
            self.state[i] = (self.state[i] + 40503 * (i * 4 + 1130)) & 0xFFFF
        b = _f32(self.min_brightness)
        one = _f32(1.0)
        f65535 = _f32(65535.0)
        term0 = _f32_mul(
            _f32_add(_f32_mul(_f32_div(_f32(self.state[0]), f65535), _f32_sub(one, b)), b),
            _f32(180.0),
        )
        term1 = _f32_mul(
            _f32_add(_f32_mul(_f32_div(_f32(self.state[1]), f65535), _f32_sub(one, b)), b),
            _f32(30.0),
        )
        term2 = _f32_mul(
            _f32_add(_f32_mul(_f32_div(_f32(self.state[2]), f65535), _f32_sub(one, b)), b),
            _f32(5.0),
        )
        value = int(_f32_add(_f32_add(term2, term1), term0))
        return Color.fixed(16 + value)


class _Painted:
    """A piece of text with an optional foreground/background color."""

    __slots__ = ("text", "fg", "bg")

    def __init__(self, text, fg, bg):
        self.text = text
        self.fg = fg
        self.bg = bg

    def __str__(self):
        return Style(fg=self.fg, bg=self.bg).paint(self.text)

    def __repr__(self):
        return f"Painted({self.text!r}, fg={self.fg!r}, bg={self.bg!r})"


class Fmt:
    """Formatting helpers, mirroring ariadne's ``Fmt`` trait.

    Rust usage is ``"Nat".fg(color)``; in Python the equivalent is
    ``Fmt.fg("Nat", color)``.  The returned object renders to an ANSI-styled
    string.
    """

    @staticmethod
    def fg(text, color) -> _Painted:
        return _Painted(str(text), color, None)

    @staticmethod
    def bg(text, color) -> _Painted:
        return _Painted(str(text), None, color)

    @staticmethod
    def style(text, style) -> "_StyledText":
        return _StyledText(str(text), style)


class _StyledText:
    __slots__ = ("text", "style")

    def __init__(self, text, style):
        self.text = text
        self.style = style

    def __str__(self):
        if self.style is None:
            return self.text
        return self.style.paint(self.text)

    def __repr__(self):
        return f"Styled({self.text!r}, {self.style!r})"


class StreamAwareFmt:
    """Stream-aware formatting helpers (kept for API compatibility)."""

    @staticmethod
    def color_enabled_for(_stream: StreamType) -> bool:
        return True

    @staticmethod
    def fg(text, color, _stream: StreamType = StreamType.STDERR) -> _Painted:
        return _Painted(str(text), color, None)

    @staticmethod
    def bg(text, color, _stream: StreamType = StreamType.STDOUT) -> _Painted:
        return _Painted(str(text), None, color)

    @staticmethod
    def style(text, style, _stream: StreamType = StreamType.STDERR) -> _StyledText:
        return _StyledText(str(text), style)


class StdoutFmt:
    """Stdout-aware formatting helpers (kept for API compatibility)."""

    @staticmethod
    def fg(text, color) -> _Painted:
        return _Painted(str(text), color, None)

    @staticmethod
    def bg(text, color) -> _Painted:
        return _Painted(str(text), None, color)


class Styleable:
    """Helpers for text that carries named styles, mirroring the ``Styleable``
    trait (unstable feature in Rust, always available here).

    Rust usage is ``"Nat".style("name")``; the Python equivalent is
    ``Styleable.style("Nat", "name")``.
    """

    @staticmethod
    def style(text, name: str) -> "_TaggedText":
        return _TaggedText(str(text), name)


class _TaggedText:
    __slots__ = ("text", "name")

    def __init__(self, text, name):
        self.text = text
        self.name = name

    def __str__(self):
        # In-line tags start with 0x13 and end with 0x11.
        return f"\x13@{{{self.name}\x11{self.text}\x13@}}\x11"

    def __repr__(self):
        return f"StyledTag({self.text!r}, {self.name!r})"


def unicode_width(c: str) -> int:
    """Approximation of the ``unicode-width`` crate's ``char::width``."""
    import unicodedata

    if unicodedata.combining(c):
        return 0
    if c in "\u200b\u200c\u200d\u2060\ufeff":
        return 0
    return 2 if unicodedata.east_asian_width(c) in ("W", "F") else 1

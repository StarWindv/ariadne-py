"""Minimal, faithful emulation of the `yansi` `Color` and `Style` types used by ariadne."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional


class Color:
    """An ANSI color.

    Mirrors ``yansi::Color``: named colors, 8-bit fixed colors and 24-bit RGB colors.
    """

    __slots__ = ("kind", "value")

    def __init__(self, kind: str, value=None):
        self.kind = kind
        self.value = value

    # --- named colors -------------------------------------------------------

    Black = None
    Red = None
    Green = None
    Yellow = None
    Blue = None
    Magenta = None
    Cyan = None
    White = None

    BrightBlack = None
    BrightRed = None
    BrightGreen = None
    BrightYellow = None
    BrightBlue = None
    BrightMagenta = None
    BrightCyan = None
    BrightWhite = None

    Default = None

    _NAMED_CODES = {
        "black": 30,
        "red": 31,
        "green": 32,
        "yellow": 33,
        "blue": 34,
        "magenta": 35,
        "cyan": 36,
        "white": 37,
        "brightblack": 90,
        "brightred": 91,
        "brightgreen": 92,
        "brightyellow": 93,
        "brightblue": 94,
        "brightmagenta": 95,
        "brightcyan": 96,
        "brightwhite": 97,
        "default": 39,
    }

    @classmethod
    def fixed(cls, n: int) -> "Color":
        """Create an 8-bit fixed color (0-255), like ``Color::Fixed(n)``."""
        return cls("fixed", int(n))

    @classmethod
    def rgb(cls, r: int, g: int, b: int) -> "Color":
        """Create a 24-bit RGB color, like ``Color::RGB(r, g, b)``."""
        return cls("rgb", (int(r), int(g), int(b)))

    def ansi(self) -> str:
        """The ANSI SGR parameter string for this color as a foreground color."""
        if self.kind == "named":
            return str(self._NAMED_CODES[self.value])
        if self.kind == "fixed":
            return f"38;5;{self.value}"
        if self.kind == "rgb":
            r, g, b = self.value
            return f"38;2;{r};{g};{b}"
        raise AssertionError(f"unknown color kind: {self.kind}")

    def bg_ansi(self) -> str:
        """The ANSI SGR parameter string for this color as a background color."""
        if self.kind == "named":
            return str(self._NAMED_CODES[self.value] + 10)
        if self.kind == "fixed":
            return f"48;5;{self.value}"
        if self.kind == "rgb":
            r, g, b = self.value
            return f"48;2;{r};{g};{b}"
        raise AssertionError(f"unknown color kind: {self.kind}")

    def foreground(self) -> "Style":
        """Create a style with this color as its foreground color."""
        return Style(fg=self)

    def background(self) -> "Style":
        """Create a style with this color as its background color."""
        return Style(bg=self)

    def __eq__(self, other):
        return isinstance(other, Color) and self.kind == other.kind and self.value == other.value

    def __hash__(self):
        return hash((self.kind, self.value))

    def __repr__(self):
        if self.kind == "named":
            return f"Color.{self.value.title()}"
        if self.kind == "fixed":
            return f"Color.Fixed({self.value})"
        return f"Color.RGB{self.value}"


Color.Black = Color("named", "black")
Color.Red = Color("named", "red")
Color.Green = Color("named", "green")
Color.Yellow = Color("named", "yellow")
Color.Blue = Color("named", "blue")
Color.Magenta = Color("named", "magenta")
Color.Cyan = Color("named", "cyan")
Color.White = Color("named", "white")
Color.BrightBlack = Color("named", "brightblack")
Color.BrightRed = Color("named", "brightred")
Color.BrightGreen = Color("named", "brightgreen")
Color.BrightYellow = Color("named", "brightyellow")
Color.BrightBlue = Color("named", "brightblue")
Color.BrightMagenta = Color("named", "brightmagenta")
Color.BrightCyan = Color("named", "brightcyan")
Color.BrightWhite = Color("named", "brightwhite")
Color.Default = Color("named", "default")


@dataclass(frozen=True)
class Style:
    """A text style, mirroring ``yansi::Style``."""

    fg: Optional[Color] = None
    bg: Optional[Color] = None
    bold: bool = False
    dimmed: bool = False
    italic: bool = False
    underline: bool = False
    blink: bool = False
    rapid_blink: bool = False
    reversed: bool = False
    hidden: bool = False
    strikethrough: bool = False

    _ATTRS = (
        ("bold", "1"),
        ("dimmed", "2"),
        ("italic", "3"),
        ("underline", "4"),
        ("blink", "5"),
        ("rapid_blink", "6"),
        ("reversed", "7"),
        ("hidden", "8"),
        ("strikethrough", "9"),
    )

    def is_empty(self) -> bool:
        return (
            self.fg is None
            and self.bg is None
            and not any(getattr(self, name) for name, _ in self._ATTRS)
        )

    def codes(self) -> list:
        codes = []
        if self.fg is not None:
            codes.append(self.fg.ansi())
        if self.bg is not None:
            codes.append(self.bg.bg_ansi())
        for name, code in self._ATTRS:
            if getattr(self, name):
                codes.append(code)
        return codes

    def paint(self, text) -> str:
        """Apply this style, returning ANSI-wrapped text (or the raw text if empty)."""
        text = str(text)
        if self.is_empty():
            return text
        return f"\x1b[{';'.join(self.codes())}m{text}\x1b[0m"

    def with_fg(self, color: Optional[Color]) -> "Style":
        return replace(self, fg=color)

    def with_bg(self, color: Optional[Color]) -> "Style":
        return replace(self, bg=color)

    def with_bold(self, enabled: bool = True) -> "Style":
        return replace(self, bold=enabled)

    def with_dimmed(self, enabled: bool = True) -> "Style":
        return replace(self, dimmed=enabled)

    def with_italic(self, enabled: bool = True) -> "Style":
        return replace(self, italic=enabled)

    def with_underline(self, enabled: bool = True) -> "Style":
        return replace(self, underline=enabled)

    def with_reversed(self, enabled: bool = True) -> "Style":
        return replace(self, reversed=enabled)

    def with_hidden(self, enabled: bool = True) -> "Style":
        return replace(self, hidden=enabled)

    def with_strikethrough(self, enabled: bool = True) -> "Style":
        return replace(self, strikethrough=enabled)

    def with_blink(self, enabled: bool = True) -> "Style":
        return replace(self, blink=enabled)

    def with_rapid_blink(self, enabled: bool = True) -> "Style":
        return replace(self, rapid_blink=enabled)

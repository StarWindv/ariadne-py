"""Configuration of report rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .color import Color, Style
from .draw import Characters, unicode_width
from .label import LabelAttach


class IndexType(Enum):
    """Whether spans are interpreted as character or byte offsets."""

    BYTE = "byte"
    CHAR = "char"

    Byte = BYTE
    Char = CHAR


class AnsiMode(Enum):
    """Whether ANSI escape styling should be included in output."""

    OFF = "off"
    ON = "on"

    Off = OFF
    On = ON


@dataclass
class ReportStyling:
    """The colors used by the various report elements."""

    error_style: Style = field(default_factory=lambda: Color.Red.foreground())
    warning_style: Style = field(default_factory=lambda: Color.Yellow.foreground())
    advice_style: Style = field(default_factory=lambda: Color.fixed(147).foreground())
    margin_style: Style = field(default_factory=lambda: Color.fixed(246).foreground())
    skipped_margin_style: Style = field(default_factory=lambda: Color.fixed(240).foreground())
    unimportant_style: Style = field(default_factory=lambda: Color.fixed(249).foreground())
    note_style: Style = field(default_factory=lambda: Color.fixed(115).foreground())


@dataclass
class Config:
    """A type used to configure a report.

    All ``with_*`` methods mutate and return ``self``, mirroring the Rust
    builder-style API.
    """

    cross_gap: bool = True
    label_attach: LabelAttach = LabelAttach.MIDDLE
    compact: bool = False
    underlines: bool = True
    multiline_arrows: bool = True
    color: bool = True
    tab_width: int = 4
    char_set: Characters = field(default_factory=Characters.unicode)
    index_type: IndexType = IndexType.CHAR
    minimise_crossings: bool = False
    context_lines: int = 0
    ansi_mode: AnsiMode = AnsiMode.ON
    enumerate_notes: bool = True
    enumerate_helps: bool = True
    styles: Optional[dict] = None
    report_style: ReportStyling = field(default_factory=ReportStyling)

    def with_cross_gap(self, cross_gap: bool) -> "Config":
        self.cross_gap = cross_gap
        return self

    def with_label_attach(self, label_attach: LabelAttach) -> "Config":
        self.label_attach = label_attach
        return self

    def with_compact(self, compact: bool) -> "Config":
        self.compact = compact
        return self

    def with_underlines(self, underlines: bool) -> "Config":
        self.underlines = underlines
        return self

    def with_multiline_arrows(self, multiline_arrows: bool) -> "Config":
        self.multiline_arrows = multiline_arrows
        return self

    def with_color(self, color: bool) -> "Config":
        self.color = color
        return self

    def with_tab_width(self, tab_width: int) -> "Config":
        self.tab_width = tab_width
        return self

    def with_char_set(self, char_set: Characters) -> "Config":
        self.char_set = char_set
        return self

    def with_index_type(self, index_type: IndexType) -> "Config":
        self.index_type = index_type
        return self

    def with_minimise_crossings(self, minimise_crossings: bool) -> "Config":
        self.minimise_crossings = minimise_crossings
        return self

    def with_context_lines(self, context_lines: int) -> "Config":
        self.context_lines = context_lines
        return self

    def with_ansi_mode(self, ansi_mode: AnsiMode) -> "Config":
        self.ansi_mode = ansi_mode
        return self

    def with_enumerated_notes(self, enumerate_notes: bool) -> "Config":
        self.enumerate_notes = enumerate_notes
        return self

    def with_enumerated_helps(self, enumerate_helps: bool) -> "Config":
        self.enumerate_helps = enumerate_helps
        return self

    def with_report_style(self, report_style: ReportStyling) -> "Config":
        self.report_style = report_style
        return self

    def with_style(self, name: str, style: Style) -> "Config":
        if self.styles is None:
            self.styles = {}
        if name in self.styles:
            raise ValueError(f"Duplicate style: `{name}`")
        self.styles[name] = style
        return self

    # Internal helpers -------------------------------------------------------

    def error_style(self) -> Optional[Style]:
        return self.report_style.error_style if self.color else None

    def warning_style(self) -> Optional[Style]:
        return self.report_style.warning_style if self.color else None

    def advice_style(self) -> Optional[Style]:
        return self.report_style.advice_style if self.color else None

    def margin_style(self) -> Optional[Style]:
        return self.report_style.margin_style if self.color else None

    def skipped_margin_style(self) -> Optional[Style]:
        return self.report_style.skipped_margin_style if self.color else None

    def unimportant_style(self) -> Optional[Style]:
        return self.report_style.unimportant_style if self.color else None

    def note_style(self) -> Optional[Style]:
        return self.report_style.note_style if self.color else None

    def filter_color(self, color: Optional[Color]) -> Optional[Color]:
        return color if self.color else None

    def char_width(self, c: str, col: int):
        if c == "\t":
            tab_end = (col // self.tab_width + 1) * self.tab_width
            return " ", tab_end - col
        if c.isspace():
            return " ", 1
        return c, unicode_width(c)

    def get_style(self, name: str) -> Style:
        if self.styles is not None:
            style = self.styles.get(name)
            if style is not None:
                return style
        return Style()

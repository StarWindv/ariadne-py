"""Report style types."""

from __future__ import annotations

from typing import Protocol

from ..color import Color, Style
from ..config import Config


class ReportStyle(Protocol):
    """A type that determines the colour/style of a report header."""

    def get_color(self, config: Config):
        ...

    def get_style(self, config: Config):
        ...


class BasicStyle:
    """A simple report style: a display name and a colour."""

    def __init__(self, name, color: Color):
        self.name = str(name)
        self.color = color

    def get_color(self, config: Config):
        return self.color if config.color else None

    def get_style(self, config: Config):
        color = self.get_color(config)
        return color.foreground() if color is not None else None

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"BasicStyle({self.name!r}, {self.color!r})"


class _StrReportStyle:
    """Adapter letting plain strings be used as report styles (no colour)."""

    def __init__(self, name: str):
        self._name = str(name)

    def get_color(self, _config: Config):
        return None

    def get_style(self, _config: Config):
        return None

    def __str__(self):
        return self._name

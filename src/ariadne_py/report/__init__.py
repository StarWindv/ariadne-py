"""Reports: diagnostics ready to be written to output."""

from __future__ import annotations

from ..config import Config
from ..draw import Fmt


class ReportKind:
    """Basic kinds of reports, mirroring the Rust ``ReportKind`` enum.

    Use ``ReportKind.Error``, ``ReportKind.Warning``, ``ReportKind.Advice`` or
    ``ReportKind.custom(name, color)``.
    """

    def __init__(self, name: str, color=None):
        self._name = name
        self._color = color

    @classmethod
    def custom(cls, name, color):
        return cls(str(name), color)

    def get_style(self, config: Config):
        if self is ReportKind.Error:
            return config.error_style()
        if self is ReportKind.Warning:
            return config.warning_style()
        if self is ReportKind.Advice:
            return config.advice_style()
        if self._color is not None:
            return self._color.foreground() if config.color else None
        return None

    def __str__(self):
        return self._name

    def __repr__(self):
        return f"ReportKind.{self._name}"


ReportKind.Error = ReportKind("Error")
ReportKind.Warning = ReportKind("Warning")
ReportKind.Advice = ReportKind("Advice")


from .builder import ReportBuilder  # noqa: E402
from .write import Report  # noqa: E402

__all__ = ["Report", "ReportKind", "ReportBuilder"]

"""The report builder."""

from __future__ import annotations

from typing import Iterable

from ..config import Config
from ..span import normalize_span
from .style import _StrReportStyle


class ReportBuilder:
    """A type used to build a :class:`~ariadne.report.write.Report`."""

    def __init__(self, kind, span, config: Config = None):
        if isinstance(kind, str):
            kind = _StrReportStyle(kind)
        self.kind = kind
        self.msg = None
        self.notes = []
        self.help = []
        self.span = normalize_span(span)
        self.labels = []
        self.config = config if config is not None else Config()

    def set_message(self, msg) -> None:
        self.msg = str(msg)

    def with_message(self, msg) -> "ReportBuilder":
        self.msg = str(msg)
        return self

    def set_note(self, note) -> None:
        self.notes = [str(note)]

    def add_note(self, note) -> None:
        self.notes.append(str(note))

    def with_notes(self, notes: Iterable) -> "ReportBuilder":
        for note in notes:
            self.add_note(note)
        return self

    def with_note(self, note) -> "ReportBuilder":
        self.add_note(note)
        return self

    def set_help(self, help) -> None:
        self.help = [str(help)]

    def add_help(self, help) -> None:
        self.help.append(str(help))

    def add_helps(self, helps: Iterable) -> None:
        for help in helps:
            self.add_help(help)

    def with_help(self, help) -> "ReportBuilder":
        self.add_help(help)
        return self

    def with_helps(self, helps: Iterable) -> "ReportBuilder":
        self.add_helps(helps)
        return self

    def add_label(self, label) -> None:
        self.add_labels([label])

    def add_labels(self, labels: Iterable) -> None:
        for label in labels:
            label._display.color = self.config.filter_color(label._display.color)
            self.labels.append(label)

    def with_label(self, label) -> "ReportBuilder":
        self.add_label(label)
        return self

    def with_labels(self, labels: Iterable) -> "ReportBuilder":
        self.add_labels(labels)
        return self

    def with_config(self, config: Config) -> "ReportBuilder":
        self.config = config
        return self

    def finish(self):
        from .write import Report

        return Report(self)

"""ariadne-py: a Python port of the `ariadne <https://crates.io/crates/ariadne>`_ 0.7.0
fancy diagnostics crate.

The public API mirrors the Rust crate:

    from ariadne_py import Label, Report, ReportKind, Source

    Report.build(ReportKind.Error, (34, 34)) \
        .with_message("Incompatible types") \
        .with_label(Label((32, 33)).with_message("This is of type Nat")) \
        .with_label(Label((52, 55)).with_message("This is of type Str")) \
        .finish() \
        .print(Source("..."))
"""

from .color import Color, Style
from .config import AnsiMode, Config, IndexType, ReportStyling
from .draw import (
    Characters,
    ColorGenerator,
    Fmt,
    StdoutFmt,
    StreamAwareFmt,
    StreamType,
    Styleable,
)
from .label import Label, LabelAttach, LabelShowLines
from .report import Report, ReportBuilder, ReportKind
from .report.style import BasicStyle, ReportStyle
from .source import Cache, FileCache, FnCache, Line, Location, Source, sources
from .span import Span

__version__ = "0.7.0"

__all__ = [
    "AnsiMode",
    "BasicStyle",
    "Cache",
    "Characters",
    "Color",
    "ColorGenerator",
    "Config",
    "FileCache",
    "Fmt",
    "FnCache",
    "IndexType",
    "Label",
    "LabelAttach",
    "LabelShowLines",
    "Line",
    "Location",
    "Report",
    "ReportBuilder",
    "ReportKind",
    "ReportStyle",
    "ReportStyling",
    "Source",
    "Span",
    "StdoutFmt",
    "StreamAwareFmt",
    "StreamType",
    "Style",
    "Styleable",
    "sources",
]

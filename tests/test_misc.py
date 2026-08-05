"""Tests for colors, character sets, color generation and tagged text."""

import pytest

from ariadne_py import (
    Color,
    ColorGenerator,
    Config,
    Fmt,
    Label,
    LabelShowLines,
    Report,
    ReportKind,
    Source,
    Style,
    Styleable,
)


def test_style_painting():
    assert Style().paint("x") == "x"
    assert Color.Red.foreground().paint("x") == "\x1b[31mx\x1b[0m"
    assert Color.fixed(246).foreground().paint("x") == "\x1b[38;5;246mx\x1b[0m"
    assert Color.rgb(1, 2, 3).foreground().paint("x") == "\x1b[38;2;1;2;3mx\x1b[0m"
    assert Color.Blue.background().paint("x") == "\x1b[44mx\x1b[0m"
    assert Color.Yellow.foreground().with_bold().paint("x") == "\x1b[33;1mx\x1b[0m"


def test_color_generator_matches_rust():
    gen = ColorGenerator.new()
    colors = [gen.next() for _ in range(8)]
    # Values verified against the Rust crate.
    assert [c.value for c in colors] == [201, 155, 187, 218, 158, 189, 131, 175]


def test_label_backwards_raises():
    with pytest.raises(ValueError):
        Label((5, 1))


def test_label_show_lines():
    assert LabelShowLines.all().is_all
    assert not LabelShowLines.at_most(4).is_all


def test_ascii_char_set():
    out = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(Config().with_color(False).with_char_set(__import__("ariadne_py").Characters.ascii()))
        .with_message("ascii")
        .with_label(Label((0, 5)).with_message("msg"))
        .finish()
        .write_to_string(Source("apple == orange;"))
    )
    assert "╭" not in out and "─" not in out
    assert "," in out and "-" in out


def test_ansi_off_strips_escapes():
    out = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(
            Config()
            .with_ansi_mode(__import__("ariadne_py").AnsiMode.OFF)
        )
        .with_message("no ansi")
        .finish()
        .write_to_string(Source("apple"))
    )
    assert "\x1b" not in out


def test_named_styles_in_messages():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_message(f"a {Styleable.style('styled', 's1')} b")
        .with_config(Config().with_style("s1", Color.Blue.foreground()))
        .finish()
        .write_to_string(Source(""))
    )
    assert "\x1b[34mstyled\x1b[0m" in report


def test_fmt_helpers():
    assert str(Fmt.fg("x", Color.Red)) == "\x1b[31mx\x1b[0m"
    assert str(Fmt.bg("x", Color.Blue)) == "\x1b[44mx\x1b[0m"


def test_custom_report_kind():
    kind = ReportKind.custom("Note", Color.Magenta)
    out = (
        Report.build(kind, (0, 0))
        .with_message("custom")
        .finish()
        .write_to_string(Source(""))
    )
    assert out.startswith("\x1b[35mNote\x1b[0m: custom")


def test_basic_style():
    from ariadne_py import BasicStyle

    out = (
        Report.build(BasicStyle("Error", Color.Red), (0, 0))
        .with_message("x")
        .finish()
        .write_to_string(Source(""))
    )
    assert out.startswith("\x1b[31mError\x1b[0m: x")


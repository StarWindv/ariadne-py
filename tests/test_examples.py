"""Compare the ported examples byte-for-byte against the Rust crate's output."""

from pathlib import Path

from ariadne_py import (
    Color,
    ColorGenerator,
    Config,
    Fmt,
    Label,
    Report,
    ReportKind,
    Source,
    sources,
)


FIXTURES = Path(__file__).parent / "fixtures"


def raw(name: str) -> str:
    return (FIXTURES / name).read_bytes().decode("utf-8")


def test_simple_example():
    sample = raw("sample.tao")
    out = (
        Report.build(ReportKind.Error, (34, 34))
        .with_message("Incompatible types")
        .with_label(Label((32, 33)).with_message("This is of type Nat"))
        .with_label(Label((52, 55)).with_message("This is of type Str"))
        .finish()
        .write_to_string(Source(sample))
    )
    assert out.replace("\r\n", "\n") == raw("simple.out").replace("\r\n", "\n")


def test_labels_example():
    out = (
        Report.build(ReportKind.Error, (2, 3))
        .with_message("Incompatible types")
        .with_config(Config().with_compact(True))
        .with_label(Label((0, 1)).with_color(Color.Red))
        .with_label(
            Label((2, 3))
            .with_color(Color.Blue)
            .with_message("`b` for banana")
            .with_order(1)
        )
        .with_label(Label((4, 5)).with_color(Color.Green))
        .with_label(
            Label((7, 9))
            .with_color(Color.Cyan)
            .with_message("`e` for emerald")
        )
        .finish()
        .write_to_string(Source("a b c d e f"))
    )
    assert out.replace("\r\n", "\n") == raw("labels.out").replace("\r\n", "\n")


def test_multifile_example():
    colors = ColorGenerator.new()
    a, b, c = colors.next(), colors.next(), colors.next()
    out = (
        Report.build(ReportKind.Error, ("b.tao", (10, 14)))
        .with_message("Cannot add types Nat and Str")
        .with_label(
            Label(("b.tao", (10, 14)))
            .with_message(f"This is of type {Fmt.fg('Nat', a)}")
            .with_color(a)
        )
        .with_label(
            Label(("b.tao", (17, 20)))
            .with_message(f"This is of type {Fmt.fg('Str', b)}")
            .with_color(b)
        )
        .with_label(
            Label(("b.tao", (15, 16)))
            .with_message(
                f" {Fmt.fg('Nat', a)} and {Fmt.fg('Str', b)} undergo addition here"
            )
            .with_color(c)
            .with_order(10)
        )
        .with_label(
            Label(("a.tao", (4, 8)))
            .with_message(f"Original definition of {Fmt.fg('five', a)} is here")
            .with_color(a)
        )
        .with_note(f"{Fmt.fg('Nat', a)} is a number and can only be added to other numbers")
        .with_note("Multiple notes are possible")
        .with_note("Multiline notes\ncan be also used when the note is humongous.")
        .finish()
        .write_to_string(
            sources({"a.tao": raw("a.tao"), "b.tao": raw("b.tao")})
        )
    )
    assert out.replace("\r\n", "\n") == raw("multifile.out").replace("\r\n", "\n")


def test_multiline_example():
    colors = ColorGenerator.new()
    a, b = colors.next(), colors.next()
    out = Color.fixed(81)
    out2 = colors.next()
    sample = raw("sample.tao")
    out = (
        Report.build(ReportKind.Error, ("sample.tao", (32, 33)))
        .with_message("Incompatible types")
        .with_label(
            Label(("sample.tao", (32, 33)))
            .with_message(f"This is of type {Fmt.fg('Nat', a)}")
            .with_color(a)
        )
        .with_label(
            Label(("sample.tao", (52, 55)))
            .with_message(f"This is of type {Fmt.fg('Str', b)}")
            .with_color(b)
        )
        .with_label(
            Label(("sample.tao", (11, 58)))
            .with_message(f"The values are outputs of this {Fmt.fg('match', out)} expression")
            .with_color(out)
        )
        .with_label(
            Label(("sample.tao", (0, 58)))
            .with_message(f"The {Fmt.fg('definition', out2)} has a problem")
            .with_color(out2)
        )
        .with_label(
            Label(("sample.tao", (60, 86)))
            .with_message(f"Usage of {Fmt.fg('definition', out2)} here")
            .with_color(out2)
        )
        .with_note(f"Outputs of {Fmt.fg('match', out)} expressions must coerce to the same type")
        .finish()
        .write_to_string(("sample.tao", Source(sample)))
    )
    assert out.replace("\r\n", "\n") == raw("multiline.out").replace("\r\n", "\n")


def test_stresstest_example():
    colors = ColorGenerator.new()
    builder = (
        Report.build(ReportKind.Error, ("stresstest.tao", (13, 13)))
        .with_message("Incompatible types")
    )
    for i in range(21):
        builder = builder.with_label(
            Label(("stresstest.tao", (i, i + 1)))
            .with_message("Color")
            .with_color(colors.next())
        )
    for span, msg in [
        ((18, 19), "This is of type Nat"),
        ((13, 16), "This is of type Str"),
        ((40, 41), "This is of type Nat"),
        ((43, 47), "This is of type Bool"),
        ((49, 51), "This is of type ()"),
        ((53, 55), "This is of type [_]"),
        ((25, 78), "This is of type Str"),
        ((81, 124), "This is of type Nat"),
        ((100, 126), "This is an inner multi-line"),
        ((106, 120), "This is another inner multi-line"),
        ((108, 122), "This is *really* nested multi-line"),
        ((110, 111), "This is an inline within the nesting!"),
        ((111, 112), "And another!"),
        ((103, 123), "This is *really* nested multi-line"),
        ((105, 125), "This is *really* nested multi-line"),
        ((112, 116), "This is *really* nested multi-line"),
    ]:
        builder = builder.with_label(
            Label(("stresstest.tao", span))
            .with_message(msg)
            .with_color(colors.next())
        )
    builder = (
        builder.with_label(
            Label(("stresstest.tao", (26, 100)))
            .with_message("Hahaha!")
            .with_color(Color.fixed(75))
        )
        .with_label(
            Label(("stresstest.tao", (85, 110)))
            .with_message("Oh god, no more 1")
            .with_color(colors.next())
        )
        .with_label(
            Label(("stresstest.tao", (84, 114)))
            .with_message("Oh god, no more 2")
            .with_color(colors.next())
        )
        .with_label(
            Label(("stresstest.tao", (89, 113)))
            .with_message("Oh god, no more 3")
            .with_color(colors.next())
        )
        .with_config(
            Config()
            .with_cross_gap(True)
            .with_compact(False)
            .with_underlines(True)
            .with_tab_width(4)
            .with_minimise_crossings(True)
        )
    )
    out = builder.finish().write_to_string(
        ("stresstest.tao", Source(raw("stresstest.tao")))
    )
    assert out.replace("\r\n", "\n") == raw("stresstest.out").replace("\r\n",  "\n")

"""Port of the Rust crate's ``report/tests.rs`` snapshot tests.

Expected strings are the insta inline snapshots extracted from the Rust source
(see ``tests/fixtures/report_snapshots.json``), so a passing suite means the
Python renderer is byte-identical to ariadne 0.7.0 (in no-color mode).
"""

import json
import os
from pathlib import Path

import pytest

from ariadne import (
    Config,
    FnCache,
    IndexType,
    Label,
    LabelShowLines,
    Report,
    ReportKind,
    Source,
    sources,
)


FIXTURES = Path(__file__).parent / "fixtures"
with open(FIXTURES / "report_snapshots.json", encoding="utf-8") as fh:
    SNAPSHOTS = json.load(fh)


def no_color() -> Config:
    return Config().with_color(False)


def remove_trailing(s: str) -> str:
    lines = s.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return "".join(line.rstrip() + "\n" for line in lines)


def render(report, cache) -> str:
    return report.finish().write_to_string(cache)


def assert_snapshot(report, cache, expected: str):
    actual = remove_trailing(report.finish().write_to_string(cache)).rstrip("\n")
    assert actual == expected


def test_one_message():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("can't compare apples with oranges")
    )
    assert_snapshot(report, Source(""), SNAPSHOTS["one_message"])


def test_two_labels_without_messages():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("can't compare apples with oranges")
        .with_label(Label((0, 5)))
        .with_label(Label((9, 15)))
    )
    assert_snapshot(report, Source("apple == orange;"), SNAPSHOTS["two_labels_without_messages"])


def test_two_labels_without_messages_on_different_lines():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("can't compare apples with oranges")
        .with_label(Label((0, 5)))
        .with_label(Label((9, 15)))
    )
    assert_snapshot(
        report,
        Source("apple\n== orange;"),
        SNAPSHOTS["two_labels_without_messages_on_different_lines"],
    )


def test_two_labels_with_messages():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("can't compare apples with oranges")
        .with_label(Label((0, 5)).with_message("This is an apple"))
        .with_label(Label((9, 15)).with_message("This is an orange"))
    )
    assert_snapshot(report, Source("apple == orange;"), SNAPSHOTS["two_labels_with_messages"])


def test_two_labels_with_messages_on_different_lines():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("can't compare apples with oranges")
        .with_label(Label((0, 5)).with_message("This is an apple"))
        .with_label(Label((9, 15)).with_message("This is an orange"))
    )
    assert_snapshot(
        report,
        Source("apple ==\norange;"),
        SNAPSHOTS["two_labels_with_messages_on_different_lines"],
    )


def test_duplicate_label():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("can't compare apples with oranges")
        .with_label(Label((0, 5)).with_message("This is an apple"))
        .with_label(Label((0, 5)).with_message("This is an apple"))
    )
    assert_snapshot(report, Source("apple == orange;"), SNAPSHOTS["duplicate_label"])


def test_multi_byte_chars():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color().with_index_type(IndexType.CHAR))
        .with_message("can't compare äpplës with örängës")
        .with_label(Label((0, 5)).with_message("This is an äpplë"))
        .with_label(Label((9, 15)).with_message("This is an örängë"))
    )
    assert_snapshot(
        report,
        Source("äpplë == örängë;"),
        SNAPSHOTS["multi_byte_chars"],
    )


def test_byte_label():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color().with_index_type(IndexType.BYTE))
        .with_message("can't compare äpplës with örängës")
        .with_label(Label((0, 7)).with_message("This is an äpplë"))
        .with_label(Label((11, 20)).with_message("This is an örängë"))
    )
    assert_snapshot(report, Source("äpplë == örängë;"), SNAPSHOTS["byte_label"])


def test_byte_column():
    report = (
        Report.build(ReportKind.Error, (11, 11))
        .with_config(no_color().with_index_type(IndexType.BYTE))
        .with_message("can't compare äpplës with örängës")
        .with_label(Label((0, 7)).with_message("This is an äpplë"))
        .with_label(Label((11, 20)).with_message("This is an örängë"))
    )
    assert_snapshot(report, Source("äpplë == örängë;"), SNAPSHOTS["byte_column"])


def test_crossing_lines():
    report = (
        Report.build(ReportKind.Error, (11, 11))
        .with_config(no_color().with_cross_gap(False))
        .with_message("can't compare äpplës with örängës")
        .with_label(Label((0, 5)).with_message("This is an äpplë"))
        .with_label(Label((9, 15)).with_message("This is an örängë"))
    )
    actual = report.finish().write_to_string(Source("äpplë == örängë;"))
    # This test does not use remove_trailing in Rust.
    assert actual == SNAPSHOTS["crossing_lines"] + "\n"


def test_label_at_end_of_long_line():
    source = "apple == " * 100 + "orange"
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("can't compare apples with oranges")
        .with_label(Label((len(source) - 6, len(source))).with_message("This is an orange"))
    )
    assert_snapshot(report, Source(source), SNAPSHOTS["label_at_end_of_long_line"])


def test_label_of_width_zero_at_end_of_line():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color().with_index_type(IndexType.BYTE))
        .with_message("unexpected end of file")
        .with_label(Label((9, 9)).with_message("Unexpected end of file"))
    )
    assert_snapshot(report, Source("apple ==\n"), SNAPSHOTS["label_of_width_zero_at_end_of_line"])


def test_empty_input():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("unexpected end of file")
        .with_label(Label((0, 0)).with_message("No more fruit!"))
    )
    assert_snapshot(report, Source(""), SNAPSHOTS["empty_input"])


def test_empty_input_help():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("unexpected end of file")
        .with_label(Label((0, 0)).with_message("No more fruit!"))
        .with_help("have you tried going to the farmer's market?")
    )
    assert_snapshot(report, Source(""), SNAPSHOTS["empty_input_help"])


def test_empty_input_note():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("unexpected end of file")
        .with_label(Label((0, 0)).with_message("No more fruit!"))
        .with_note("eat your greens!")
    )
    assert_snapshot(report, Source(""), SNAPSHOTS["empty_input_note"])


def test_empty_input_help_note():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("unexpected end of file")
        .with_label(Label((0, 0)).with_message("No more fruit!"))
        .with_note("eat your greens!")
        .with_help("have you tried going to the farmer's market?")
    )
    assert_snapshot(report, Source(""), SNAPSHOTS["empty_input_help_note"])


def test_byte_spans_never_crash():
    source = "apple\np\n\nempty\n"
    for i in range(len(source) + 1):
        for j in range(i, len(source) + 1):
            report = (
                Report.build(ReportKind.Error, (0, 0))
                .with_config(no_color().with_index_type(IndexType.BYTE))
                .with_message("Label")
                .with_label(Label((i, j)).with_message("Label"))
            )
            report.finish().write_to_string(Source(source))


def test_multiline_label():
    source = "apple\n==\norange"
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_label(Label((0, len(source))).with_message("illegal comparison"))
    )
    assert_snapshot(report, Source(source), SNAPSHOTS["multiline_label"])


def test_multiple_multilines_same_span():
    source = "apple\n==\norange"
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_label(Label((0, len(source))).with_message("illegal comparison"))
        .with_label(Label((0, len(source))).with_message("do not do this"))
        .with_label(Label((0, len(source))).with_message("please reconsider"))
    )
    # This test does not use remove_trailing in Rust.
    actual = report.finish().write_to_string(Source(source))
    assert actual == SNAPSHOTS["multiple_multilines_same_span"] + "\n"


def test_multiline_label_show_6():
    source = "pear\napple\na\nb\nc\nd\norange\nbanana"
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_label(
            Label((5, 25))
            .with_message("illegal comparison")
            .with_show_lines(LabelShowLines.at_most(6))
        )
    )
    assert_snapshot(report, Source(source), SNAPSHOTS["multiline_label_show_6"])


def test_multiline_label_longer_than_max_span_line_count():
    source = "pear\napple\na\nb\nc\nd\norange\nbanana"
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_label(
            Label((5, len(source)))
            .with_message("illegal comparison")
            .with_show_lines(LabelShowLines.at_most(6))
        )
    )
    assert_snapshot(
        report,
        Source(source),
        SNAPSHOTS["multiline_label_longer_than_max_span_line_count"],
    )


def test_multiline_context_label():
    source = "apple\nbanana\ncarrot\ndragonfruit\negg\nfruit\ngrapes"
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color().with_context_lines(1))
        .with_label(Label((13, 35)).with_message("illegal comparison"))
    )
    assert_snapshot(report, Source(source), SNAPSHOTS["multiline_context_label"])


def test_partially_overlapping_labels():
    source = "https://example.com/"
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_label(Label((0, len(source))).with_message("URL"))
        .with_label(Label((0, source.find(":"))).with_message("scheme"))
    )
    assert_snapshot(report, Source(source), SNAPSHOTS["partially_overlapping_labels"])


def test_multiple_labels_same_span():
    source = "apple == orange;"
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("can't compare apples with oranges")
        .with_label(Label((0, 5)).with_message("This is an apple"))
        .with_label(Label((0, 5)).with_message("Have I mentioned that this is an apple?"))
        .with_label(Label((0, 5)).with_message("No really, have I mentioned that?"))
        .with_label(Label((9, 15)).with_message("This is an orange"))
        .with_label(Label((9, 15)).with_message("Have I mentioned that this is an orange?"))
        .with_label(Label((9, 15)).with_message("No really, have I mentioned that?"))
    )
    assert_snapshot(report, Source(source), SNAPSHOTS["multiple_labels_same_span"])


def test_note():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("can't compare apples with oranges")
        .with_label(Label((0, 5)).with_message("This is an apple"))
        .with_label(Label((9, 15)).with_message("This is an orange"))
        .with_note("stop trying ... this is a fruitless endeavor")
    )
    assert_snapshot(report, Source("apple == orange;"), SNAPSHOTS["note"])


def test_help():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("can't compare apples with oranges")
        .with_label(Label((0, 5)).with_message("This is an apple"))
        .with_label(Label((9, 15)).with_message("This is an orange"))
        .with_help("have you tried peeling the orange?")
    )
    assert_snapshot(report, Source("apple == orange;"), SNAPSHOTS["help"])


def test_help_and_note():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("can't compare apples with oranges")
        .with_label(Label((0, 5)).with_message("This is an apple"))
        .with_label(Label((9, 15)).with_message("This is an orange"))
        .with_help("have you tried peeling the orange?")
        .with_note("stop trying ... this is a fruitless endeavor")
    )
    assert_snapshot(report, Source("apple == orange;"), SNAPSHOTS["help_and_note"])


def test_single_note_single_line():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("can't compare apples with oranges")
        .with_label(Label((0, 15)).with_message("This is a strange comparison"))
        .with_note("No need to try, they can't be compared.")
    )
    assert_snapshot(report, Source("apple == orange;"), SNAPSHOTS["single_note_single_line"])


def test_multi_notes_single_lines():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("can't compare apples with oranges")
        .with_label(Label((0, 15)).with_message("This is a strange comparison"))
        .with_note("No need to try, they can't be compared.")
        .with_note("Yeah, really, please stop.")
    )
    assert_snapshot(report, Source("apple == orange;"), SNAPSHOTS["multi_notes_single_lines"])


def test_multi_notes_multi_lines():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("can't compare apples with oranges")
        .with_label(Label((0, 15)).with_message("This is a strange comparison"))
        .with_note("No need to try, they can't be compared.")
        .with_note("Yeah, really, please stop.\nIt has no resemblance.")
    )
    assert_snapshot(report, Source("apple == orange;"), SNAPSHOTS["multi_notes_multi_lines"])


def test_multi_helps_multi_lines():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message("can't compare apples with oranges")
        .with_label(Label((0, 15)).with_message("This is a strange comparison"))
        .with_help("No need to try, they can't be compared.")
        .with_help("Yeah, really, please stop.\nIt has no resemblance.")
    )
    assert_snapshot(report, Source("apple == orange;"), SNAPSHOTS["multi_helps_multi_lines"])


def test_ordered_labels():
    report = (
        Report.build(ReportKind.Error, ("", (0, 0)))
        .with_config(no_color())
        .with_label(Label(("b", (13, 18))).with_order(1).with_message("1"))
        .with_label(Label(("a", (0, 6))).with_order(2).with_message("2"))
        .with_label(Label(("a", (7, 12))).with_order(3).with_message("3"))
        .with_label(Label(("b", (0, 6))).with_order(4).with_message("4"))
        .with_label(Label(("b", (7, 12))).with_order(5).with_message("5"))
    )
    cache = sources({"a": "second\nthird", "b": "fourth\nfifth\nfirst"})
    assert_snapshot(report, cache, SNAPSHOTS["ordered_labels"])


def test_minimise_crossings():
    source = "begin\napple == orange;\nend"
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color().with_minimise_crossings(True))
        .with_message("can't compare apples with oranges")
        .with_label(Label((6, 11)).with_message("This is an apple"))
        .with_label(Label((15, 21)).with_message("This is an orange"))
        .with_label(Label((3, 25)).with_message("multi 1"))
        .with_label(Label((25, 26)).with_message("single"))
    )
    assert_snapshot(report, Source(source), SNAPSHOTS["minimise_crossings"])


def test_only_help_and_note():
    report = (
        Report.build(ReportKind.Error, (0, 0))
        .with_config(no_color())
        .with_message('Programming language "Rest" not found')
        .with_help("a language with a similar name exists: Rust")
        .with_note("perhaps you'd like some sleep?")
    )
    assert_snapshot(report, Source("this should not be printed"), SNAPSHOTS["only_help_and_note"])


def _multi_sources(texts):
    return FnCache(lambda id: texts[id])


def test_multi_source():
    report = (
        Report.build(ReportKind.Error, (0, (0, 0)))
        .with_config(no_color())
        .with_message("can't compare apples with oranges or pears")
        .with_label(Label((0, (0, 5))).with_message("This is an apple"))
        .with_label(Label((0, (9, 15))).with_message("This is an orange"))
        .with_label(Label((1, (0, 5))).with_message("This is an apple"))
        .with_label(Label((1, (9, 13))).with_message("This is a pear"))
    )
    assert_snapshot(
        report,
        _multi_sources(["apple == orange;", "apple == pear;"]),
        SNAPSHOTS["multi_source"],
    )


def test_help_and_note_multi():
    report = (
        Report.build(ReportKind.Error, (0, (0, 0)))
        .with_config(no_color())
        .with_message("can't compare apples with oranges or pears")
        .with_label(Label((0, (0, 5))).with_message("This is an apple"))
        .with_label(Label((0, (9, 15))).with_message("This is an orange"))
        .with_label(Label((1, (0, 5))).with_message("This is an apple"))
        .with_label(Label((1, (9, 13))).with_message("This is a pear"))
        .with_help("have you tried peeling the orange?")
        .with_note("stop trying ... this is a fruitless endeavor")
    )
    assert_snapshot(
        report,
        _multi_sources(["apple == orange;", "apple == pear;"]),
        SNAPSHOTS["help_and_note_multi"],
    )


def test_no_labels():
    report = (
        Report.build(ReportKind.Error, (0, (0, 0)))
        .with_config(no_color())
        .with_message("no code")
        .with_help("have you tried adding code?")
        .with_note("code needs to exist")
    )
    assert_snapshot(report, _multi_sources([]), SNAPSHOTS["no_labels"])

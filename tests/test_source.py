"""Port of the Rust crate's ``source/tests.rs``."""

import pytest

from ariadne_py import Line, Location, Source


def check_lines(lines):
    source = Source("".join(lines))
    source_lines = list(source.lines())
    assert len(source_lines) == len(lines)

    offset = 0
    for source_line, raw_line in zip(source_lines, lines):
        assert source_line.offset == offset
        assert source_line.char_len == len(raw_line)
        assert source.get_line_text(source_line) == raw_line
        offset += source_line.char_len
    assert source.len() == offset


def test_source_from_empty():
    check_lines([""])


def test_source_from_single():
    check_lines(["Single line"])
    check_lines(["Single line with LF\n"])
    check_lines(["Single line with CRLF\r\n"])


def test_source_from_multi():
    check_lines(["Two\r\n", "lines\n"])
    check_lines(["Some\n", "more\r\n", "lines"])
    check_lines(["\n", "\r\n", "\n", "Empty Lines"])


def test_source_from_trims_trailing_spaces():
    check_lines(["Trailing spaces  \n", "are trimmed\t"])


def test_source_from_alternate_line_endings():
    check_lines(
        ["CR\r", "VT\x0b", "FF\x0c", "NEL\u0085", "LS\u2028", "PS\u2029"]
    )


def test_source_other_string_types():
    raw = (
        "A raw string\n"
        "            with multiple\n"
        "            lines behind\n"
        "            an Arc"
    )
    source = Source(raw)
    assert len(list(source.lines())) == 4

    offset = 0
    for source_line, raw_line in zip(source.lines(), raw.splitlines(keepends=True)):
        assert source_line.offset == offset
        assert source_line.char_len == len(raw_line)
        assert source.get_line_text(source_line) == raw_line
        offset += source_line.char_len
    assert source.len() == offset


def test_get_offset_line():
    source = Source("a\nbb\nccc\n")
    loc = source.get_offset_line(0)
    assert loc.line_idx == 0
    assert loc.col_idx == 0
    loc = source.get_offset_line(2)
    assert loc.line_idx == 1
    assert loc.col_idx == 0
    loc = source.get_offset_line(4)
    assert loc.line_idx == 1
    assert loc.col_idx == 2
    assert source.get_offset_line(100) is None


def test_get_byte_line():
    source = Source("ä\nbb\n")
    # 'ä' is 2 bytes
    loc = source.get_byte_line(0)
    assert loc.line_idx == 0
    assert loc.col_idx == 0
    loc = source.get_byte_line(2)
    assert loc.line_idx == 0
    assert loc.col_idx == 2
    loc = source.get_byte_line(4)
    assert loc.line_idx == 1
    assert loc.col_idx == 1


def test_display_line_offset():
    source = Source("a\nb\n").with_display_line_offset(10)
    assert source.display_line_offset() == 10

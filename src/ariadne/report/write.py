"""The report rendering engine: a faithful port of ariadne's ``write.rs``."""

from __future__ import annotations

import io
import re
import sys
from itertools import chain

from ..config import AnsiMode, Config, IndexType
from ..draw import Fmt
from ..label import LabelAttach, LabelShowLines
from ..source import Source, as_cache
from ..span import UNIT
from .text import parse_tags, render_tags


_STRIP_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def _paint(text, style) -> str:
    if style is None:
        return str(text)
    return style.paint(text)


def _nb_digits(value: int) -> int:
    if value == 0:
        return 1
    return len(str(value))


def _not_usize(x: int) -> int:
    """Sort-key equivalent of Rust's bitwise-``!`` on usize."""
    return -(x + 1)


# Used to emulate Rust's bitwise-NOT-in-usize sort keys when mixed with plain
# usize values in a single tuple: `!x` is a huge positive number, so it must
# sort *after* any plain column index.
_NOT_BASE = 1 << 62


class _Writer:
    def __init__(self, stream, ansi_mode: AnsiMode):
        self._stream = stream
        self._strip = ansi_mode == AnsiMode.OFF

    def write(self, s: str) -> None:
        if self._strip:
            s = _STRIP_ANSI_RE.sub("", s)
        self._stream.write(s)


class _LabelInfo:
    __slots__ = ("kind", "char_span", "display_info", "start_line", "end_line")

    def __init__(self, kind, char_span, display_info, start_line, end_line):
        self.kind = kind  # "inline" | "multiline"
        self.char_span = char_span  # (start, end)
        self.display_info = display_info
        self.start_line = start_line
        self.end_line = end_line

    def last_offset(self) -> int:
        return max(self.char_span[1] - 1, self.char_span[0])

    def display_range(self, config: Config):
        return (
            max(0, self.start_line - config.context_lines),
            self.end_line + config.context_lines + 1,
        )

    def len(self) -> int:
        return self.char_span[1] - self.char_span[0]

    def contains(self, offset: int) -> bool:
        return self.char_span[0] <= offset < self.char_span[1]


class _SourceGroup:
    __slots__ = ("src_id", "char_span", "display_range", "labels")

    def __init__(self, src_id, char_span, display_range, labels):
        self.src_id = src_id
        self.char_span = char_span
        self.display_range = display_range
        self.labels = labels


class _LineLabel:
    __slots__ = ("col", "label", "multi", "draw_msg")

    def __init__(self, col, label, multi, draw_msg):
        self.col = col
        self.label = label
        self.multi = multi
        self.draw_msg = draw_msg

    def is_referencing(self, label: _LabelInfo) -> bool:
        return self.label is label


def _fetch_source(cache, src_id):
    src_name = _display_name(cache, src_id)
    try:
        return cache.fetch(src_id), src_name
    except Exception as err:  # noqa: BLE001 - mirrors Rust's Debug-printed error
        print(f"Unable to fetch source {src_name}: {err!r}", file=sys.stderr)
        return None


def _display_name(cache, src_id) -> str:
    try:
        display = cache.display(src_id)
    except Exception:
        display = None
    return str(display) if display is not None else "<unknown>"


def _max_line_num(groups) -> int:
    if not groups:
        return 0
    return max(_nb_digits(group.display_range[1]) for group in groups)


class Report:
    """A diagnostic that is ready to be written to output."""

    def __init__(self, builder):
        self.kind = builder.kind
        self.msg = builder.msg
        self.notes = builder.notes
        self.help = builder.help
        self.span = builder.span
        self.labels = builder.labels
        self.config = builder.config

    @classmethod
    def build(cls, kind, span):
        """Begin building a new report at the given primary span."""
        from .builder import ReportBuilder

        return ReportBuilder(kind, span)

    def _text(self, s: str) -> str:
        return render_tags(parse_tags(s), self.config)

    # --- source grouping ----------------------------------------------------

    def get_source_groups(self, cache):
        labels = []
        for label in self.labels:
            label_source = label.source()
            fetched = _fetch_source(cache, label_source)
            if fetched is None:
                continue
            src, _src_name = fetched

            given_span = (label.start(), label.end())

            if self.config.index_type == IndexType.CHAR:
                start_location = src.get_offset_line(given_span[0])
                if start_location is None:
                    continue
                if given_span[0] >= given_span[1]:
                    end_line = start_location.line_idx
                else:
                    end_location = src.get_offset_line(given_span[1] - 1)
                    if end_location is None:
                        continue
                    end_line = end_location.line_idx
                char_span = given_span
                start_line = start_location.line_idx
            else:  # IndexType.BYTE
                start_location = src.get_byte_line(given_span[0])
                if start_location is None:
                    continue
                line_text = src.get_line_text(start_location.line)
                line_bytes = line_text.encode("utf-8")
                num_chars_before_start = len(
                    line_bytes[: min(start_location.col_idx, len(line_bytes))].decode("utf-8")
                )
                start_char_offset = start_location.line.offset + num_chars_before_start
                if given_span[0] >= given_span[1]:
                    char_span = (start_char_offset, start_char_offset)
                    start_line = start_location.line_idx
                    end_line = start_location.line_idx
                else:
                    end_pos = given_span[1] - 1
                    end_location = src.get_byte_line(end_pos)
                    if end_location is None:
                        continue
                    end_line_text = src.get_line_text(end_location.line)
                    end_line_bytes = end_line_text.encode("utf-8")
                    num_chars_before_end = len(
                        end_line_bytes[: end_location.col_idx + 1].decode("utf-8")
                    )
                    end_char_offset = end_location.line.offset + num_chars_before_end
                    char_span = (start_char_offset, end_char_offset)
                    start_line = start_location.line_idx
                    end_line = end_location.line_idx

            label_info = _LabelInfo(
                kind="inline" if start_line == end_line else "multiline",
                char_span=char_span,
                display_info=label._display,
                start_line=start_line,
                end_line=end_line,
            )
            labels.append((label_info, label_source))

        labels.sort(key=lambda item: (item[0].display_info.order, item[0].end_line, item[0].start_line))

        groups = []
        for label, src_id in labels:
            if groups:
                last_group = groups[-1]
                last_label = last_group.labels[-1] if last_group.labels else None
                if (
                    last_group.src_id == src_id
                    and (last_label is None or last_label.end_line <= label.end_line)
                ):
                    last_group.char_span = (
                        min(last_group.char_span[0], label.char_span[0]),
                        max(last_group.char_span[1], label.char_span[1]),
                    )
                    display_range = label.display_range(self.config)
                    last_group.display_range = (
                        min(last_group.display_range[0], display_range[0]),
                        max(last_group.display_range[1], display_range[1]),
                    )
                    last_group.labels.append(label)
                    continue
            groups.append(
                _SourceGroup(
                    src_id=src_id,
                    char_span=tuple(label.char_span),
                    display_range=label.display_range(self.config),
                    labels=[label],
                )
            )
        return groups

    # --- public writing API -------------------------------------------------

    def write(self, cache, w) -> None:
        """Write this diagnostic to a text stream."""
        self._write_for_stream(as_cache(cache), w)

    def write_for_stdout(self, cache, w) -> None:
        """Write this diagnostic to a text stream (stdout variant)."""
        self._write_for_stream(as_cache(cache), w)

    def write_to_string(self, cache) -> str:
        """Render this diagnostic to a string (useful for testing)."""
        buf = io.StringIO()
        self._write_for_stream(as_cache(cache), buf)
        return buf.getvalue()

    def print(self, cache) -> None:
        """Write this diagnostic out to stdout."""
        self.write(cache, sys.stdout)
        sys.stdout.flush()

    def eprint(self, cache) -> None:
        """Write this diagnostic out to stderr."""
        self.write(cache, sys.stderr)
        sys.stderr.flush()

    # --- rendering ----------------------------------------------------------

    def _write_for_stream(self, cache, w) -> None:
        writer = _Writer(w, self.config.ansi_mode)
        draw = self.config.char_set

        # --- Header ---
        kind_style = self.kind.get_style(self.config)
        writer.write(_paint(str(self.kind), kind_style))
        msg = self._text(self.msg) if self.msg is not None else ""
        writer.write(f": {msg}\n")

        groups = self.get_source_groups(cache)
        line_num_width = _max_line_num(groups)

        margin_char = lambda c: _paint(c, self.config.margin_style())

        def write_margin(idx, is_src_line, is_ellipsis):
            if not groups:
                return
            if is_src_line and not is_ellipsis:
                line_num_margin = f"{idx + 1:>{line_num_width}} {draw.vbar}"
                writer.write(f" {_paint(line_num_margin, self.config.margin_style())} ")
            else:
                line_num_margin = " " * (line_num_width + 1) + draw.vbar_char(is_ellipsis)
                writer.write(
                    f" {_paint(line_num_margin, self.config.skipped_margin_style())} "
                )

        def write_spacer_line():
            if not self.config.compact:
                writer.write(
                    " " * (line_num_width + 2)
                    + _paint(draw.vbar, self.config.margin_style())
                    + "\n"
                )

        # --- Source sections ---
        for group_idx, group in enumerate(groups):
            fetched = _fetch_source(cache, group.src_id)
            if fetched is None:
                continue
            src, src_name = fetched

            if group.src_id == self.span[0]:
                location_offset = self.span[1]
                index_type = self.config.index_type
            else:
                location_offset = group.labels[0].char_span[0]
                index_type = IndexType.CHAR

            if index_type == IndexType.CHAR:
                location = src.get_offset_line(location_offset)
            else:
                byte_location = src.get_byte_line(location_offset)
                location = None
                if byte_location is not None:
                    line_text = src.get_line_text(byte_location.line)
                    line_bytes = line_text.encode("utf-8")
                    col = len(
                        line_bytes[: min(byte_location.col_idx, len(line_bytes))].decode(
                            "utf-8"
                        )
                    )
                    location = _LocationLike(
                        line=byte_location.line,
                        line_idx=byte_location.line_idx,
                        col_idx=col,
                    )

            if location is not None:
                location_str = (
                    f"{src_name}:{location.line_idx + 1 + src.display_line_offset()}:"
                    f"{location.col_idx + 1}"
                )
            else:
                location_str = ":?:?"

            corner_char = draw.ltop if group_idx == 0 else None
            if corner_char is None:
                write_spacer_line()
                corner_char = draw.lcross
            writer.write(_paint(" " * (line_num_width + 2), self.config.margin_style()))
            writer.write(margin_char(corner_char))
            writer.write(margin_char(draw.hbar))
            writer.write(margin_char(draw.lbox))
            writer.write(f" {location_str} ")
            writer.write(margin_char(draw.rbox))
            writer.write("\n")

            if not self.config.compact:
                write_spacer_line()

            # Multi-line labels with messages, sorted by descending span length
            multi_labels = [
                label for label in group.labels if label.kind == "multiline"
            ]
            multi_labels.sort(key=lambda l: -(l.len() + 1))
            multi_labels_with_message = [
                label for label in multi_labels if label.display_info.msg is not None
            ]

            if self.config.minimise_crossings:
                n_mls = len(multi_labels_with_message)
                for k in range(n_mls * n_mls * 2):
                    if n_mls <= 1:
                        break
                    j = k % (n_mls - 1)
                    a = multi_labels_with_message[j]
                    b = multi_labels_with_message[j + 1]
                    pro_a = int(a.char_span[0] < b.char_span[0]) + int(
                        a.char_span[1] > b.char_span[1]
                    )
                    pro_b = int(b.char_span[0] < a.char_span[0]) + int(
                        b.char_span[1] > a.char_span[1]
                    )
                    if pro_a < pro_b:
                        multi_labels_with_message[j], multi_labels_with_message[j + 1] = (
                            multi_labels_with_message[j + 1],
                            multi_labels_with_message[j],
                        )

            def write_margin_and_arrows(
                idx, is_src_line, is_ellipsis, report_row, line_labels, margin_label
            ):
                write_margin(idx, is_src_line, is_ellipsis)

                n_mls = len(multi_labels_with_message)
                for col in range(n_mls + (1 if multi_labels_with_message else 0)):
                    corner = None
                    hbar = None
                    vbar = None
                    margin_ptr = None

                    multi_label = multi_labels_with_message[col] if col < n_mls else None
                    line_span = src.line(idx).span()

                    for i, label in enumerate(
                        multi_labels_with_message[: min(col + 1, n_mls)]
                    ):
                        margin = (
                            margin_label
                            if margin_label is not None
                            and margin_label.is_referencing(label)
                            else None
                        )

                        if (
                            label.char_span[0] < line_span[1]
                            and label.char_span[1] > line_span[0]
                        ):
                            is_parent = i != col
                            is_start = line_span[0] <= label.char_span[0] < line_span[1]
                            is_end = line_span[0] <= label.last_offset() < line_span[1]

                            if margin is not None and is_src_line:
                                margin_ptr = (margin, is_start)
                            elif not is_start and (not is_end or is_src_line):
                                if not is_parent:
                                    vbar = vbar or label
                            elif report_row is not None:
                                report_row_idx, is_arrow = report_row
                                label_row = 0
                                for r, ll in enumerate(line_labels):
                                    if ll.is_referencing(label):
                                        label_row = r
                                        break
                                if report_row_idx == label_row:
                                    if margin is not None:
                                        vbar = margin.label if col == i else None
                                        if is_start:
                                            continue
                                    if is_arrow:
                                        hbar = label
                                        if not is_parent:
                                            corner = (label, is_start)
                                    elif not is_start:
                                        if not is_parent:
                                            vbar = vbar or label
                                else:
                                    if (
                                        not is_parent
                                        and (is_start != (report_row_idx < label_row))
                                    ):
                                        vbar = vbar or label

                            if (
                                margin_label is not None
                                and margin_label.is_referencing(label)
                                and is_end
                                and is_src_line
                                and col > i
                            ):
                                hbar = margin_label.label

                    if margin_ptr is not None and is_src_line:
                        margin, _is_start = margin_ptr
                        is_col = (
                            multi_label is not None and margin.is_referencing(multi_label)
                        )
                        is_limit = col + 1 == n_mls
                        if not is_col and not is_limit:
                            hbar = hbar or margin.label

                    if corner is not None:
                        label, is_start = corner
                        a = (draw.arrow_bend(is_start), label)
                        b = (draw.hbar, label)
                    elif vbar is not None and hbar is not None:
                        a = (draw.vbar if self.config.cross_gap else draw.xbar, vbar)
                        b = (draw.hbar, hbar)
                    elif margin_ptr is not None and is_src_line:
                        margin, is_start = margin_ptr
                        is_col = (
                            multi_label is not None and margin.is_referencing(multi_label)
                        )
                        is_limit = col == n_mls
                        if is_limit:
                            a_char = (
                                draw.rarrow if self.config.multiline_arrows else draw.hbar
                            )
                        elif is_col:
                            a_char = draw.ltop if is_start else draw.lcross
                        else:
                            a_char = draw.hbar
                        a = (a_char, margin.label)
                        b = (" " if is_limit else draw.hbar, margin.label)
                    elif hbar is not None:
                        a = (draw.hbar, hbar)
                        b = (draw.hbar, hbar)
                    elif vbar is not None:
                        a = (draw.vbar_char(is_ellipsis), vbar)
                        b = None
                    else:
                        a = None
                        b = None

                    def arrow_char(opt):
                        if opt is None:
                            return " "
                        c, label = opt
                        return _paint(c, label.display_info.get_style(self.config))

                    writer.write(arrow_char(a))
                    if not self.config.compact:
                        writer.write(arrow_char(b))

            is_ellipsis = False
            for idx in range(group.display_range[0], group.display_range[1]):
                line = src.line(idx)
                if line is None:
                    continue

                # The (optional) label whose arrows are drawn in the margin
                margin_candidates = []
                for i, label in enumerate(multi_labels_with_message):
                    is_start = line.contains(label.char_span[0])
                    is_end = line.contains(label.last_offset())
                    if is_start:
                        margin_candidates.append(
                            _LineLabel(
                                col=label.char_span[0] - line.offset,
                                label=label,
                                multi=i,
                                draw_msg=False,
                            )
                        )
                    elif is_end:
                        margin_candidates.append(
                            _LineLabel(
                                col=label.last_offset() - line.offset,
                                label=label,
                                multi=i,
                                draw_msg=True,
                            )
                        )
                margin_label = (
                    min(
                        margin_candidates,
                        key=lambda ll: (ll.col, _not_usize(ll.label.char_span[0])),
                    )
                    if margin_candidates
                    else None
                )

                def is_margin_label(label):
                    return (
                        margin_label is not None and margin_label.is_referencing(label)
                    )

                # Generate the list of labels for this line
                line_labels = []
                for i, label in enumerate(multi_labels_with_message):
                    is_start = line.contains(label.char_span[0])
                    is_end = line.contains(label.last_offset())
                    if is_start and not is_margin_label(label):
                        line_labels.append(
                            _LineLabel(
                                col=label.char_span[0] - line.offset,
                                label=label,
                                multi=i,
                                draw_msg=False,
                            )
                        )
                    elif is_end:
                        line_labels.append(
                            _LineLabel(
                                col=label.last_offset() - line.offset,
                                label=label,
                                multi=i,
                                draw_msg=True,
                            )
                        )
                for label_info in group.labels:
                    if (
                        label_info.kind == "inline"
                        and label_info.char_span[0] >= line.span()[0]
                        and label_info.char_span[1] <= line.span()[1]
                    ):
                        if self.config.label_attach == LabelAttach.START:
                            attach = label_info.char_span[0]
                        elif self.config.label_attach == LabelAttach.MIDDLE:
                            attach = (label_info.char_span[0] + label_info.char_span[1]) // 2
                        else:
                            attach = label_info.last_offset()
                        line_labels.append(
                            _LineLabel(
                                col=max(attach, label_info.char_span[0]) - line.offset,
                                label=label_info,
                                multi=None,
                                draw_msg=True,
                            )
                        )

                # Skip this line if it has no labels and no context relevance
                far_from_labels = all(
                    min(
                        abs(l.start_line - idx),
                        abs(l.end_line - idx),
                    )
                    > self.config.context_lines
                    for l in group.labels
                )
                if not line_labels and margin_label is None and far_from_labels:
                    within_label = any(
                        label.contains(line.span()[0]) for label in multi_labels
                    )
                    if not is_ellipsis and within_label:
                        should_show = False
                        for label in multi_labels:
                            if label.contains(line.span()[0]):
                                sl = label.display_info.show_lines
                                if sl.is_all or (label.end_line - label.start_line) < sl.value:
                                    should_show = True
                                    break
                        if not should_show:
                            is_ellipsis = True
                    else:
                        if not self.config.compact and not is_ellipsis:
                            write_margin(idx, False, is_ellipsis)
                            writer.write("\n")
                        is_ellipsis = True
                        continue
                else:
                    is_ellipsis = False

                # Sort labels by their columns
                def line_label_key(ll):
                    if self.config.minimise_crossings and ll.multi is not None:
                        multi_key = (
                            _NOT_BASE - ll.multi if ll.draw_msg else ll.multi
                        )
                    else:
                        multi_key = None
                    if self.config.minimise_crossings != ll.draw_msg:
                        col_key = ll.col
                    else:
                        col_key = _NOT_BASE - ll.col
                    return (
                        ll.label.display_info.order,
                        multi_key is not None,
                        multi_key if multi_key is not None else 0,
                        col_key,
                        _not_usize(ll.label.char_span[0]),
                    )

                line_labels.sort(key=line_label_key)

                arrow_end_space = 1 if self.config.compact else 2
                arrow_len = 0
                for ll in line_labels:
                    if ll.multi is not None:
                        arrow_len = max(arrow_len, line.len())
                    else:
                        arrow_len = max(
                            arrow_len,
                            max(0, ll.label.char_span[1] - line.offset),
                        )
                arrow_len += arrow_end_space

                def get_vbar(col, row):
                    for j, ll in enumerate(line_labels):
                        if (
                            ll.label.display_info.msg is not None
                            and not is_margin_label(ll.label)
                            and ll.col == col
                            and row <= j
                        ):
                            return ll
                    return None

                def get_highlight(col):
                    offset = line.offset + col
                    best = None
                    best_key = None
                    labels_iter = chain(
                        (margin_label.label,) if margin_label is not None else (),
                        multi_labels,
                        (ll.label for ll in line_labels),
                    )
                    for l in labels_iter:
                        if l.contains(offset):
                            key = (-l.display_info.priority, l.len())
                            if best_key is None or key < best_key:
                                best_key = key
                                best = l
                    return best

                def get_underline(col):
                    if not self.config.underlines:
                        return None
                    offset = line.offset + col
                    best = None
                    best_key = None
                    for ll in line_labels:
                        if ll.multi is None and ll.label.contains(offset):
                            l = ll.label
                            key = (-l.display_info.priority, l.len())
                            if best_key is None or key < best_key:
                                best_key = key
                                best = l
                    return best

                # Margin
                write_margin_and_arrows(
                    idx, True, is_ellipsis, None, line_labels, margin_label
                )

                # Line
                if not is_ellipsis:
                    line_text = src.get_line_text(line).rstrip()
                    for col, c in enumerate(line_text):
                        highlight = get_highlight(col)
                        if highlight is not None:
                            style = highlight.display_info.get_style(self.config)
                        else:
                            style = self.config.unimportant_style()
                        c, width = self.config.char_width(c, col)
                        painted = _paint(c, style)
                        if c.isspace():
                            for _ in range(width):
                                writer.write(painted)
                        else:
                            writer.write(painted)
                writer.write("\n")

                # Arrows
                for row, line_label in enumerate(line_labels):
                    if row == 0 or (
                        line_label.label.display_info.msg is not None
                        and not self.config.compact
                    ):
                        # Margin alternate
                        write_margin_and_arrows(
                            idx,
                            False,
                            is_ellipsis,
                            (row, False),
                            line_labels,
                            margin_label,
                        )
                        # Lines alternate
                        line_chars = iter(src.get_line_text(line).rstrip())
                        for col in range(arrow_len):
                            nxt = next(line_chars, None)
                            width = 1 if nxt is None else self.config.char_width(nxt, col)[1]

                            vbar = get_vbar(col, row)
                            underline = get_underline(col) if row == 0 else None
                            if vbar is not None:
                                if underline is not None:
                                    span_len = (
                                        vbar.label.char_span[1] - vbar.label.char_span[0]
                                    )
                                    if span_len <= 1:
                                        c, tail = draw.underbar_single, draw.underline
                                    elif line.offset + col == vbar.label.char_span[0]:
                                        c, tail = draw.lunderbar, draw.munderbar
                                    elif line.offset + col == vbar.label.last_offset():
                                        c, tail = draw.runderbar, draw.munderbar
                                    else:
                                        c, tail = draw.munderbar, draw.underline
                                elif (
                                    vbar.multi is not None
                                    and row == 0
                                    and self.config.multiline_arrows
                                ):
                                    c, tail = draw.uarrow, " "
                                else:
                                    c, tail = draw.vbar, " "
                                vbar_style = vbar.label.display_info.get_style(self.config)
                                c_painted = _paint(c, vbar_style)
                                tail_painted = _paint(tail, vbar_style)
                            elif underline is not None:
                                underline_style = underline.display_info.get_style(
                                    self.config
                                )
                                c_painted = _paint(draw.underline, underline_style)
                                tail_painted = _paint(draw.underline, underline_style)
                            else:
                                c_painted = " "
                                tail_painted = " "

                            for i in range(width):
                                writer.write(c_painted if i == 0 else tail_painted)
                        writer.write("\n")

                    # No message to draw, thus no arrow to draw
                    if line_label.label.display_info.msg is None:
                        continue

                    # Margin
                    write_margin_and_arrows(
                        idx,
                        False,
                        is_ellipsis,
                        (row, True),
                        line_labels,
                        margin_label,
                    )
                    # Lines
                    line_chars = iter(src.get_line_text(line).rstrip())
                    for col in range(arrow_len):
                        nxt = next(line_chars, None)
                        width = 1 if nxt is None else self.config.char_width(nxt, col)[1]

                        is_hbar = (
                            (
                                (col > line_label.col)
                                != (line_label.multi is not None)
                            )
                            or (
                                line_label.label.display_info.msg is not None
                                and line_label.draw_msg
                                and col > line_label.col
                            )
                        ) and line_label.label.display_info.msg is not None

                        label_style = line_label.label.display_info.get_style(self.config)
                        if (
                            col == line_label.col
                            and line_label.label.display_info.msg is not None
                            and not is_margin_label(line_label.label)
                        ):
                            if line_label.multi is not None:
                                c = draw.mbot if line_label.draw_msg else draw.rbot
                            else:
                                c = draw.lbot
                            c_painted = _paint(c, label_style)
                            tail_painted = _paint(draw.hbar, label_style)
                        elif get_vbar(col, row) is not None and (
                            col != line_label.col
                            or line_label.label.display_info.msg is not None
                        ):
                            vbar_ll = get_vbar(col, row)
                            vbar_style = vbar_ll.label.display_info.get_style(self.config)
                            if not self.config.cross_gap and is_hbar:
                                c_painted = _paint(draw.xbar, vbar_style)
                                tail_painted = _paint(" ", label_style)
                            else:
                                c_painted = _paint(draw.vbar, vbar_style)
                                tail_painted = _paint(" ", label_style)
                        elif is_hbar:
                            c_painted = _paint(draw.hbar, label_style)
                            tail_painted = _paint(draw.hbar, label_style)
                        else:
                            c_painted = " "
                            tail_painted = " "

                        if width > 0:
                            writer.write(c_painted)
                        for _ in range(1, width):
                            writer.write(tail_painted)
                    if line_label.draw_msg:
                        writer.write(" ")
                        writer.write(self._text(line_label.label.display_info.msg))
                    writer.write("\n")

        # Help
        for i, help in enumerate(self.help):
            if not self.config.compact and i == 0:
                write_margin(0, False, False)
                writer.write("\n")
            help_prefix = (
                f"Help {i + 1}"
                if len(self.help) > 1 and self.config.enumerate_helps
                else "Help"
            )
            lines = help.split("\n")
            if lines:
                write_margin(0, False, False)
                writer.write(_paint(help_prefix, self.config.note_style()))
                writer.write(f": {lines[0]}\n")
            for line in lines[1:]:
                write_margin(0, False, False)
                writer.write(f"{'':>{len(help_prefix) + 2}}{line}\n")

        # Notes
        for i, note in enumerate(self.notes):
            if not self.config.compact and i == 0:
                write_margin(0, False, False)
                writer.write("\n")
            note_prefix = (
                f"Note {i + 1}"
                if len(self.notes) > 1 and self.config.enumerate_notes
                else "Note"
            )
            lines = note.split("\n")
            if lines:
                write_margin(0, False, False)
                writer.write(_paint(note_prefix, self.config.note_style()))
                writer.write(f": {lines[0]}\n")
            for line in lines[1:]:
                write_margin(0, False, False)
                writer.write(f"{'':>{len(note_prefix) + 2}}{line}\n")

        # Tail of report
        if not (self.config.compact or not groups):
            writer.write(
                _paint(
                    draw.hbar * (line_num_width + 2) + draw.rbot,
                    self.config.margin_style(),
                )
            )
            writer.write("\n")


class _LocationLike:
    """Small stand-in for :class:`Location` used during byte-column conversion."""

    __slots__ = ("line", "line_idx", "col_idx")

    def __init__(self, line, line_idx, col_idx):
        self.line = line
        self.line_idx = line_idx
        self.col_idx = col_idx

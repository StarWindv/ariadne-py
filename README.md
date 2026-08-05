# ariadne-py

A Python port of the [`ariadne`](https://crates.io/crates/ariadne) 0.7.0 fancy
compiler-diagnostics crate. The public API and rendered output mirror the Rust
crate: `use ariadne::{...}` becomes `from ariadne_py import ...`, spans like
`0..5` become `(0, 5)` tuples, and `Label::new(...)` becomes `Label(...)`.

## Example

```python
from ariadne_py import Label, Report, ReportKind, Source

Report.build(
    ReportKind.Error, (34, 34)
).with_message("Incompatible types") \
    .with_label(Label((32, 33)).with_message("This is of type Nat")) \
    .with_label(Label((52, 55)).with_message("This is of type Str")) \
    .finish() \
    .print(Source(sample))
```

## Feature parity

- `Report` / `ReportBuilder` with the full builder API (`with_message`,
  `with_note`, `with_help`, `with_label`, `with_config`, ...) and
  `print` / `eprint` / `write` / `write_to_string`.
- `ReportKind` (`Error`, `Warning`, `Advice`, `custom(name, color)`),
  `BasicStyle` and custom report styles.
- `Label` with `with_message`, `with_color`, `with_style`, `with_order`,
  `with_priority`, `with_show_lines`; `LabelAttach`, `LabelShowLines`.
- Spans: `(start, end)` for unit sources, `(source_id, (start, end))` for named
  sources, `range`/`slice` objects, or any object with `source()`, `start()`,
  `end()`.
- `Source` (with the same line splitting, including CRLF handling and the
  alternative Unicode line separators), `Line`, `Location`, `Cache`,
  `FileCache`, `FnCache`, `sources(...)`.
- `Config` with every `with_*` option: `cross_gap`, `label_attach`, `compact`,
  `underlines`, `multiline_arrows`, `color`, `tab_width`, `char_set`,
  `index_type` (char or byte spans), `minimise_crossings`, `context_lines`,
  `ansi_mode`, `enumerate_notes`, `enumerate_helps`, `report_style`, and named
  `with_style` entries.
- `Characters` (Unicode and ASCII character sets), `Color` / `Style`
  (a faithful `yansi`-compatible ANSI emulation), and `ColorGenerator` with
  bit-identical color sequences to the Rust crate.
- Formatting helpers: `Fmt.fg(text, color)` / `Fmt.bg(text, color)` (Rust:
  `"text".fg(color)`), `Styleable.style(text, name)` (Rust: `"text".style(name)`).

## Testing

The test suite is byte-for-byte compatible with the Rust crate:

- `tests/test_report.py` ports all 37 insta snapshot tests from the Rust
  source (expected strings are extracted verbatim from `report/tests.rs`).
- `tests/test_examples.py` compares the five crate examples
  (`simple`, `labels`, `multifile`, `multiline`, `stresstest`) byte-for-byte
  against captured Rust output, including full ANSI escape sequences.
- `tests/test_source.py`, `tests/test_misc.py` cover line indexing, caches,
  colours and configuration.

```sh
python -m pytest tests
```


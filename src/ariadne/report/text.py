"""Parsing and rendering of in-line style tags (the ``Styleable`` format)."""

from __future__ import annotations

from ..config import Config

TAG_START = "\x13"
TAG_END = "\x11"


def parse_tags(s: str):
    """Parse tagged text into a list of ``("text", str)`` / ``("tagged", name, children)``.

    Faithful port of ``Text::parse`` including its handling of malformed tags.
    """
    open_tags = [("", [])]
    plain_start = 0
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == TAG_START:
            open_tags[-1][1].append(("text", s[plain_start:i]))
            i += 1
            tag_start = i
            while i < n:
                if s[i] == TAG_END:
                    tag = s[tag_start:i]
                    if tag.startswith("@{"):
                        open_tags.append((tag[2:], []))
                    elif tag == "@}":
                        t, children = open_tags.pop()
                        open_tags[-1][1].append(("tagged", t, children))
                    else:
                        # Any other tag contents get ignored to maximise compatibility
                        open_tags[-1][1].pop()
                        i += 1
                        break
                    i += 1
                    plain_start = i
                    break
                else:
                    i += 1
        else:
            i += 1
    open_tags[-1][1].append(("text", s[plain_start:i]))
    return open_tags.pop()[1]


def render_tags(ts, config: Config) -> str:
    out = []
    for t in ts:
        if t[0] == "text":
            out.append(t[1])
        else:
            style = config.get_style(t[1])
            out.append(style.paint(render_tags(t[2], config)))
    return "".join(out)

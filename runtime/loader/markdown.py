"""The runtime's only Markdown parser.

Per ADR 0004, all Markdown parsing lives behind the Project Loader. If a second
module in this runtime starts splitting headings or matching list items, that
is a defect -- the fix is to extend what the Loader returns, not to parse again
somewhere else.

Scope is deliberately tiny: split a document into sections, and read simple
labelled values out of a section body. Nothing here understands config,
knowledge, or any framework concept. Meaning is applied one layer up, in
`config_parser`, so this stays a pure text utility.
"""

from __future__ import annotations

import re

# A setext-free subset: only ATX headings ("## Title") are recognised, which is
# what every template and project in the framework uses.
_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})[ \t]+(?P<title>.*\S)[ \t]*$", re.MULTILINE)

# "- **Label:** value" / "* **Label:** value"
_LABELLED_ITEM_RE = re.compile(
    r"^[ \t]*[-*+][ \t]+\*\*(?P<label>[^*]+?)\*\*[ \t]*:?[ \t]*(?P<value>.*)$",
    re.MULTILINE,
)

# "- item" / "* item" / "+ item"
_LIST_ITEM_RE = re.compile(r"^[ \t]*[-*+][ \t]+(?P<item>.*\S)[ \t]*$", re.MULTILINE)

# `inline code`
_CODE_SPAN_RE = re.compile(r"`(?P<code>[^`]+)`")


def normalise_heading(title: str) -> str:
    """Canonical lookup form for a heading: no hashes, no case, no padding."""
    return title.strip().lstrip("#").strip().casefold()


def split_sections(text: str) -> tuple[tuple[str, str], ...]:
    """Split Markdown into ``(normalised heading, body)`` pairs, in order.

    Content appearing before the first heading is discarded: it belongs to no
    section, and inventing a synthetic one would create a heading that does not
    exist in the document.

    Order is preserved and duplicates are kept, so callers decide how to handle
    a repeated heading rather than having the parser silently choose.
    """
    matches = list(_HEADING_RE.finditer(text))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((normalise_heading(match.group("title")), text[start:end].strip()))
    return tuple(sections)


def strip_inline_markup(value: str) -> str:
    """Remove emphasis/code markers and surrounding punctuation from a value."""
    return value.replace("*", "").replace("`", "").strip(" \t.:-")


def labelled_values(body: str) -> tuple[tuple[str, str], ...]:
    """Extract ``- **Label:** value`` pairs from a section body.

    Returns label and value with inline markup stripped, in document order.
    An empty value is returned as an empty string, distinct from the label
    being absent altogether -- the caller needs that distinction.
    """
    found: list[tuple[str, str]] = []
    for match in _LABELLED_ITEM_RE.finditer(body):
        label = strip_inline_markup(match.group("label"))
        value = strip_inline_markup(match.group("value"))
        if label:
            found.append((label, value))
    return tuple(found)


def list_items(body: str) -> tuple[str, ...]:
    """Every bullet item in a section body, in document order."""
    return tuple(
        item
        for item in (match.group("item").strip() for match in _LIST_ITEM_RE.finditer(body))
        if item
    )


def code_spans(body: str) -> tuple[str, ...]:
    """Every `inline code` span in a section body, in document order."""
    return tuple(match.group("code").strip() for match in _CODE_SPAN_RE.finditer(body))


def leading_label(item: str) -> str:
    """The label portion of a list item, dropping any trailing description.

    Handles the shapes the framework's own templates use:
        "**Discovery** -- understand the need"  -> "Discovery"
        "Discovery - understand the need"       -> "Discovery"
        "Discovery"                             -> "Discovery"
    """
    bold = re.match(r"^[ \t]*\*\*(?P<label>[^*]+?)\*\*", item)
    if bold:
        return strip_inline_markup(bold.group("label"))
    head = re.split(r"\s+[—–-]{1,2}\s+", item, maxsplit=1)[0]
    return strip_inline_markup(head)

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
from typing import NamedTuple

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


class ParsedSection(NamedTuple):
    """One heading occurrence and the body that follows it.

    `heading` is the **original text, verbatim** -- not normalised and not
    casefolded. `normalise_heading` exists for lookup, never for storage: an
    earlier revision stored the normalised form and the original capitalisation
    became unrecoverable.
    """

    level: int
    heading: str
    body: str


class ParsedDocument(NamedTuple):
    """A document split into its preamble and every heading occurrence.

    Lossless with respect to content: every heading occurrence is a separate
    entry, so a repeated heading yields repeated entries rather than one
    surviving winner. Callers decide how to handle repetition; this parser never
    silently chooses.
    """

    preamble: str
    sections: tuple[ParsedSection, ...]


def split_sections(text: str) -> ParsedDocument:
    """Split Markdown into its preamble and ordered heading occurrences.

    Preserves, for every occurrence: the original heading text, the heading
    level (the `#` count), the body, document order, and repetition. Content
    appearing before the first heading is returned as `preamble` rather than
    discarded -- an earlier revision dropped it, which silently lost any
    document that opened with prose.

    The only normalisation applied is `.strip()` on bodies and preamble, which
    this parser already applied and which the Prompt Assembler independently
    applies when rendering. Nothing else about the text is altered.
    """
    matches = list(_HEADING_RE.finditer(text))
    preamble = (text[: matches[0].start()] if matches else text).strip()

    sections: list[ParsedSection] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append(
            ParsedSection(
                level=len(match.group("hashes")),
                heading=match.group("title"),
                body=text[start:end].strip(),
            )
        )
    return ParsedDocument(preamble=preamble, sections=tuple(sections))


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

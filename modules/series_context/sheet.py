"""Turn raw series metadata into a short, spoiler-lean "series sheet".

The sheet is injected into the LLM's ``extra_context`` so that translations get
the right tone, register, names and pronoun genders.

Spoiler policy (best effort, and documented honestly: public metadata APIs do
not expose *per-chapter* information, so we cannot tailor a sheet to a given
chapter):

* text the source marks as a spoiler (AniList ``~!...!~``) is removed;
* tags flagged as spoilers by the source are dropped;
* only the opening of the synopsis is kept (the premise), never cut mid-sentence;
* only MAIN characters are listed, with no role or plot information;
* the result is shown to the user for review before it is used.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

DEFAULT_MAX_CHARS = 1000  # matches LlmsPage.DEFAULT_EXTRA_CONTEXT_LIMIT

_SPOILER_BLOCK = re.compile(r"~!.*?!~", re.S)
_HTML_BR = re.compile(r"<br\s*/?>", re.I)
_HTML_TAG = re.compile(r"<[^>]+>")
_SOURCE_NOTE = re.compile(r"\((?:source|written by)[^)]*\)", re.I)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…。！？])\s+")

_LABELS = {
    "fr": {
        "series": "Série",
        "genres": "Genres",
        "themes": "Thèmes",
        "characters": "Personnages principaux",
        "premise": "Prémisse (début de l'histoire)",
        "note": "Utilise ces infos pour le ton, le registre, les noms et le genre des personnages.",
        "native": "orig.",
    },
    "en": {
        "series": "Series",
        "genres": "Genres",
        "themes": "Themes",
        "characters": "Main characters",
        "premise": "Premise (start of the story)",
        "note": "Use this for tone, register, names and characters' genders.",
        "native": "orig.",
    },
}


@dataclass
class Character:
    name: str
    native: str = ""
    gender: str = ""  # "M", "F" or ""


@dataclass
class SeriesInfo:
    title: str
    native_title: str = ""
    genres: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)  # already spoiler-filtered
    description: str = ""
    characters: list[Character] = field(default_factory=list)
    source: str = ""
    # True only when the source marks spoilers itself and we stripped them.
    spoiler_safe: bool = False


def clean_description(raw: str | None) -> str:
    """Strip spoiler blocks, markup and boilerplate from a synopsis."""
    text = raw or ""
    text = _SPOILER_BLOCK.sub("", text)
    # An unterminated spoiler marker (truncated text): drop everything after it.
    text = text.split("~!")[0]
    text = _HTML_BR.sub("\n", text)
    text = _HTML_TAG.sub("", text)
    text = html.unescape(text)
    text = _SOURCE_NOTE.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text.strip()


def premise(text: str, max_chars: int) -> str:
    """Keep the opening sentences of ``text`` within ``max_chars``.

    Never cuts mid-sentence unless even the first sentence is too long, in which
    case it is cut at a word boundary and ends with an ellipsis.
    """
    if max_chars <= 0 or not text:
        return ""
    flat = re.sub(r"\s+", " ", text).strip()
    kept: list[str] = []
    used = 0
    for sentence in _SENTENCE_SPLIT.split(flat):
        extra = len(sentence) + (1 if kept else 0)
        if used + extra > max_chars:
            break
        kept.append(sentence)
        used += extra
    if kept:
        return " ".join(kept)
    cut = flat[: max(0, max_chars - 1)].rsplit(" ", 1)[0].rstrip(",;:- ")
    return f"{cut}…" if cut else ""


def _character_text(c: Character, native_label: str) -> str:
    extras = []
    if c.native and c.native != c.name:
        extras.append(f"{native_label} {c.native}")
    if c.gender:
        extras.append(c.gender)
    return f"{c.name} ({', '.join(extras)})" if extras else c.name


def format_sheet(info: SeriesInfo, lang: str = "fr", max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Render ``info`` as plain text of at most ``max_chars`` characters."""
    lb = _LABELS.get(lang, _LABELS["en"])

    title = info.title
    if info.native_title and info.native_title != info.title:
        title = f"{info.title} ({info.native_title})"

    header = f"{lb['series']} : {title}"
    genres = f"{lb['genres']} : {', '.join(info.genres[:5])}" if info.genres else ""
    themes = f"{lb['themes']} : {', '.join(info.themes[:5])}" if info.themes else ""
    chars = ""
    if info.characters:
        chars = f"{lb['characters']} : " + "; ".join(
            _character_text(c, lb["native"]) for c in info.characters[:6]
        )

    def assemble(parts: list[str], premise_text: str, note: bool) -> str:
        lines = [p for p in parts if p]
        if premise_text:
            lines.append(f"{lb['premise']} : {premise_text}")
        if note:
            lines.append(lb["note"])
        return "\n".join(lines)

    # Fixed parts first; the premise takes whatever budget is left. If the fixed
    # parts alone are too long, shed the least useful pieces in order.
    parts = [header, genres, themes, chars]
    note = True
    for drop in (None, "note", "themes", "genres"):
        if drop == "note":
            note = False
        elif drop == "themes":
            parts[2] = ""
        elif drop == "genres":
            parts[1] = ""
        fixed = assemble(parts, "", note)
        label_cost = len(f"\n{lb['premise']} : ")
        room = max_chars - len(fixed) - label_cost
        if room >= 60 or drop == "genres":
            break

    body = premise(info.description, room)
    text = assemble(parts, body, note)
    if len(text) > max_chars:  # last resort for pathological titles/names
        text = text[: max_chars - 1].rstrip() + "…"
    return text

"""Look up a manga/manhwa/webtoon on public metadata APIs.

Providers: AniList (GraphQL, no key needed) and MangaDex (REST, no key needed).
AniList is preferred because it marks spoilers itself, which lets us strip them.

All network access goes through an injectable ``http`` callable so the logic can
be tested without a connection:

    http(method, url, **kwargs) -> parsed JSON (dict)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

from .sheet import Character, SeriesInfo, clean_description

ANILIST_URL = "https://graphql.anilist.co"
MANGADEX_URL = "https://api.mangadex.org"
USER_AGENT = "comic-translate-series-search/1.0"
TIMEOUT = 10

Http = Callable[..., dict]


class SeriesSearchError(Exception):
    """Raised with a user-presentable message when a lookup fails."""


@dataclass
class Candidate:
    source: str  # "anilist" | "mangadex"
    id: str
    title: str
    native_title: str = ""
    year: int | None = None
    country: str = ""

    def label(self) -> str:
        bits = [self.title]
        if self.native_title and self.native_title != self.title:
            bits.append(f"({self.native_title})")
        meta = [m for m in (str(self.year) if self.year else "", self.country, self.source) if m]
        return " ".join(bits) + (f" — {' · '.join(meta)}" if meta else "")


def _default_http(method: str, url: str, **kwargs: Any) -> dict:
    import requests  # imported lazily: only needed for real network calls

    headers = {"User-Agent": USER_AGENT, **kwargs.pop("headers", {})}
    try:
        resp = requests.request(method, url, headers=headers, timeout=TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise SeriesSearchError(f"Network error: {exc}") from exc
    except ValueError as exc:
        raise SeriesSearchError("The server returned an unreadable response.") from exc


# ----------------------------------------------------------------- AniList
_ANILIST_SEARCH = """
query ($search: String) {
  Page(perPage: 8) {
    media(search: $search, type: MANGA, sort: SEARCH_MATCH) {
      id
      title { romaji english native }
      startDate { year }
      countryOfOrigin
    }
  }
}
"""

_ANILIST_DETAIL = """
query ($id: Int) {
  Media(id: $id, type: MANGA) {
    id
    title { romaji english native }
    description(asHtml: false)
    genres
    tags { name rank isMediaSpoiler isGeneralSpoiler }
    characters(role: MAIN, perPage: 6) {
      nodes { name { full native } gender }
    }
  }
}
"""


def _anilist_post(http: Http, query: str, variables: dict) -> dict:
    data = http("POST", ANILIST_URL, json={"query": query, "variables": variables})
    if data.get("errors") and not data.get("data"):
        msg = (data["errors"][0] or {}).get("message", "unknown error")
        raise SeriesSearchError(f"AniList error: {msg}")
    return data.get("data") or {}


def _anilist_title(t: dict) -> tuple[str, str]:
    title = t.get("english") or t.get("romaji") or t.get("native") or ""
    return title, t.get("native") or ""


def _anilist_search(http: Http, query: str) -> list[Candidate]:
    data = _anilist_post(http, _ANILIST_SEARCH, {"search": query})
    out = []
    for m in (data.get("Page") or {}).get("media") or []:
        title, native = _anilist_title(m.get("title") or {})
        out.append(
            Candidate(
                "anilist",
                str(m["id"]),
                title,
                native,
                (m.get("startDate") or {}).get("year"),
                m.get("countryOfOrigin") or "",
            )
        )
    return out


def _anilist_info(http: Http, cand: Candidate) -> SeriesInfo:
    data = _anilist_post(http, _ANILIST_DETAIL, {"id": int(cand.id)})
    m = data.get("Media") or {}
    title, native = _anilist_title(m.get("title") or {})
    gender_map = {"male": "M", "female": "F"}
    chars = []
    for node in ((m.get("characters") or {}).get("nodes")) or []:
        name = (node.get("name") or {}).get("full") or ""
        if not name:
            continue
        chars.append(
            Character(
                name,
                (node.get("name") or {}).get("native") or "",
                gender_map.get((node.get("gender") or "").lower(), ""),
            )
        )
    # Spoiler-flagged tags are dropped; the rest are ranked by relevance.
    tags = [
        t
        for t in (m.get("tags") or [])
        if not t.get("isMediaSpoiler") and not t.get("isGeneralSpoiler")
    ]
    tags.sort(key=lambda t: t.get("rank") or 0, reverse=True)
    return SeriesInfo(
        title=title or cand.title,
        native_title=native or cand.native_title,
        genres=list(m.get("genres") or []),
        themes=[t["name"] for t in tags if t.get("name")],
        description=clean_description(m.get("description")),
        characters=chars,
        source="anilist",
        spoiler_safe=True,
    )


# ---------------------------------------------------------------- MangaDex
def _md_pick(d: dict | None, prefer: tuple[str, ...] = ("en",)) -> str:
    d = d or {}
    for key in prefer:
        if d.get(key):
            return d[key]
    return next((v for v in d.values() if v), "")


def _md_titles(attrs: dict) -> tuple[str, str]:
    title = _md_pick(attrs.get("title"))
    origin = attrs.get("originalLanguage") or ""
    native = ""
    for alt in attrs.get("altTitles") or []:
        for lang, value in alt.items():
            if lang.split("-")[0] == origin.split("-")[0] and origin not in ("", "en") and value:
                native = native or value
    return title, native


def _mangadex_search(http: Http, query: str) -> list[Candidate]:
    data = http("GET", f"{MANGADEX_URL}/manga", params={"title": query, "limit": 8})
    out = []
    for item in data.get("data") or []:
        attrs = item.get("attributes") or {}
        title, native = _md_titles(attrs)
        out.append(
            Candidate("mangadex", item["id"], title, native, attrs.get("year"), attrs.get("originalLanguage") or "")
        )
    return out


def _mangadex_info(http: Http, cand: Candidate) -> SeriesInfo:
    data = http("GET", f"{MANGADEX_URL}/manga/{cand.id}")
    attrs = (data.get("data") or {}).get("attributes") or {}
    title, native = _md_titles(attrs)
    genres, themes = [], []
    for tag in attrs.get("tags") or []:
        ta = tag.get("attributes") or {}
        name = _md_pick(ta.get("name"))
        if not name:
            continue
        if ta.get("group") == "genre":
            genres.append(name)
        elif ta.get("group") == "theme":
            themes.append(name)
    return SeriesInfo(
        title=title or cand.title,
        native_title=native or cand.native_title,
        genres=genres,
        themes=themes,
        description=clean_description(_md_pick(attrs.get("description"))),
        characters=[],
        source="mangadex",
        # MangaDex has no spoiler markup: the user must review the premise.
        spoiler_safe=False,
    )


# ------------------------------------------------------------------ public
def _norm(s: str) -> str:
    return re.sub(r"\W+", "", s.casefold())


def search(query: str, http: Http | None = None) -> list[Candidate]:
    """Search both providers; AniList results come first. Raises
    ``SeriesSearchError`` only if *both* providers fail."""
    query = (query or "").strip()
    if not query:
        return []
    http = http or _default_http

    results: list[Candidate] = []
    errors: list[str] = []
    for fn in (_anilist_search, _mangadex_search):
        try:
            results.extend(fn(http, query))
        except SeriesSearchError as exc:
            errors.append(str(exc))
        except Exception as exc:  # malformed payloads must not crash the UI
            errors.append(f"{fn.__name__}: {exc}")

    if not results and len(errors) == 2:
        raise SeriesSearchError(" / ".join(errors))

    seen, unique = set(), []
    for c in results:
        key = _norm(c.title)
        if key and key not in seen:
            seen.add(key)
            unique.append(c)
    return unique[:10]


def fetch_info(candidate: Candidate, http: Http | None = None) -> SeriesInfo:
    http = http or _default_http
    if candidate.source == "anilist":
        return _anilist_info(http, candidate)
    if candidate.source == "mangadex":
        return _mangadex_info(http, candidate)
    raise SeriesSearchError(f"Unknown source: {candidate.source}")

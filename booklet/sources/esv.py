from __future__ import annotations

import re

import httpx

from booklet.models import PassageText


READING_SLOTS = ("old_testament", "psalm", "epistle", "gospel")
BOOK_TOKENS = [
    "1 Thess",
    "2 Thess",
    "1 Tim",
    "2 Tim",
    "1 Cor",
    "2 Cor",
    "1 Sam",
    "2 Sam",
    "1 Kings",
    "2 Kings",
    "1 Chr",
    "2 Chr",
    "1 Pet",
    "2 Pet",
    "1 John",
    "2 John",
    "3 John",
    "Gen",
    "Ex",
    "Lev",
    "Num",
    "Deut",
    "Josh",
    "Judg",
    "Ruth",
    "Ezra",
    "Neh",
    "Esth",
    "Job",
    "Ps",
    "Prov",
    "Eccl",
    "Song",
    "Isa",
    "Jer",
    "Lam",
    "Ezek",
    "Dan",
    "Hos",
    "Joel",
    "Amos",
    "Obad",
    "Jonah",
    "Mic",
    "Nah",
    "Hab",
    "Zeph",
    "Hag",
    "Zech",
    "Mal",
    "Acts",
    "Rom",
    "Gal",
    "Eph",
    "Phil",
    "Col",
    "Titus",
    "Phlm",
    "Heb",
    "JAM",
    "James",
    "Jude",
    "Matt",
    "Mark",
    "Luke",
    "John",
    "Rev",
]
BOOK_SPLIT_RE = re.compile(
    r"(?=(?:^|\s)("
    + "|".join(re.escape(token) for token in sorted(BOOK_TOKENS, key=len, reverse=True))
    + r")\s)"
)


class ESVSource:
    def __init__(self, api_token: str):
        self.api_token = api_token

    def fetch_compact_readings(self, compact_readings: str) -> list[PassageText]:
        passages: list[PassageText] = []
        for index, citation in enumerate(split_compact_readings(compact_readings)):
            query = normalize_esv_query(citation)
            text = self.fetch_passage(query)
            slot = READING_SLOTS[index] if index < len(READING_SLOTS) else f"reading_{index + 1}"
            passages.append(
                PassageText(
                    slot=slot,
                    citation=citation,
                    query=query,
                    text=text,
                )
            )
        return passages

    def fetch_passage(self, query: str) -> str:
        response = httpx.get(
            "https://api.esv.org/v3/passage/text/",
            params={
                "q": query,
                "include-footnotes": "false",
                "include-headings": "false",
                "include-passage-references": "false",
                "include-copyright": "false",
                "include-short-copyright": "false",
            },
            headers={"Authorization": f"Token {self.api_token}"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        passages = payload.get("passages") or []
        if not passages:
            raise ValueError(f"ESV API returned no passage text for query: {query}")
        return passages[0].strip()


def split_compact_readings(compact_readings: str) -> list[str]:
    text = " ".join(compact_readings.split())
    starts = [match.start(1) for match in BOOK_SPLIT_RE.finditer(text)]
    if not starts:
        return [text]

    citations: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        citation = text[start:end].strip(" ;")
        if citation:
            citations.append(citation)
    return citations


def normalize_esv_query(citation: str) -> str:
    return (
        citation.replace("—", "-")
        .replace("–", "-")
        .replace(";", "")
        .replace(" v", "")
        .strip()
    )

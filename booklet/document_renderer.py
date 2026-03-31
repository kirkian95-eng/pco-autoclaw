from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
import os
import re

from booklet.models import AssembledService, PassageText, RoleAssignment, SongAssignment
from booklet.sources.google_docs import DocumentParagraph, TextReplacement


def _load_name_aliases() -> dict[str, str]:
    """Load name aliases from NAME_ALIASES env var.

    Format: comma-separated KEY:VALUE pairs, e.g. "JAM:James,KT:Kim,MG:Michael"
    Used to expand planning worksheet initials to first names in booklets.
    """
    raw = os.environ.get("NAME_ALIASES", "")
    if not raw.strip():
        return {}
    aliases = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" in pair:
            key, val = pair.split(":", 1)
            aliases[key.strip()] = val.strip()
    return aliases


KNOWN_NAME_ALIASES = _load_name_aliases()

BOOK_NAME_MAP = {
    "Gen": "Genesis",
    "Ex": "Exodus",
    "Lev": "Leviticus",
    "Num": "Numbers",
    "Deut": "Deuteronomy",
    "Josh": "Joshua",
    "Judg": "Judges",
    "Ruth": "Ruth",
    "1 Sam": "1 Samuel",
    "2 Sam": "2 Samuel",
    "1 Kings": "1 Kings",
    "2 Kings": "2 Kings",
    "1 Chr": "1 Chronicles",
    "2 Chr": "2 Chronicles",
    "Ezra": "Ezra",
    "Neh": "Nehemiah",
    "Esth": "Esther",
    "Job": "Job",
    "Ps": "Psalm",
    "Prov": "Proverbs",
    "Eccl": "Ecclesiastes",
    "Song": "Song of Solomon",
    "Isa": "Isaiah",
    "Jer": "Jeremiah",
    "Lam": "Lamentations",
    "Ezek": "Ezekiel",
    "Dan": "Daniel",
    "Hos": "Hosea",
    "Joel": "Joel",
    "Amos": "Amos",
    "Obad": "Obadiah",
    "Jonah": "Jonah",
    "Mic": "Micah",
    "Nah": "Nahum",
    "Hab": "Habakkuk",
    "Zeph": "Zephaniah",
    "Hag": "Haggai",
    "Zech": "Zechariah",
    "Mal": "Malachi",
    "Matt": "Matthew",
    "Mark": "Mark",
    "Luke": "Luke",
    "John": "John",
    "Acts": "Acts",
    "Rom": "Romans",
    "1 Cor": "1 Corinthians",
    "2 Cor": "2 Corinthians",
    "Gal": "Galatians",
    "Eph": "Ephesians",
    "Phil": "Philippians",
    "Col": "Colossians",
    "1 Thess": "1 Thessalonians",
    "2 Thess": "2 Thessalonians",
    "1 Tim": "1 Timothy",
    "2 Tim": "2 Timothy",
    "Titus": "Titus",
    "Phlm": "Philemon",
    "Heb": "Hebrews",
    "James": "James",
    "JAM": "James",
    "1 Pet": "1 Peter",
    "2 Pet": "2 Peter",
    "1 John": "1 John",
    "2 John": "2 John",
    "3 John": "3 John",
    "Jude": "Jude",
    "Rev": "Revelation",
}
PROPHET_BOOKS = {
    "Isaiah",
    "Jeremiah",
    "Lamentations",
    "Ezekiel",
    "Daniel",
    "Hosea",
    "Joel",
    "Amos",
    "Obadiah",
    "Jonah",
    "Micah",
    "Nahum",
    "Habakkuk",
    "Zephaniah",
    "Haggai",
    "Zechariah",
    "Malachi",
}
LETTER_BOOKS = {
    "Romans",
    "1 Corinthians",
    "2 Corinthians",
    "Galatians",
    "Ephesians",
    "Philippians",
    "Colossians",
    "1 Thessalonians",
    "2 Thessalonians",
    "1 Timothy",
    "2 Timothy",
    "Titus",
    "Philemon",
    "Hebrews",
    "James",
    "1 Peter",
    "2 Peter",
    "1 John",
    "2 John",
    "3 John",
    "Jude",
    "Revelation",
}
GOSPEL_BOOKS = {"Matthew", "Mark", "Luke", "John"}


@dataclass
class RenderPlan:
    template_family: str
    replacements: list[TextReplacement] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "template_family": self.template_family,
            "warnings": self.warnings,
            "replacements": [
                {
                    **asdict(replacement),
                    "length_delta": len(replacement.text) - (replacement.end_index - replacement.start_index),
                }
                for replacement in self.replacements
            ],
        }


def build_render_plan(
    service: AssembledService,
    paragraphs: list[DocumentParagraph],
) -> RenderPlan:
    if service.template_family not in ("ordinary_time", "easter"):
        raise NotImplementedError(
            f"render planning is not implemented for family: {service.template_family}"
        )
    return _build_ordinary_time_plan(service, paragraphs)


def _build_ordinary_time_plan(
    service: AssembledService,
    paragraphs: list[DocumentParagraph],
) -> RenderPlan:
    role_lookup = {role.slot: role.first_name for role in service.roles if role.first_name}
    replacements: list[TextReplacement] = []
    warnings: list[str] = []

    title = _format_service_title(service)
    date_line = _format_service_datetime(service.service_date)
    preacher_name = (
        role_lookup.get("officiant")
        or role_lookup.get("preacher")
        or _first_name(service.worksheet.preacher if service.worksheet else None)
    )
    celebrant_name = role_lookup.get("celebrant") or _first_name(
        service.worksheet.celebrant if service.worksheet else None
    )
    worship_name = (
        role_lookup.get("worship_leader")
        or role_lookup.get("music")
        or role_lookup.get("band_leader")
    )

    _append_paragraph_replacement(
        replacements,
        paragraphs,
        lambda p: p.style == "TITLE",
        title,
        "service title",
        warnings,
        occurrence=1,
    )
    _append_paragraph_replacement(
        replacements,
        paragraphs,
        lambda p: p.style == "TITLE" and ("10:30 AM Sunday," in p.text or "10:30am Sunday," in p.text),
        date_line,
        "service date line",
        warnings,
    )
    if preacher_name:
        _append_paragraph_replacement(
            replacements,
            paragraphs,
            lambda p: p.text.startswith("Officiant & Preacher:"),
            f"Officiant & Preacher: {preacher_name}",
            "officiant and preacher line",
            warnings,
        )
        _append_paragraph_replacement(
            replacements,
            paragraphs,
            lambda p: p.text.startswith("Officiant:"),
            f"Officiant: {preacher_name}",
            "officiant line",
            warnings,
        )
        _append_paragraph_replacement(
            replacements,
            paragraphs,
            lambda p: p.text.startswith("Sermon ("),
            f"Sermon ({preacher_name})",
            "sermon heading",
            warnings,
        )
    if celebrant_name:
        _append_paragraph_replacement(
            replacements,
            paragraphs,
            lambda p: p.text.startswith("Celebrant:"),
            f"Celebrant: {celebrant_name}",
            "celebrant line",
            warnings,
        )
    if worship_name:
        _append_paragraph_replacement(
            replacements,
            paragraphs,
            lambda p: p.text.startswith("Music:"),
            f"Music: {worship_name} leading",
            "music line",
            warnings,
        )

    if service.collect:
        _append_after_anchor_replacement(
            replacements,
            paragraphs,
            anchor_text="Officiant: Let us pray.",
            new_text=service.collect,
            description="collect text",
            warnings=warnings,
        )
    _append_announcements_replacement(replacements, paragraphs, service, warnings)
    proper_preface_body = _proper_preface_body(service.proper_preface)
    if proper_preface_body:
        _append_paragraph_replacement(
            replacements,
            paragraphs,
            lambda p: p.text.startswith("Celebrant: When we sinned")
            or p.text.startswith("Celebrant: Through Jesus Christ")
            or p.text.startswith("Celebrant: Who, with your co-eternal Son"),
            f"Celebrant: {proper_preface_body}",
            "proper preface paragraph",
            warnings,
        )

    songs_by_slot = {song.slot: song.title for song in service.songs if song.title}
    _append_song_replacement(replacements, paragraphs, "Song 1:", songs_by_slot.get("song_1"), warnings)
    _append_song_replacement(replacements, paragraphs, "Song 2:", songs_by_slot.get("song_2"), warnings)
    _append_song_replacement(
        replacements,
        paragraphs,
        "Song of Preparation:",
        songs_by_slot.get("song_3"),
        warnings,
    )
    _append_song_replacement(replacements, paragraphs, "Song 4:", songs_by_slot.get("song_4"), warnings)

    readings_by_slot = {reading.slot: reading for reading in service.readings}
    ot = readings_by_slot.get("old_testament")
    psalm = readings_by_slot.get("psalm")
    epistle = readings_by_slot.get("epistle")
    gospel = readings_by_slot.get("gospel")

    if ot:
        _append_reading_block_replacement(
            replacements,
            paragraphs,
            start_predicate=lambda p: p.text.startswith("Lesson Reading"),
            end_predicate=lambda p: p.text.startswith("Reader: The Word of the Lord."),
            intro_line=_format_lesson_intro(ot),
            body_lines=_format_passage_body(ot),
            description="old testament block",
            warnings=warnings,
        )
    if psalm:
        _append_block_replacement(
            replacements,
            paragraphs,
            start_predicate=lambda p: p.text.startswith("Psalm Reading"),
            end_predicate=lambda p: p.text.startswith("All: (Don’t cross yourself here)"),
            new_lines=[
                _format_psalm_intro(psalm),
                *_format_passage_body(psalm),
            ],
            description="psalm block",
            warnings=warnings,
        )
    if epistle:
        _append_reading_block_replacement(
            replacements,
            paragraphs,
            start_predicate=lambda p: p.text.startswith("Lesson Reading"),
            end_predicate=lambda p: p.text.startswith("Reader: The Word of the Lord."),
            intro_line=_format_lesson_intro(epistle),
            body_lines=_format_passage_body(epistle),
            description="epistle block",
            warnings=warnings,
            occurrence=2,
        )
    if gospel:
        _append_paragraph_replacement(
            replacements,
            paragraphs,
            lambda p: p.text.startswith("Gospel Reading ("),
            "Gospel Reading (Gospel Reader)",
            "gospel heading",
            warnings,
        )
        _append_gospel_block_replacement(
            replacements,
            paragraphs,
            intro_line=_format_gospel_intro(gospel),
            body_lines=_format_passage_body(gospel),
            description="gospel block",
            warnings=warnings,
        )

    return RenderPlan(
        template_family=service.template_family,
        replacements=replacements,
        warnings=warnings,
    )


def _append_song_replacement(
    replacements: list[TextReplacement],
    paragraphs: list[DocumentParagraph],
    prefix: str,
    song_title: str | None,
    warnings: list[str],
) -> None:
    if not song_title:
        return
    team_label = "Music Team"
    if prefix == "Song of Preparation:":
        text = f"{prefix} {song_title} ({team_label})"
    else:
        text = f"{prefix} {song_title} ({team_label})"
    _append_paragraph_replacement(
        replacements,
        paragraphs,
        lambda p: p.text.startswith(prefix),
        text,
        f"{prefix} title",
        warnings,
    )


def _append_after_anchor_replacement(
    replacements: list[TextReplacement],
    paragraphs: list[DocumentParagraph],
    anchor_text: str,
    new_text: str,
    description: str,
    warnings: list[str],
) -> None:
    for index, paragraph in enumerate(paragraphs):
        if paragraph.text != anchor_text:
            continue
        for candidate in paragraphs[index + 1:]:
            if candidate.style == "NORMAL_TEXT" and not candidate.text.startswith("All:"):
                replacements.append(
                    TextReplacement(
                        start_index=candidate.start_index,
                        end_index=candidate.content_end_index,
                        text=new_text,
                        description=description,
                    )
                )
                return
    warnings.append(f"Could not locate paragraph after anchor: {anchor_text}")


def _append_paragraph_replacement(
    replacements: list[TextReplacement],
    paragraphs: list[DocumentParagraph],
    predicate,
    new_text: str,
    description: str,
    warnings: list[str],
    occurrence: int = 1,
) -> None:
    paragraph_index = _find_paragraph_index(paragraphs, predicate, occurrence=occurrence)
    if paragraph_index is None:
        warnings.append(f"Could not locate paragraph for {description}")
        return
    paragraph = paragraphs[paragraph_index]
    replacements.append(
        TextReplacement(
            start_index=paragraph.start_index,
            end_index=paragraph.content_end_index,
            text=new_text,
            description=description,
        )
    )


def _append_block_replacement(
    replacements: list[TextReplacement],
    paragraphs: list[DocumentParagraph],
    start_predicate,
    end_predicate,
    new_lines: list[str],
    description: str,
    warnings: list[str],
    occurrence: int = 1,
) -> None:
    start_index = _find_paragraph_index(paragraphs, start_predicate, occurrence=occurrence)
    if start_index is None:
        warnings.append(f"Could not locate start paragraph for {description}")
        return
    end_index = _find_paragraph_index(
        paragraphs[start_index + 1:],
        end_predicate,
        occurrence=1,
    )
    if end_index is None:
        warnings.append(f"Could not locate end paragraph for {description}")
        return
    last_content = paragraphs[start_index + end_index]
    replacements.append(
        TextReplacement(
            start_index=paragraphs[start_index].start_index,
            end_index=last_content.content_end_index,
            text="\n".join(new_lines),
            description=description,
        )
    )


def _append_reading_block_replacement(
    replacements: list[TextReplacement],
    paragraphs: list[DocumentParagraph],
    start_predicate,
    end_predicate,
    intro_line: str,
    body_lines: list[str],
    description: str,
    warnings: list[str],
    occurrence: int = 1,
) -> None:
    _append_block_replacement(
        replacements,
        paragraphs,
        start_predicate=start_predicate,
        end_predicate=end_predicate,
        new_lines=[
            intro_line,
            "*Please count to 5 to allow for locating text*",
            *body_lines,
        ],
        description=description,
        warnings=warnings,
        occurrence=occurrence,
    )


def _append_gospel_block_replacement(
    replacements: list[TextReplacement],
    paragraphs: list[DocumentParagraph],
    intro_line: str,
    body_lines: list[str],
    description: str,
    warnings: list[str],
) -> None:
    _append_block_replacement(
        replacements,
        paragraphs,
        start_predicate=lambda p: p.text.startswith("Gospel Reader: You may follow along"),
        end_predicate=lambda p: p.text.startswith("Reader: This is the Gospel of the Lord."),
        new_lines=[
            intro_line,
            "(Sign of the cross on forehead, lips and heart, using thumb)",
            "All: Glory to you, Lord Christ.",
            "*Please count to 5 to allow for locating text*",
            *body_lines,
        ],
        description=description,
        warnings=warnings,
    )


def _find_paragraph_index(
    paragraphs: list[DocumentParagraph],
    predicate,
    occurrence: int = 1,
) -> int | None:
    seen = 0
    for index, paragraph in enumerate(paragraphs):
        if predicate(paragraph):
            seen += 1
            if seen == occurrence:
                return index
    return None


def _format_service_title(service: AssembledService) -> str:
    observance = (service.observance or service.description or "Ordinary Time").strip()
    if observance.lower().startswith("proper "):
        return f"Ordinary Time: {observance}"
    return observance


def _format_service_datetime(service_date: str) -> str:
    dt = date.fromisoformat(service_date)
    return f"10:30 AM Sunday, {dt.strftime('%B')} {dt.day}, {dt.year}"


def _format_lesson_intro(passage: PassageText) -> str:
    return "Lesson Reading (Reader 1): You may follow along in your pew Bibles. " + _reading_intro_clause(passage.citation)


def _format_psalm_intro(passage: PassageText) -> str:
    return f"Psalm Reading (Reader 2): Let us read from {_format_psalm_citation(passage.citation)} responsively by half-verse:"


def _format_gospel_intro(passage: PassageText) -> str:
    return "Gospel Reader: You may follow along in your pew Bibles. " + _gospel_intro_clause(passage.citation)


def _format_psalm_citation(citation: str) -> str:
    normalized = citation.replace("Ps ", "Psalm ", 1)
    return normalized.replace("–", "-")


def _format_citation_long(citation: str) -> str:
    normalized = citation.replace("–", "-")
    match = re.match(r"^([1-3]?\s?[A-Za-z]+)\s+(.*)$", normalized)
    if not match:
        return normalized
    book_token = " ".join(match.group(1).split())
    book = BOOK_NAME_MAP.get(book_token, book_token)
    rest = match.group(2)
    return f"{book} {rest}"


def _format_passage_body(passage: PassageText) -> list[str]:
    cleaned_text = _strip_verse_numbers(passage.text)
    blocks = [block.strip() for block in re.split(r"\n\s*\n", cleaned_text) if block.strip()]
    if not blocks:
        return [cleaned_text.strip()]
    return blocks


def _strip_verse_numbers(text: str) -> str:
    return re.sub(r"\[(\d+)\]\s*", "", text)


def _append_announcements_replacement(
    replacements: list[TextReplacement],
    paragraphs: list[DocumentParagraph],
    service: AssembledService,
    warnings: list[str],
) -> None:
    lines: list[str] = []
    worksheet = service.worksheet
    if worksheet:
        for value in [worksheet.special_theme, worksheet.special_elements, worksheet.special_volunteers]:
            if value:
                lines.extend(_split_semantic_lines(value))
    _append_section_contents_replacement(
        replacements,
        paragraphs,
        heading_text="Announcements (Officiant)",
        new_lines=lines,
        description="announcements block",
        warnings=warnings,
    )


def _first_name(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.replace("Probably ", "").strip()
    if normalized in KNOWN_NAME_ALIASES:
        return KNOWN_NAME_ALIASES[normalized]
    if normalized.isupper() and normalized in KNOWN_NAME_ALIASES:
        return KNOWN_NAME_ALIASES[normalized]
    return normalized.split()[0]


def _proper_preface_body(value: str | None) -> str | None:
    if not value:
        return None
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", value) if chunk.strip()]
    if not chunks:
        return None
    if len(chunks) == 1:
        return chunks[0]
    return chunks[1]


def _reading_intro_clause(citation: str) -> str:
    parsed = _parse_citation(citation)
    if not parsed:
        return f"A reading from {_format_citation_long(citation)}:"
    book, chapter1, verse1, chapter2, verse2 = parsed
    if book in PROPHET_BOOKS:
        label = f"the Prophet {book}"
    elif book in LETTER_BOOKS:
        label = book
    else:
        label = book
    return f"A reading from {label}, {_verbalize_reference(chapter1, verse1, chapter2, verse2)}:"


def _gospel_intro_clause(citation: str) -> str:
    parsed = _parse_citation(citation)
    if not parsed:
        return f"The Holy Gospel according to {_format_citation_long(citation)}."
    book, chapter1, verse1, chapter2, verse2 = parsed
    if book not in GOSPEL_BOOKS:
        return f"The Holy Gospel according to {book}, {_verbalize_reference(chapter1, verse1, chapter2, verse2)}."
    return f"The Holy Gospel according to {book}, {_verbalize_reference(chapter1, verse1, chapter2, verse2)}."


def _verbalize_reference(
    chapter1: str,
    verse1: str | None,
    chapter2: str | None,
    verse2: str | None,
) -> str:
    if verse1 is None:
        return f"chapter {chapter1}"
    if verse2 and not chapter2:
        return f"chapter {chapter1}, verses {verse1}-{verse2}"
    if chapter2 and verse2:
        if chapter2 == chapter1:
            return f"chapter {chapter1}, verses {verse1}-{verse2}"
        return f"chapter {chapter1}, verse {verse1} through chapter {chapter2}, verse {verse2}"
    return f"chapter {chapter1}, verses {verse1}"


def _parse_citation(citation: str) -> tuple[str, str, str | None, str | None, str | None] | None:
    normalized = citation.replace("—", "-").replace("–", "-")
    match = re.match(r"^(.+?)\s+(\d+)(?::(\d+)(?:-(?:(\d+):)?(\d+))?)?$", normalized)
    if not match:
        return None
    book_token = " ".join(match.group(1).split())
    book = BOOK_NAME_MAP.get(book_token, book_token)
    chapter1 = match.group(2)
    verse1 = match.group(3)
    chapter2 = match.group(4)
    verse2 = match.group(5)
    return book, chapter1, verse1, chapter2, verse2


def _split_semantic_lines(value: str) -> list[str]:
    parts = re.split(r"\n+|;\s*|\s{2,}", value)
    return [part.strip() for part in parts if part.strip()]


def _append_section_contents_replacement(
    replacements: list[TextReplacement],
    paragraphs: list[DocumentParagraph],
    heading_text: str,
    new_lines: list[str],
    description: str,
    warnings: list[str],
) -> None:
    heading_index = _find_paragraph_index(paragraphs, lambda p: p.text == heading_text)
    if heading_index is None:
        warnings.append(f"Could not locate section heading for {description}")
        return
    next_heading_index = None
    for idx in range(heading_index + 1, len(paragraphs)):
        if paragraphs[idx].style.startswith("HEADING_"):
            next_heading_index = idx
            break
    if next_heading_index is None:
        warnings.append(f"Could not locate section end for {description}")
        return
    start_paragraph = paragraphs[heading_index + 1] if heading_index + 1 < next_heading_index else None
    if not start_paragraph:
        return
    end_paragraph = paragraphs[next_heading_index - 1]
    replacements.append(
        TextReplacement(
            start_index=start_paragraph.start_index,
            end_index=end_paragraph.content_end_index,
            text="\n".join(new_lines),
            description=description,
        )
    )

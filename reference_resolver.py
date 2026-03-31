from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re

from booklet.generate_liturgical_sundays import SundayEntry, generate_sunday_entries


ORDINAL_WORDS = {
    "first": 1,
    "1st": 1,
    "second": 2,
    "2nd": 2,
    "third": 3,
    "3rd": 3,
    "fourth": 4,
    "4th": 4,
    "fifth": 5,
    "5th": 5,
    "sixth": 6,
    "6th": 6,
    "seventh": 7,
    "7th": 7,
    "eighth": 8,
    "8th": 8,
    "ninth": 9,
    "9th": 9,
    "tenth": 10,
    "10th": 10,
    "eleventh": 11,
    "11th": 11,
    "twelfth": 12,
    "12th": 12,
    "thirteenth": 13,
    "13th": 13,
    "fourteenth": 14,
    "14th": 14,
    "fifteenth": 15,
    "15th": 15,
    "sixteenth": 16,
    "16th": 16,
    "seventeenth": 17,
    "17th": 17,
    "eighteenth": 18,
    "18th": 18,
    "nineteenth": 19,
    "19th": 19,
    "twentieth": 20,
    "20th": 20,
}

MONTH_WORDS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


@dataclass(frozen=True)
class ResolvedSunday:
    service_date: date
    label: str
    template_family: str


@dataclass(frozen=True)
class SundayResolution:
    status: str
    query: str
    resolved: ResolvedSunday | None = None
    candidates: tuple[ResolvedSunday, ...] = ()
    message: str | None = None


def resolve_sunday_reference(query: str, today: date | None = None) -> SundayResolution:
    today = today or date.today()
    original_query = query.strip()
    normalized = _normalize_query(query)
    entries = _candidate_entries(today)

    direct_date = _extract_iso_date(normalized)
    if direct_date:
        return _resolved(query, ResolvedSunday(direct_date, query.strip(), _template_family_for_label(query)))

    month_day = _extract_month_day(normalized, today)
    if month_day:
        return _resolved(query, ResolvedSunday(month_day, month_day.isoformat(), _template_family_for_label(month_day.isoformat())))

    year = _extract_year(normalized)
    scoped_entries = tuple(entry for entry in entries if year is None or entry.service_date.year == year)

    if proper := _match_proper(normalized, scoped_entries):
        return _resolved(query, proper)

    if exact := _match_exact_label(normalized, scoped_entries, today):
        return _resolved(query, exact)

    if ordinary := _match_ordinary_time(original_query, normalized, scoped_entries):
        return ordinary

    if season := _match_season_ordinal(normalized, scoped_entries):
        return season

    if fuzzy := _match_fuzzy(normalized, scoped_entries, today):
        return _resolved(query, fuzzy)

    return SundayResolution(
        status="not_found",
        query=query,
        message=f'I could not match "{query}" to a Sunday in the liturgical calendar.',
    )


def _candidate_entries(today: date) -> tuple[SundayEntry, ...]:
    end_year = max(today.year + 3, 2029)
    return tuple(generate_sunday_entries(date(2026, 1, 1), date(end_year, 12, 31)))


def _resolved(query: str, sunday: ResolvedSunday) -> SundayResolution:
    return SundayResolution(status="resolved", query=query, resolved=sunday)


def _extract_iso_date(text: str) -> date | None:
    match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", text)
    return date.fromisoformat(match.group(0)) if match else None


def _extract_year(text: str) -> int | None:
    match = re.search(r"\b(20\d{2})\b", text)
    return int(match.group(1)) if match else None


def _extract_month_day(text: str, today: date) -> date | None:
    month_names = "|".join(MONTH_WORDS)
    match = re.search(rf"\b({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(20\d{{2}}))?\b", text)
    if not match:
        return None
    month = MONTH_WORDS[match.group(1)]
    day = int(match.group(2))
    if match.group(3):
        return date(int(match.group(3)), month, day)
    candidate = date(today.year, month, day)
    if candidate < today:
        candidate = date(today.year + 1, month, day)
    return candidate


def _extract_ordinal(text: str) -> int | None:
    for token, value in sorted(ORDINAL_WORDS.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"\b{re.escape(token)}\b", text):
            return value
    return None


def _match_proper(text: str, entries: tuple[SundayEntry, ...]) -> ResolvedSunday | None:
    match = re.search(r"\bproper\s+(\d{1,2})\b", text)
    if not match:
        return None
    target = f"proper {int(match.group(1))}"
    for entry in entries:
        if entry.label.lower().startswith(target):
            return _resolved_from_entry(entry)
    return None


def _match_exact_label(text: str, entries: tuple[SundayEntry, ...], today: date) -> ResolvedSunday | None:
    matches = []
    for entry in entries:
        normalized_label = _normalize_query(entry.label)
        if normalized_label == text or normalized_label in text:
            matches.append(_resolved_from_entry(entry))
    if not matches:
        return None
    return _choose_nearest(matches, today)


def _match_ordinary_time(
    original_query: str,
    text: str,
    entries: tuple[SundayEntry, ...],
) -> SundayResolution | None:
    if "ordinary time" not in text:
        return None

    ordinal = _extract_ordinal(text)
    if ordinal is None:
        return None

    proper_entries = [
        _resolved_from_entry(entry)
        for entry in entries
        if entry.label == "Trinity Sunday" or _is_proper_entry(entry.label)
    ]
    epiphany_entries = [_resolved_from_entry(entry) for entry in entries if _is_epiphany_entry(entry.label)]
    candidates: list[ResolvedSunday] = []

    if "after pentecost" in text or "following pentecost" in text or "post pentecost" in text:
        if 1 <= ordinal <= len(proper_entries):
            return _resolved(original_query, proper_entries[ordinal - 1])
        return None

    if 1 <= ordinal <= len(epiphany_entries):
        candidates.append(epiphany_entries[ordinal - 1])
    if 1 <= ordinal <= len(proper_entries):
        candidates.append(proper_entries[ordinal - 1])

    if not candidates:
        return None
    if len(candidates) == 1:
        return _resolved(original_query, candidates[0])

    return SundayResolution(
        status="ambiguous",
        query=original_query,
        candidates=tuple(candidates[:2]),
        message=_build_ordinary_time_ambiguity(original_query, tuple(candidates[:2])),
    )


def _match_season_ordinal(text: str, entries: tuple[SundayEntry, ...]) -> SundayResolution | None:
    ordinal = _extract_ordinal(text)
    if ordinal is None:
        return None

    season_map = {
        "advent": "sunday in advent",
        "lent": "sunday in lent",
        "easter": "sunday of easter",
        "christmas": "sunday of christmas",
        "epiphany": "sunday of epiphany",
    }
    for season_token, phrase in season_map.items():
        if season_token not in text:
            continue
        target = f"{_ordinal_name(ordinal)} {phrase}"
        matches = [
            _resolved_from_entry(entry)
            for entry in entries
            if entry.label.lower() == target
        ]
        if matches:
            return _resolved(text, matches[0])
    return None


def _match_fuzzy(text: str, entries: tuple[SundayEntry, ...], today: date) -> ResolvedSunday | None:
    matches = [
        _resolved_from_entry(entry)
        for entry in entries
        if text in _normalize_query(entry.label) or _normalize_query(entry.label) in text
    ]
    if not matches:
        return None
    return _choose_nearest(matches, today)


def _resolved_from_entry(entry: SundayEntry) -> ResolvedSunday:
    return ResolvedSunday(
        service_date=entry.service_date,
        label=entry.label,
        template_family=_template_family_for_label(entry.label),
    )


def _choose_nearest(matches: list[ResolvedSunday], today: date) -> ResolvedSunday:
    upcoming = [match for match in matches if match.service_date >= today]
    pool = upcoming or matches
    return sorted(pool, key=lambda item: abs((item.service_date - today).days))[0]


def _normalize_query(value: str) -> str:
    cleaned = value.strip().lower().replace("’", "'")
    return " ".join(cleaned.split())


def _ordinal_name(value: int) -> str:
    for token, ordinal in ORDINAL_WORDS.items():
        if ordinal == value and token.isalpha():
            return token
    return str(value)


def _is_epiphany_entry(label: str) -> bool:
    lowered = label.lower()
    return "sunday of epiphany" in lowered


def _is_proper_entry(label: str) -> bool:
    return label.lower().startswith("proper ")


def _build_ordinary_time_ambiguity(query: str, candidates: tuple[ResolvedSunday, ...]) -> str:
    options = " or ".join(
        f"{candidate.service_date.isoformat()} ({candidate.label})"
        for candidate in candidates
    )
    return f'"{query}" is ambiguous. Did you mean {options}?'


def _template_family_for_label(label: str) -> str:
    lowered = label.lower()
    if "advent" in lowered:
        return "advent"
    if "palm sunday" in lowered:
        return "palm_sunday"
    if "lent" in lowered:
        return "lent"
    if "easter" in lowered:
        return "easter"
    if "epiphany" in lowered:
        return "epiphany"
    if "christmas" in lowered:
        return "christmas"
    if "pentecost" in lowered:
        return "pentecost"
    return "ordinary_time"

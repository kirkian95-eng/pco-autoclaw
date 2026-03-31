from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


EASTER_SUNDAYS = {
    2026: date(2026, 4, 5),
    2027: date(2027, 3, 28),
    2028: date(2028, 4, 16),
    2029: date(2029, 4, 1),
}

PROPER_RANGES = [
    ((5, 8), (5, 14), "Proper 1"),
    ((5, 15), (5, 21), "Proper 2"),
    ((5, 22), (5, 28), "Proper 3"),
    ((5, 29), (6, 4), "Proper 4"),
    ((6, 5), (6, 11), "Proper 5"),
    ((6, 12), (6, 18), "Proper 6"),
    ((6, 19), (6, 25), "Proper 7"),
    ((6, 26), (7, 2), "Proper 8"),
    ((7, 3), (7, 9), "Proper 9"),
    ((7, 10), (7, 16), "Proper 10"),
    ((7, 17), (7, 23), "Proper 11"),
    ((7, 24), (7, 30), "Proper 12"),
    ((7, 31), (8, 6), "Proper 13"),
    ((8, 7), (8, 13), "Proper 14"),
    ((8, 14), (8, 20), "Proper 15"),
    ((8, 21), (8, 27), "Proper 16"),
    ((8, 28), (9, 3), "Proper 17"),
    ((9, 4), (9, 10), "Proper 18"),
    ((9, 11), (9, 17), "Proper 19"),
    ((9, 18), (9, 24), "Proper 20"),
    ((9, 25), (10, 1), "Proper 21"),
    ((10, 2), (10, 8), "Proper 22"),
    ((10, 9), (10, 15), "Proper 23"),
    ((10, 16), (10, 22), "Proper 24"),
    ((10, 23), (10, 29), "Proper 25"),
    ((10, 30), (11, 5), "Proper 26"),
    ((11, 6), (11, 12), "Proper 27"),
    ((11, 13), (11, 19), "Proper 28"),
    ((11, 20), (11, 26), "Proper 29 (Christ the King)"),
]

ORDINALS = {
    1: "First",
    2: "Second",
    3: "Third",
    4: "Fourth",
    5: "Fifth",
    6: "Sixth",
    7: "Seventh",
    8: "Eighth",
}


@dataclass(frozen=True)
class SundayEntry:
    service_date: date
    label: str
    season: str


def generate_sunday_entries(start_date: date, end_date: date) -> list[SundayEntry]:
    first_sunday = _next_or_same_sunday(start_date)
    current = first_sunday
    entries: list[SundayEntry] = []
    while current <= end_date:
        entries.append(SundayEntry(service_date=current, label=label_for_sunday(current), season=season_for_sunday(current)))
        current += timedelta(days=7)
    return entries


def label_for_sunday(service_date: date) -> str:
    advent_start = first_sunday_of_advent(service_date.year)
    christmas_year = service_date.year if service_date.month == 12 else service_date.year - 1
    christmas = date(christmas_year, 12, 25)
    epiphany_year = service_date.year + 1 if service_date.month == 12 else service_date.year
    first_epiphany = first_sunday_of_epiphany(epiphany_year)
    easter = easter_sunday(service_date.year)
    ash_wednesday = easter - timedelta(days=46)
    palm_sunday = easter - timedelta(days=7)
    pentecost = easter + timedelta(days=49)
    trinity = easter + timedelta(days=56)
    sunday_after_ascension = easter + timedelta(days=42)

    if christmas <= service_date < first_epiphany:
        return "Christmas Day" if service_date == christmas else _christmas_sunday_label(service_date)

    if service_date >= advent_start:
        week = ((service_date - advent_start).days // 7) + 1
        return f"{_ordinal_name(week)} Sunday in Advent"

    if service_date < ash_wednesday and service_date >= first_epiphany:
        return _epiphany_label(service_date, first_epiphany, ash_wednesday)

    if service_date == palm_sunday:
        return "Palm Sunday"
    if service_date == easter:
        return "Easter Day"
    if service_date == pentecost:
        return "Pentecost"
    if service_date == trinity:
        return "Trinity Sunday"
    if service_date == sunday_after_ascension:
        return "Sunday after Ascension Day"

    if ash_wednesday < service_date < palm_sunday:
        lent_number = ((service_date - (ash_wednesday + timedelta(days=4))).days // 7) + 1
        return f"{_ordinal_name(lent_number)} Sunday in Lent"

    if easter < service_date < pentecost:
        easter_number = ((service_date - easter).days // 7) + 1
        return f"{_ordinal_name(easter_number)} Sunday of Easter"

    if trinity < service_date < advent_start:
        return _proper_label(service_date)

    if service_date.year < min(EASTER_SUNDAYS):
        # Only needed for late-Christmas carryover when start_date predates 2026.
        return _christmas_sunday_label(service_date)

    raise ValueError(f"Could not resolve liturgical label for {service_date.isoformat()}")


def season_for_sunday(service_date: date) -> str:
    label = label_for_sunday(service_date)
    lowered = label.lower()
    if "advent" in lowered:
        return "Advent"
    if "christmas" in lowered:
        return "Christmas"
    if "epiphany" in lowered or "world mission" in lowered or "transfiguration" in lowered:
        return "Epiphany"
    if "lent" in lowered or "palm" in lowered:
        return "Lent / Holy Week"
    if "easter" in lowered or "ascension" in lowered:
        return "Easter"
    if "pentecost" in lowered:
        return "Pentecost"
    if "trinity" in lowered or "proper" in lowered:
        return "Ordinary Time"
    return "Season Unknown"


def build_markdown(start_date: date, end_date: date) -> str:
    entries = generate_sunday_entries(start_date, end_date)
    lines = [
        "# ACNA Sunday Calendar Through 2029",
        "",
        f"Generated for Hildy on {date.today().isoformat()}.",
        "",
        "Source rules:",
        "- ACNA 2019 BCP Calendar of the Christian Year",
        "- ACNA 2019 Leaflet Scriptures Year A, Year B, and Year C",
        "",
        "Notes:",
        "- This list starts with the next Sunday on or after the chosen start date.",
        "- Labels follow ACNA 2019 naming as closely as possible for Sunday observances.",
        "- Ordinary Time Sundays after Trinity are listed by ACNA Proper number.",
        "",
    ]
    current_year = None
    for entry in entries:
        if current_year != entry.service_date.year:
            current_year = entry.service_date.year
            lines.extend([f"## {current_year}", ""])
        lines.append(f"- {entry.service_date.isoformat()} - {entry.label}")
    lines.append("")
    lines.append("Sources:")
    lines.append("- https://bcp2019.anglicanchurch.net/wp-content/uploads/2019/08/57-Calendar-of-the-Christian-Year.pdf")
    lines.append("- https://bcp2019.anglicanchurch.net/index.php/leaflet-scriptures-year-a/")
    lines.append("- https://bcp2019.anglicanchurch.net/index.php/leaflet-scriptures-year-b/")
    lines.append("- https://bcp2019.anglicanchurch.net/index.php/leaflet-scriptures-year-c/")
    return "\n".join(lines) + "\n"


def write_markdown(output_path: Path, start_date: date, end_date: date) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_markdown(start_date, end_date), encoding="utf-8")
    return output_path


def easter_sunday(year: int) -> date:
    if year in EASTER_SUNDAYS:
        return EASTER_SUNDAYS[year]
    raise KeyError(f"Easter date not configured for {year}")


def first_sunday_of_advent(year: int) -> date:
    current = date(year, 11, 27)
    while current.weekday() != 6:
        current += timedelta(days=1)
    return current


def first_sunday_of_epiphany(year: int) -> date:
    current = date(year, 1, 7)
    while current.weekday() != 6:
        current += timedelta(days=1)
    return current


def _liturgical_year_end(service_date: date) -> int:
    return service_date.year + 1 if service_date >= first_sunday_of_advent(service_date.year) else service_date.year


def _next_or_same_sunday(value: date) -> date:
    return value + timedelta(days=(6 - value.weekday()) % 7)


def _christmas_sunday_label(service_date: date) -> str:
    christmas_day = date(service_date.year if service_date.month == 12 else service_date.year - 1, 12, 25)
    if service_date == christmas_day:
        return "Christmas Day"
    index = ((service_date - _next_or_same_sunday(christmas_day)).days // 7) + 1
    return f"{_ordinal_name(index)} Sunday of Christmas"


def _epiphany_label(service_date: date, first_epiphany: date, ash_wednesday: date) -> str:
    last_sunday = ash_wednesday - timedelta(days=3)
    second_to_last = last_sunday - timedelta(days=7)
    if service_date == first_epiphany:
        return "First Sunday of Epiphany (Baptism of Our Lord)"
    if service_date == last_sunday:
        return "Last Sunday of Epiphany (Transfiguration)"
    if service_date == second_to_last:
        return "World Mission Sunday (2nd to Last Sunday of Epiphany)"
    index = ((service_date - first_epiphany).days // 7) + 1
    return f"{_ordinal_name(index)} Sunday of Epiphany"


def _proper_label(service_date: date) -> str:
    md = (service_date.month, service_date.day)
    for start_md, end_md, label in PROPER_RANGES:
        if start_md <= md <= end_md:
            return label
    raise ValueError(f"No Proper rule matched {service_date.isoformat()}")


def _ordinal_name(number: int) -> str:
    if number not in ORDINALS:
        raise ValueError(f"No ordinal label configured for {number}")
    return ORDINALS[number]

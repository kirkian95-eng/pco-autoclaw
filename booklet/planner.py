from __future__ import annotations

from datetime import date

from .models import PlannedService


def build_planned_service(
    service_date: date,
    service_type_id: str,
    template_family: str,
) -> PlannedService:
    """Return the minimum persisted planning record for a future generator run.

    This deliberately avoids pretending to resolve the full lectionary or PCO plan
    before the adapters exist. The first implementation slice is ordinary time
    after Pentecost, so we treat the chosen template family as authoritative for now.
    """

    _validate_service_date(service_date, template_family)

    season = _season_from_template_family(template_family)
    observance = _observance_from_template_family(template_family)

    return PlannedService(
        service_date=service_date.isoformat(),
        service_type_id=service_type_id,
        template_family=template_family,
        season=season,
        observance=observance,
    )


def _season_from_template_family(template_family: str) -> str:
    mapping = {
        "ordinary_after_pentecost": "ordinary time",
        "advent": "advent",
        "lent": "lent",
        "easter": "easter",
        "epiphany": "epiphany",
    }
    return mapping.get(template_family, template_family.replace("_", " "))


def _observance_from_template_family(template_family: str) -> str | None:
    special = {
        "palm_sunday": "Palm Sunday",
        "easter_day": "Easter Day",
        "pentecost": "Pentecost",
    }
    return special.get(template_family)


def _validate_service_date(service_date: date, template_family: str) -> None:
    weekday_families = {"ash_wednesday"}
    if template_family in weekday_families:
        return
    if service_date.weekday() != 6:
        raise ValueError(
            f"{service_date.isoformat()} is a {service_date.strftime('%A')}, not a Sunday"
        )

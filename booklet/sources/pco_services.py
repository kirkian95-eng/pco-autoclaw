from __future__ import annotations

import re
from datetime import date, datetime, timezone

from booklet.models import RoleAssignment, SongAssignment


GENERIC_SONG_SLOT_RE = re.compile(r"^song\s+\d+$", re.IGNORECASE)
EXCLUDED_BOOKLET_SONG_TITLES = {
    "Doxology",
    "Sanctus",
    "Agnus Dei",
    "Kyrie",
    "Gloria",
    "Gloria Patri",
}


class PlanningCenterSource:
    def __init__(self):
        from pco_client import PCOClient

        self.client = PCOClient()

    def get_plan_for_date(self, service_type_id: str, service_date: date) -> dict | None:
        now = datetime.now(timezone.utc).date()
        days_ahead = max((service_date - now).days + 14, 21)
        plans = self.client.get_upcoming_plans(service_type_id, days_ahead=days_ahead)
        for plan in plans:
            sort_date = (plan.get("attributes") or {}).get("sort_date", "")[:10]
            if sort_date == service_date.isoformat():
                return plan
        return None

    def get_role_assignments(self, service_type_id: str, plan_id: str) -> list[RoleAssignment]:
        assignments: list[RoleAssignment] = []
        for team_member in self.client.get_plan_team_members(service_type_id, plan_id):
            attrs = team_member.get("attributes") or {}
            status = (attrs.get("status") or "").strip().upper()
            if status == "D":
                continue
            assignments.append(
                RoleAssignment(
                    slot=_slotify(attrs.get("team_position_name") or "participant"),
                    first_name=_first_name(attrs.get("name")),
                )
            )
        return assignments

    def get_song_assignments(self, service_type_id: str, plan_id: str) -> list[SongAssignment]:
        songs: list[SongAssignment] = []
        endpoint = f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/items"
        item_index = 1
        for payload in self.client.pco.iterate(endpoint, include="song"):
            item = payload.get("data") or {}
            attrs = item.get("attributes") or {}
            if attrs.get("item_type") != "song":
                continue
            if (attrs.get("service_position") or "").strip().lower() != "during":
                continue

            item_title = (attrs.get("title") or "").strip()
            related_song_title = None
            for included in payload.get("included") or []:
                if included.get("type") == "Song":
                    related_song_title = (included.get("attributes") or {}).get("title")
                    break

            title = related_song_title or None
            if not title and item_title and not GENERIC_SONG_SLOT_RE.match(item_title):
                title = item_title
            if title in EXCLUDED_BOOKLET_SONG_TITLES:
                continue

            songs.append(SongAssignment(slot=f"song_{item_index}", title=title))
            item_index += 1
        return songs


def _slotify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _first_name(full_name: str | None) -> str | None:
    if not full_name:
        return None
    return full_name.strip().split()[0]

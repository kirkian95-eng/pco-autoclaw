from __future__ import annotations

from datetime import date

from booklet.config import BookletConfig
from booklet.models import AssembledService, RoleAssignment, SongAssignment
from booklet.planner import build_planned_service
from booklet.sources.esv import ESVSource
from booklet.sources.pco_services import PlanningCenterSource
from booklet.sources.planning_worksheet import PlanningWorksheetSource


def assemble_service(
    config: BookletConfig,
    service_date: date,
    service_type_id: str,
    template_family: str,
    include_pco: bool = True,
    include_scripture: bool = True,
) -> AssembledService:
    planned = build_planned_service(
        service_date=service_date,
        service_type_id=service_type_id,
        template_family=template_family,
    )
    worksheet = PlanningWorksheetSource(config.planning_workbook_file).get_service(service_date)
    notes: list[str] = []

    readings = []
    if worksheet and worksheet.compact_readings and include_scripture:
        if not config.esv_api_token:
            notes.append("ESV_API_TOKEN is not configured; scripture text was skipped.")
        else:
            readings = ESVSource(config.esv_api_token).fetch_compact_readings(
                worksheet.compact_readings
            )
    elif include_scripture:
        notes.append("No worksheet readings found for this date.")

    roles: list[RoleAssignment] = []
    songs: list[SongAssignment] = list(worksheet.songs) if worksheet else []
    plan_id: str | None = None

    if include_pco:
        try:
            pco = PlanningCenterSource()
            plan = pco.get_plan_for_date(service_type_id, service_date)
            if plan:
                plan_id = plan["id"]
                roles = pco.get_role_assignments(service_type_id, plan_id)
                pco_songs = pco.get_song_assignments(service_type_id, plan_id)
                songs = _merge_song_lists(
                    worksheet.songs if worksheet else [],
                    pco_songs,
                )
                if not pco_songs:
                    notes.append("Planning Center has no booklet-song items yet; using worksheet songs.")
            else:
                notes.append("No Planning Center plan found for this service date.")
        except KeyError:
            notes.append("Planning Center credentials are not configured on this machine.")
        except Exception as exc:
            notes.append(f"Planning Center lookup skipped: {exc}")
    else:
        notes.append("Planning Center lookup skipped by request.")

    if worksheet and worksheet.preacher:
        notes.append(f"Worksheet preacher marker: {worksheet.preacher}")
    if worksheet and worksheet.celebrant:
        notes.append(f"Worksheet celebrant marker: {worksheet.celebrant}")

    return AssembledService(
        service_date=planned.service_date,
        service_type_id=planned.service_type_id,
        template_family=planned.template_family,
        season=planned.season,
        observance=worksheet.description if worksheet and worksheet.description else planned.observance,
        description=worksheet.description if worksheet else None,
        plan_id=plan_id,
        worksheet=worksheet,
        roles=roles,
        songs=songs,
        readings=readings,
        collect=worksheet.collect if worksheet else None,
        proper_preface=worksheet.proper_preface if worksheet else None,
        notes=notes,
    )


def _merge_song_lists(
    worksheet_songs: list[SongAssignment],
    pco_songs: list[SongAssignment],
) -> list[SongAssignment]:
    merged: list[SongAssignment] = []
    total = max(len(worksheet_songs), len(pco_songs))
    for index in range(total):
        worksheet_song = worksheet_songs[index] if index < len(worksheet_songs) else None
        pco_song = pco_songs[index] if index < len(pco_songs) else None
        merged.append(
            SongAssignment(
                slot=f"song_{index + 1}",
                title=(pco_song.title if pco_song and pco_song.title else None)
                or (worksheet_song.title if worksheet_song else None),
            )
        )
    return merged

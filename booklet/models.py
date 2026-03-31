from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class ScriptureReference:
    slot: str
    citation: str


@dataclass
class RoleAssignment:
    slot: str
    first_name: str | None = None


@dataclass
class SongAssignment:
    slot: str
    title: str | None = None


@dataclass
class PassageText:
    slot: str
    citation: str
    query: str
    text: str


@dataclass
class WorksheetService:
    service_date: str
    description: str | None = None
    preacher: str | None = None
    celebrant: str | None = None
    special_theme: str | None = None
    special_elements: str | None = None
    special_volunteers: str | None = None
    compact_readings: str | None = None
    collect: str | None = None
    proper_preface: str | None = None
    songs: list[SongAssignment] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PlannedService:
    service_date: str
    service_type_id: str
    template_family: str
    season: str
    observance: str | None = None
    plan_id: str | None = None
    doc_id: str | None = None
    roles: list[RoleAssignment] = field(default_factory=list)
    songs: list[SongAssignment] = field(default_factory=list)
    readings: list[ScriptureReference] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AssembledService:
    service_date: str
    service_type_id: str
    template_family: str
    season: str
    observance: str | None = None
    description: str | None = None
    plan_id: str | None = None
    worksheet: WorksheetService | None = None
    roles: list[RoleAssignment] = field(default_factory=list)
    songs: list[SongAssignment] = field(default_factory=list)
    readings: list[PassageText] = field(default_factory=list)
    collect: str | None = None
    proper_preface: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

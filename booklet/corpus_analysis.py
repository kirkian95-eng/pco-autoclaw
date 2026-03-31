from __future__ import annotations

import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from googleapiclient.discovery import build

from booklet.config import BookletConfig
from booklet.example_analysis import extract_doc_structure
from booklet.sources.google_docs import load_google_credentials


KEYWORDS = [
    "Ordinary Time",
    "Advent",
    "Lent",
    "Palm Sunday",
    "Epiphany",
    "Christmas",
    "Reading Program",
    "Pentecost",
    "Easter",
    "Passion Sunday",
    "Transfiguration",
    "World Mission Sunday",
    "Holy Week",
]

# Churches can add extra corpus search keywords via BOOKLET_EXTRA_KEYWORDS env var
# (comma-separated). Example: "Kingdom of Dallas,Healing Service"
_extra = os.environ.get("BOOKLET_EXTRA_KEYWORDS", "")
if _extra.strip():
    KEYWORDS.extend(k.strip() for k in _extra.split(",") if k.strip())

NOISE_TOKENS = {
    "ordinary",
    "time",
    "eastertide",
    "advent",
    "lent",
    "epiphany",
    "christmas",
    "easter",
    "palm",
    "sunday",
    "reading",
    "program",
    "kingdom",
    "of",
    "holy",
    "week",
    "proper",
    "first",
    "second",
    "third",
    "fourth",
    "fifth",
    "sixth",
    "seventh",
    "eighth",
    "ninth",
    "last",
    "week",
    "yr",
    "jan",
    "feb",
    "mar",
    "apr",
    "jun",
    "jul",
    "aug",
    "sep",
    "sept",
    "oct",
    "nov",
    "dec",
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "in",
    "the",
    "copy",
    "template",
    "day",
    "programs",
    "program",
    "liturgy",
}
TITLE_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z']+")


@dataclass(frozen=True)
class CorpusDoc:
    doc_id: str
    name: str
    modified_time: str
    family: str
    variants: tuple[str, ...] = field(default_factory=tuple)


def analyze_corpus_rules(config: BookletConfig) -> str:
    docs_service = build("docs", "v1", credentials=load_google_credentials(config))
    corpus_docs = fetch_corpus_docs(config)

    by_family: dict[str, list[dict]] = defaultdict(list)
    for corpus_doc in corpus_docs:
        doc = docs_service.documents().get(documentId=corpus_doc.doc_id).execute()
        significant_lines, normalized_sections = extract_doc_structure(doc)
        by_family[corpus_doc.family].append(
            {
                "doc": corpus_doc,
                "title": doc.get("title", corpus_doc.name),
                "significant_lines": significant_lines,
                "normalized_sections": normalized_sections,
            }
        )

    lines: list[str] = []
    lines.append("# Booklet Corpus Rules")
    lines.append("")
    lines.append(
        f"Derived from {len(corpus_docs)} accessible liturgy-related Google Docs in Drive."
    )
    lines.append("")
    lines.append("## Corpus Inventory")
    family_counts = Counter(doc.family for doc in corpus_docs)
    for family, count in family_counts.most_common():
        lines.append(f"- `{family}`: {count}")
    lines.append("")

    lines.append("## Family Rules")
    for family, docs in sorted(by_family.items(), key=lambda item: (-len(item[1]), item[0])):
        lines.extend(_family_rule_lines(family, docs))
        lines.append("")

    lines.append("## Generator Rules")
    lines.append("- `reading_program` is a separate artifact family from the main leader booklet.")
    lines.append("- Treat sections present in at least 75% of a family as required managed blocks.")
    lines.append("- Treat sections present in 30%-74% of a family as optional family blocks.")
    lines.append("- Preserve logistics and production cues as human-authored unless they are explicitly marked for management.")
    lines.append("- Use title keywords and special-case markers like `alternative liturgy`, `inclement weather`, and `world mission sunday` as variant flags layered on top of the base family.")
    lines.append("- Palm Sunday and Passion/Holy Week style liturgies should not inherit directly from ordinary-time order.")
    lines.append("")
    return "\n".join(lines)


def write_corpus_rules_report(config: BookletConfig, output_path: Path) -> Path:
    report = analyze_corpus_rules(config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return output_path


def fetch_corpus_docs(config: BookletConfig) -> list[CorpusDoc]:
    drive = build("drive", "v3", credentials=load_google_credentials(config))
    seen: dict[str, CorpusDoc] = {}
    for keyword in KEYWORDS:
        page_token = None
        while True:
            response = drive.files().list(
                q=(
                    "mimeType='application/vnd.google-apps.document' "
                    f"and trashed=false and name contains '{keyword}'"
                ),
                fields="nextPageToken, files(id,name,modifiedTime)",
                orderBy="modifiedTime desc",
                pageSize=100,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()
            for file_data in response.get("files", []):
                family, variants = classify_family(file_data["name"])
                seen[file_data["id"]] = CorpusDoc(
                    doc_id=file_data["id"],
                    name=file_data["name"],
                    modified_time=file_data["modifiedTime"],
                    family=family,
                    variants=variants,
                )
            page_token = response.get("nextPageToken")
            if not page_token:
                break
    return sorted(seen.values(), key=lambda doc: doc.modified_time, reverse=True)


def classify_family(name: str) -> tuple[str, tuple[str, ...]]:
    lowered = name.lower()
    variants: list[str] = []
    if "reading program" in lowered or lowered.endswith(" program") or "program " in lowered:
        family = "reading_program"
    elif "palm sunday" in lowered:
        family = "palm_sunday"
    elif "passion sunday" in lowered:
        family = "passion_sunday"
    elif "holy week" in lowered:
        family = "holy_week"
    elif "pentecost" in lowered:
        family = "pentecost"
    elif "easter" in lowered:
        family = "easter"
    elif "lent" in lowered:
        family = "lent"
    elif "advent" in lowered:
        family = "advent"
    elif "christmas" in lowered:
        family = "christmas"
    elif "epiphany" in lowered or "transfiguration" in lowered:
        family = "epiphany"
    elif "ordinary time" in lowered or "proper" in lowered:
        family = "ordinary_time"
    else:
        family = "special"

    _variant_markers = [
        "alternative liturgy",
        "inclement weather",
        "world mission sunday",
        "incarnation sunday",
        "transfiguration",
        "morning prayer",
        "proper",
    ]
    _extra_variants = os.environ.get("BOOKLET_EXTRA_VARIANT_MARKERS", "")
    if _extra_variants.strip():
        _variant_markers.extend(v.strip().lower() for v in _extra_variants.split(",") if v.strip())
    for marker in _variant_markers:
        if marker in lowered:
            variants.append(marker.replace(" ", "_"))
    return family, tuple(variants)


def _family_rule_lines(family: str, docs: list[dict]) -> list[str]:
    total = len(docs)
    section_counts = Counter()
    variant_counts = Counter()
    title_tokens = Counter()
    for doc in docs:
        section_counts.update(set(doc["normalized_sections"]))
        variant_counts.update(doc["doc"].variants)
        title_tokens.update(_salient_title_tokens(doc["title"]))

    required = _sections_by_threshold(section_counts, total, threshold=0.75)
    optional = _sections_by_threshold(section_counts, total, threshold=0.30, upper=0.75)

    lines = [f"### {family}"]
    lines.append(f"- Docs analyzed: {total}")
    if required:
        lines.append(f"- Required blocks: `{', '.join(required[:15])}`")
    if optional:
        lines.append(f"- Optional blocks: `{', '.join(optional[:15])}`")
    if variant_counts:
        lines.append(
            "- Common variants: "
            + ", ".join(f"`{name}` ({count})" for name, count in variant_counts.most_common(8))
        )
    if title_tokens:
        lines.append(
            "- Common title markers: "
            + ", ".join(f"`{token}` ({count})" for token, count in title_tokens.most_common(8))
        )
    lines.extend(_family_observation_lines(family, required, optional))
    return lines


def _family_observation_lines(
    family: str,
    required: list[str],
    optional: list[str],
) -> list[str]:
    observations: list[str] = []
    if family == "ordinary_time":
        observations.append("- Rule: start from the standard leader-booklet order with collect, readings, affirmation/creed, prayers, peace, and offertory flow.")
    elif family == "advent":
        observations.append("- Rule: preserve the Advent-specific gathering shape and expect Advent-title/season framing.")
    elif family == "lent":
        observations.append("- Rule: Lent consistently foregrounds acclamation, penitential material, and affirmation-of-faith rather than a purely ordinary-time order.")
    elif family == "christmas":
        observations.append("- Rule: Christmas often adds seasonal ceremony such as wreath lighting or procession and occasionally includes `collect_for_purity`.")
    elif family == "epiphany":
        observations.append("- Rule: Epiphany is close to ordinary time structurally but carries local variants like inclement-weather and mission/incarnation overlays.")
    elif family == "easter":
        observations.append("- Rule: Easter should be its own family; do not assume Lent or ordinary-time penitential order.")
    elif family == "pentecost":
        observations.append("- Rule: Pentecost needs a seasonal overlay family even if the run of show resembles ordinary time.")
    elif family == "palm_sunday":
        observations.append("- Rule: Palm Sunday is a special liturgy with procession, outdoor start, palm gospel, and distinct prep notes.")
    elif family == "reading_program":
        observations.append("- Rule: reading programs are scripture-reader artifacts, not the main service booklet.")
    elif family == "special":
        observations.append("- Rule: special titles should be reviewed manually before being assigned a base template.")
    return observations


def _sections_by_threshold(
    section_counts: Counter[str],
    total: int,
    threshold: float,
    upper: float | None = None,
) -> list[str]:
    selected = []
    for section, count in section_counts.items():
        ratio = count / total if total else 0
        if ratio >= threshold and (upper is None or ratio < upper):
            selected.append((section, count))
    selected.sort(key=lambda item: (-item[1], item[0]))
    return [section for section, _ in selected]


def _salient_title_tokens(title: str) -> Counter[str]:
    counts = Counter()
    for token in TITLE_TOKEN_RE.findall(title.lower()):
        if token in NOISE_TOKENS:
            continue
        counts[token] += 1
    return counts

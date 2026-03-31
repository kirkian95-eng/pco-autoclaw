from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from googleapiclient.discovery import build

from booklet.config import BookletConfig
from booklet.sources.google_docs import load_google_credentials


@dataclass(frozen=True)
class ExampleDoc:
    family: str
    label: str
    doc_id: str


def _load_example_docs() -> list[ExampleDoc]:
    """Load example docs from BOOKLET_EXAMPLE_DOCS env var.

    Format: comma-separated "family|label|doc_id" triples.
    Example: "advent|Advent 1|1jPW...,lent|Lent 1|1ptl..."

    Returns empty list if not configured (corpus analysis will be skipped).
    """
    raw = os.environ.get("BOOKLET_EXAMPLE_DOCS", "")
    if not raw.strip():
        return []
    docs = []
    for entry in raw.split(","):
        entry = entry.strip()
        parts = entry.split("|")
        if len(parts) == 3:
            docs.append(ExampleDoc(parts[0].strip(), parts[1].strip(), parts[2].strip()))
    return docs


EXAMPLE_DOCS = _load_example_docs()

SIGNIFICANT_STYLES = {"TITLE", "SUBTITLE", "HEADING_1", "HEADING_2", "HEADING_3", "HEADING_4", "HEADING_5"}
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\b")
PARENS_RE = re.compile(r"\([^)]*\)")
PRESET_RE = re.compile(r"^\*Preset:")
MONTH_RE = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
    re.IGNORECASE,
)


def analyze_example_docs(config: BookletConfig) -> str:
    docs_service = build("docs", "v1", credentials=load_google_credentials(config))
    analyses = [_analyze_doc(docs_service, example) for example in EXAMPLE_DOCS]

    family_counter: dict[str, Counter[str]] = {}
    for analysis in analyses:
        family_counter.setdefault(analysis["family"], Counter()).update(
            set(analysis["normalized_sections"])
        )

    all_sections = Counter()
    for analysis in analyses:
        all_sections.update(set(analysis["normalized_sections"]))

    lines: list[str] = []
    lines.append("# Booklet Example Analysis")
    lines.append("")
    lines.append(
        f"Reverse-engineered {len(analyses)} real Google Docs to identify reusable booklet families and managed sections."
    )
    lines.append("")
    lines.append("## Global Patterns")
    for section, count in all_sections.most_common(15):
        lines.append(f"- `{section}` appears in {count}/{len(analyses)} examples")
    lines.append("")
    lines.append("## Family Patterns")
    for family in sorted(family_counter):
        lines.append(f"### {family.replace('_', ' ').title()}")
        for section, count in family_counter[family].most_common(10):
            family_total = sum(1 for analysis in analyses if analysis["family"] == family)
            lines.append(f"- `{section}` appears in {count}/{family_total} examples")
        lines.append("")

    lines.append("## Document Notes")
    for analysis in analyses:
        lines.append(f"### {analysis['label']} ({analysis['title']})")
        lines.append(f"- Family: `{analysis['family']}`")
        lines.append(f"- Significant lines captured: {len(analysis['significant_lines'])}")
        lines.append("- First structural markers:")
        for line in analysis["significant_lines"][:12]:
            lines.append(f"  - `{line['style']}`: {line['text']}")
        lines.append("- Normalized section signature:")
        lines.append(f"  - `{', '.join(_dedupe_preserve_order(analysis['normalized_sections'])[:12])}`")
        lines.append("")

    lines.append("## Generator Implications")
    lines.append("- Keep a season/template-family layer. Ordinary Time, Advent, Lent, Palm Sunday, Christmas, and Epiphany are visibly different.")
    lines.append("- Treat `The Readings`, `Collect for Today`, creed/affirmation, prayers, peace, and preparation-of-gifts style blocks as core managed sections.")
    lines.append("- Preserve stage-direction lines like `*Preset:*`, microphone cues, and manual logistics as human-authored text around the managed sections.")
    lines.append("- Palm Sunday is structurally special enough to need its own family, not a minor variant flag.")
    lines.append("- Reading Programs should remain a separate artifact family from the main leader booklet.")
    lines.append("")
    return "\n".join(lines)


def write_example_analysis_report(config: BookletConfig, output_path: Path) -> Path:
    report = analyze_example_docs(config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    return output_path


def _analyze_doc(docs_service, example: ExampleDoc) -> dict:
    doc = docs_service.documents().get(documentId=example.doc_id).execute()
    significant_lines, normalized_sections = extract_doc_structure(doc)

    return {
        "family": example.family,
        "label": example.label,
        "doc_id": example.doc_id,
        "title": doc.get("title", example.label),
        "significant_lines": significant_lines,
        "normalized_sections": normalized_sections,
    }


def extract_doc_structure(doc: dict) -> tuple[list[dict], list[str]]:
    significant_lines = []
    normalized_sections = []

    for element in doc.get("body", {}).get("content", []):
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        style = paragraph.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
        text = "".join(
            run.get("textRun", {}).get("content", "") for run in paragraph.get("elements", [])
        )
        text = " ".join(text.split())
        if not text:
            continue
        if _is_significant_line(style, text):
            significant_lines.append({"style": style, "text": text})
            normalized = _normalize_section_label(text)
            if normalized:
                normalized_sections.append(normalized)

    return significant_lines, normalized_sections


def _is_significant_line(style: str, text: str) -> bool:
    if PRESET_RE.match(text):
        return False
    if style in SIGNIFICANT_STYLES:
        return True
    return text.upper() == text and len(text) > 10


def _normalize_section_label(text: str) -> str | None:
    text = TIME_RE.sub("", text)
    text = PARENS_RE.sub("", text)
    text = text.replace("&", " and ")
    text = re.sub(r"\s+", " ", text).strip(" :-")
    lowered = text.lower()
    if not lowered:
        return None
    if PRESET_RE.match(text):
        return None
    if re.match(r"^\d", text):
        return None
    if "sunday" in lowered and MONTH_RE.search(lowered):
        return None
    if lowered in {"sunday", "sunday,", "10:30 am sunday,", "10:30 am sunday", "10:30 am"}:
        return None
    if lowered.startswith("song "):
        return "song_slot"
    if lowered.startswith("welcome"):
        return "welcome"
    if lowered == "sermon":
        return "sermon"
    if lowered == "homily":
        return "sermon"
    if "collect for today" in lowered:
        return "collect_for_today"
    if "collect for purity" in lowered:
        return "collect_for_purity"
    if "the readings" in lowered:
        return "readings"
    if "the lessons" in lowered:
        return "lessons"
    if "gospel reading" in lowered:
        return "gospel_reading"
    if "nicene creed" in lowered:
        return "nicene_creed"
    if "affirmation of faith" in lowered:
        return "affirmation_of_faith"
    if "prayers of the people" in lowered:
        return "prayers_of_the_people"
    if "lord’s prayer" in lowered or "lord's prayer" in lowered:
        return "lords_prayer"
    if "summary of the law" in lowered:
        return "summary_of_the_law"
    if "confession" in lowered:
        return "confession"
    if "absolution" in lowered:
        return "absolution"
    if "kyrie" in lowered:
        return "kyrie"
    if "peace" in lowered:
        return "peace"
    if "preparation of the gifts" in lowered:
        return "preparation_of_the_gifts"
    if "gathering of the community" in lowered:
        return "gathering_of_the_community"
    if "acclamation" in lowered:
        return "acclamation"
    if "doxology" in lowered:
        return "doxology"
    if "palm gospel" in lowered:
        return "palm_gospel"
    if "procession" in lowered:
        return "procession"
    if "announcements" in lowered:
        return "announcements"
    if "offering" in lowered:
        return "offering"
    if "remaining outside" in lowered:
        return "remaining_outside"
    if "children’s dismissal" in lowered or "children's dismissal" in lowered:
        return "childrens_dismissal"
    if "new member presentation" in lowered:
        return "new_member_presentation"
    if "gathering in the name of jesus" in lowered:
        return "gathering_in_the_name_of_jesus"
    if "gathering outdoors in the name of jesus" in lowered:
        return "gathering_outdoors_in_the_name_of_jesus"
    if "liturgy of the palms" in lowered:
        return "liturgy_of_the_palms_passion_reading_and_eucharist"
    if lowered.startswith("first sunday") or lowered.startswith("second sunday") or lowered.startswith("third sunday") or lowered.startswith("fourth sunday") or lowered.startswith("fifth sunday"):
        return "service_title"
    if lowered.startswith("ordinary time") or lowered.startswith("palm sunday") or lowered.startswith("christmas") or lowered.startswith("epiphany"):
        return "service_title"
    if len(lowered.split()) > 6:
        return None
    return lowered[:80].replace(" ", "_")


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result

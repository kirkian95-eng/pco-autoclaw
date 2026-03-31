from __future__ import annotations

from dataclasses import asdict, dataclass, field

from googleapiclient.discovery import build

from booklet.config import BookletConfig
from booklet.example_analysis import _is_significant_line, _normalize_section_label
from booklet.master_templates import FamilyTemplate, get_family_template
from booklet.sources.google_docs import load_google_credentials


@dataclass
class ParagraphProfile:
    start_index: int
    end_index: int
    text: str
    style: str
    alignment: str | None


@dataclass
class SectionProfile:
    key: str
    heading_text: str
    heading_style: str
    heading_start_index: int
    content_start_index: int
    content_end_index: int
    sample_paragraphs: list[ParagraphProfile] = field(default_factory=list)


@dataclass
class TemplateProfile:
    family: str
    template_doc_id: str
    template_title: str
    provisional: bool
    title_lines: list[ParagraphProfile] = field(default_factory=list)
    front_matter_lines: list[ParagraphProfile] = field(default_factory=list)
    sections: list[SectionProfile] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def build_template_profile(config: BookletConfig, family: str) -> TemplateProfile:
    template = get_family_template(family)
    docs = build("docs", "v1", credentials=load_google_credentials(config))
    document = docs.documents().get(documentId=template.doc_id).execute()
    paragraphs = _extract_paragraphs(document)

    title_lines = [p for p in paragraphs[:6] if p.style == "TITLE"]
    front_matter_lines = []
    for paragraph in paragraphs:
        if paragraph.style in {"TITLE", "HEADING_1"}:
            continue
        if paragraph.text.startswith("Welcome"):
            break
        front_matter_lines.append(paragraph)

    sections: list[SectionProfile] = []
    significant_indices = []
    for idx, paragraph in enumerate(paragraphs):
        if _is_significant_line(paragraph.style, paragraph.text):
            normalized = _normalize_section_label(paragraph.text)
            if normalized:
                significant_indices.append((idx, normalized))

    for pos, (idx, section_key) in enumerate(significant_indices):
        paragraph = paragraphs[idx]
        next_idx = significant_indices[pos + 1][0] if pos + 1 < len(significant_indices) else len(paragraphs)
        content_start = paragraph.end_index
        content_end = paragraphs[next_idx].start_index if next_idx < len(paragraphs) else paragraphs[-1].end_index
        sections.append(
            SectionProfile(
                key=section_key,
                heading_text=paragraph.text,
                heading_style=paragraph.style,
                heading_start_index=paragraph.start_index,
                content_start_index=content_start,
                content_end_index=content_end,
                sample_paragraphs=paragraphs[idx + 1: min(next_idx, idx + 6)],
            )
        )

    return TemplateProfile(
        family=family,
        template_doc_id=template.doc_id,
        template_title=template.title,
        provisional=template.provisional,
        title_lines=title_lines,
        front_matter_lines=front_matter_lines[:10],
        sections=sections,
    )


def render_template_profile_markdown(config: BookletConfig, family: str) -> str:
    template = get_family_template(family)
    profile = build_template_profile(config, family)
    lines = [
        f"# {family.replace('_', ' ').title()} Template Profile",
        "",
        f"- Source doc: `{template.title}`",
        f"- Doc ID: `{template.doc_id}`",
        f"- Source type: `{template.source}`",
        f"- Provisional: `{template.provisional}`",
        "",
        "## Title Lines",
    ]
    for line in profile.title_lines:
        lines.append(f"- `{line.style}` `{line.alignment}`: {line.text}")
    lines.append("")
    lines.append("## Front Matter")
    for line in profile.front_matter_lines:
        lines.append(f"- `{line.style}` `{line.alignment}`: {line.text}")
    lines.append("")
    lines.append("## Sections")
    for section in profile.sections:
        lines.append(
            f"- `{section.key}` heading `{section.heading_text}` range `{section.content_start_index}:{section.content_end_index}`"
        )
        for sample in section.sample_paragraphs[:3]:
            lines.append(f"  - `{sample.style}`: {sample.text[:140]}")
    lines.append("")
    return "\n".join(lines)


def _extract_paragraphs(document: dict) -> list[ParagraphProfile]:
    paragraphs: list[ParagraphProfile] = []
    for element in document.get("body", {}).get("content", []):
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        text = "".join(
            run.get("textRun", {}).get("content", "") for run in paragraph.get("elements", [])
        ).strip("\n")
        if not text.strip():
            continue
        paragraph_style = paragraph.get("paragraphStyle", {})
        paragraphs.append(
            ParagraphProfile(
                start_index=element["startIndex"],
                end_index=element["endIndex"],
                text=" ".join(text.split()),
                style=paragraph_style.get("namedStyleType", "NORMAL_TEXT"),
                alignment=paragraph_style.get("alignment"),
            )
        )
    return paragraphs

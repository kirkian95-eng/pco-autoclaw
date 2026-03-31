from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys


REPO_ROOT = "/home/ubuntu/pco-autoclaw"
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from booklet.reference_resolver import resolve_sunday_reference


CLI = f"{REPO_ROOT}/booklet_cli.py"
FORMATTER = f"{REPO_ROOT}/booklet/response_formatter.py"
WRITE_ACTIONS = {"make", "make_attach", "update", "update_attach", "link", "attach"}
INFO_ACTIONS = {"songs", "roles", "readings", "preview"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve a booklet request and execute it.")
    parser.add_argument("parts", nargs="+")
    args = parser.parse_args()

    intent, query = _parse_request_parts(args.parts)
    if not intent:
        print(_action_help_message(query))
        return 0

    resolution = resolve_sunday_reference(query)
    if resolution.status != "resolved":
        print(resolution.message or f'Could not resolve "{query}".')
        return 0

    if intent in WRITE_ACTIONS:
        return _run_write_intent(intent, resolution.resolved.service_date.isoformat(), resolution.resolved.template_family)
    return _run_info_intent(intent, resolution.resolved.service_date.isoformat(), resolution.resolved.template_family)


def _run_write_intent(intent: str, service_date: str, template_family: str) -> int:
    cmd = _command_for_write_intent(intent, service_date, template_family)
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    output = _format_write_output(result)

    if output:
        print(output)
    if result.returncode in {0, 1}:
        return result.returncode
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def _run_info_intent(intent: str, service_date: str, template_family: str) -> int:
    result = subprocess.run(
        [
            "python3",
            CLI,
            "preview-service",
            "--date",
            service_date,
            "--template-family",
            template_family,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.strip())
        return result.returncode

    payload = json.loads(result.stdout)
    print(_format_info_response(intent, payload))
    return 0


def _parse_request_parts(parts: list[str]) -> tuple[str | None, str]:
    valid = WRITE_ACTIONS | INFO_ACTIONS
    if parts and parts[0] in valid:
        return parts[0], " ".join(parts[1:]).strip()
    text = " ".join(parts).strip()
    return _infer_action(text), text


def _infer_action(text: str) -> str | None:
    lowered = text.lower()
    wants_attach = _matches_any(
        lowered,
        (
            r"\b(attach|upload|publish)\b.*\b(pdf|planning center|pco)\b",
            r"\bplanning center\b.*\b(pdf|file|attachment)\b",
        ),
    )
    if wants_attach and _matches_any(
        lowered,
        (
            r"\b(make|generate|create|build)\b",
        ),
    ):
        return "make_attach"
    if wants_attach and _matches_any(
        lowered,
        (
            r"\b(update|refresh|sync|revise|edit)\b",
        ),
    ):
        return "update_attach"
    if _matches_any(
        lowered,
        (
            r"\b(send|show|get|give)\b.*\blink\b",
            r"\blink\b",
        ),
    ):
        return "link"
    if wants_attach:
        return "attach"
    if _matches_any(
        lowered,
        (
            r"\b(update|refresh|sync|revise|edit)\b",
        ),
    ):
        return "update"
    if _matches_any(
        lowered,
        (
            r"\b(make|generate|create|build)\b",
        ),
    ):
        return "make"
    if _matches_any(
        lowered,
        (
            r"\bwhat songs\b",
            r"\bsongs\b",
            r"\bsinging\b",
        ),
    ):
        return "songs"
    if _matches_any(
        lowered,
        (
            r"\bwho('?s| is)?\s+serving\b",
            r"\bwho('?s| is)?\s+on\b",
            r"\bvolunteers?\b",
            r"\bparticipants?\b",
            r"\bservers?\b",
        ),
    ):
        return "roles"
    if _matches_any(
        lowered,
        (
            r"\breadings?\b",
            r"\bscripture\b",
            r"\bpassages?\b",
            r"\bwhat do we read\b",
        ),
    ):
        return "readings"
    if _matches_any(
        lowered,
        (
            r"\bpreview\b",
            r"\bdetails\b",
            r"\bliturgy\b",
            r"\bservice\b",
        ),
    ):
        return "preview"
    return None


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _format_write_output(result: subprocess.CompletedProcess[str]) -> str:
    if result.stdout:
        formatted = subprocess.run(
            ["python3", FORMATTER],
            cwd=REPO_ROOT,
            input=result.stdout,
            capture_output=True,
            text=True,
        )
        return formatted.stdout.strip() or result.stdout.strip()
    return result.stderr.strip()


def _command_for_write_intent(intent: str, service_date: str, template_family: str) -> list[str]:
    if intent == "make" or intent == "make_attach":
        return [
            "python3",
            CLI,
            "generate-booklet",
            "--date",
            service_date,
            "--template-family",
            template_family,
            "--attach-pdf-to-pco",
        ]
    if intent == "update" or intent == "update_attach":
        return [
            "python3",
            CLI,
            "update-booklet",
            "--date",
            service_date,
            "--template-family",
            template_family,
            "--attach-pdf-to-pco",
        ]
    if intent == "attach":
        return [
            "python3",
            CLI,
            "attach-booklet-pdf",
            "--date",
            service_date,
        ]
    return [
        "python3",
        CLI,
        "get-booklet-link",
        "--date",
        service_date,
    ]


def _format_info_response(intent: str, payload: dict) -> str:
    observance = payload.get("observance") or payload.get("description") or payload.get("service_date")
    service_date = payload.get("service_date")
    songs = [song.get("title") for song in payload.get("songs") or [] if song.get("title")]
    roles = [
        f"{_pretty_slot(role.get('slot', 'participant'))}: {role.get('first_name')}"
        for role in payload.get("roles") or []
        if role.get("first_name")
    ]
    readings = [reading.get("citation") for reading in payload.get("readings") or [] if reading.get("citation")]
    notes = payload.get("notes") or []

    if intent == "songs":
        if songs:
            return f"For {observance} on {service_date}, the planned songs are: {', '.join(songs)}."
        return _fallback_note(service_date, "I do not have any planned songs yet.", notes)

    if intent == "roles":
        if roles:
            return f"For {observance} on {service_date}, the current serving assignments are: {', '.join(roles)}."
        return _fallback_note(service_date, "I do not have any Planning Center serving assignments yet.", notes)

    if intent == "readings":
        if readings:
            return f"For {observance} on {service_date}, the readings are: {', '.join(readings)}."
        return f"I do not have readings loaded for {service_date}."

    summary_parts = [f"{observance} on {service_date}"]
    if songs:
        summary_parts.append(f"songs: {', '.join(songs)}")
    if readings:
        summary_parts.append(f"readings: {', '.join(readings)}")
    if roles:
        summary_parts.append(f"serving: {', '.join(roles)}")
    return " | ".join(summary_parts)


def _fallback_note(service_date: str | None, default: str, notes: list[str]) -> str:
    if notes:
        return f"{default} For {service_date}, note: {notes[0]}"
    return default


def _pretty_slot(slot: str) -> str:
    return slot.replace("_", " ").title()


def _action_help_message(query: str) -> str:
    if query:
        return (
            f'I understood the Sunday reference "{query}", but I still need the action. '
            "Say whether you want me to make it, update it, send the link, attach the PDF to Planning Center, give the songs, give the readings, or list who is serving."
        )
    return "Tell me whether you want me to make the booklet, update it, send the link, attach the PDF to Planning Center, give the songs, give the readings, or list who is serving."


if __name__ == "__main__":
    raise SystemExit(main())

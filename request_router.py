from __future__ import annotations

import argparse
import re
import subprocess
import sys


REPO_ROOT = "/home/ubuntu/pco-autoclaw"
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from booklet.reference_resolver import SundayResolution, resolve_sunday_reference


CLI = f"{REPO_ROOT}/booklet_cli.py"
FORMATTER = f"{REPO_ROOT}/booklet/response_formatter.py"
ACTIONS = {"make", "update", "link"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve a booklet request and execute it.")
    parser.add_argument("parts", nargs="+")
    args = parser.parse_args()

    action, query = _parse_request_parts(args.parts)
    if not action:
        print(_action_help_message(query))
        return 0

    resolution = resolve_sunday_reference(query)
    if resolution.status != "resolved":
        print(resolution.message or f'Could not resolve "{query}".')
        return 0

    cmd = _command_for(
        action,
        resolution.resolved.service_date.isoformat(),
        resolution.resolved.template_family,
    )
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    output = _format_output(result)

    if output:
        print(output)
    if result.returncode in {0, 1}:
        return result.returncode
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def _parse_request_parts(parts: list[str]) -> tuple[str | None, str]:
    if parts and parts[0] in ACTIONS:
        return parts[0], " ".join(parts[1:]).strip()
    text = " ".join(parts).strip()
    return _infer_action(text), text


def _infer_action(text: str) -> str | None:
    lowered = text.lower()
    if _matches_any(
        lowered,
        (
            r"\b(send|show|get|give)\b.*\blink\b",
            r"\blink\b",
        ),
    ):
        return "link"
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
    return None


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _format_output(result: subprocess.CompletedProcess[str]) -> str:
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


def _command_for(action: str, service_date: str, template_family: str) -> list[str]:
    if action == "make":
        return [
            "python3",
            CLI,
            "generate-booklet",
            "--date",
            service_date,
            "--template-family",
            template_family,
        ]
    if action == "update":
        return [
            "python3",
            CLI,
            "update-booklet",
            "--date",
            service_date,
            "--template-family",
            template_family,
        ]
    return [
        "python3",
        CLI,
        "get-booklet-link",
        "--date",
        service_date,
    ]


def _action_help_message(query: str) -> str:
    if query:
        return (
            f'I understood the Sunday reference "{query}", but I still need the action. '
            'Say whether you want me to make it, update it, or send the link.'
        )
    return "Tell me whether you want me to make the booklet, update it, or send the link."


if __name__ == "__main__":
    raise SystemExit(main())

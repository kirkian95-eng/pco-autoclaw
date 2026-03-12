#!/usr/bin/env bash
# Unified CLI for pco-autoclaw. Stephen calls this via exec.
# All subcommands print plain text output (not JSON) for easy relay to Kirk.
set -euo pipefail
cd "$(dirname "$0")"

CMD="${1:-help}"
shift 2>/dev/null || true

case "$CMD" in
  # ── Lookups ──────────────────────────────────────────────
  who-serving)
    # Usage: pco.sh who-serving [service_type_id]
    python3 pco_client.py who-serving "$@"
    ;;
  who-available)
    # Usage: pco.sh who-available <team_id> [service_type_id]
    python3 pco_client.py who-available "$@"
    ;;
  not-responded)
    # Usage: pco.sh not-responded [service_type_id]
    python3 pco_client.py not-responded "$@"
    ;;
  last-served)
    # Usage: pco.sh last-served <name>
    python3 pco_client.py last-served "$@"
    ;;
  volunteer-report)
    # Usage: pco.sh volunteer-report [service_type_id]
    python3 pco_client.py volunteer-report "$@"
    ;;

  # ── Scheduling ───────────────────────────────────────────
  needs)
    python3 scheduler.py --dry-run
    ;;
  schedule)
    python3 scheduler.py
    ;;
  status)
    python3 scheduler.py --status
    ;;

  # ── Declines ─────────────────────────────────────────────
  poll)
    python3 poller.py
    ;;
  approve)
    python3 poller.py --approve
    ;;
  summary)
    python3 poller.py --summary
    ;;

  # ── Discovery ────────────────────────────────────────────
  service-types)
    python3 pco_client.py list-service-types
    ;;
  teams)
    python3 pco_client.py list-teams "$@"
    ;;
  plans)
    python3 pco_client.py list-plans "$@"
    ;;
  show-plan)
    python3 pco_client.py show-plan "$@"
    ;;

  # ── Help ─────────────────────────────────────────────────
  help|*)
    cat <<'HELP'
pco.sh — Planning Center volunteer scheduling

Lookups:
  who-serving [st_id]         Who's on the next upcoming service
  who-available <team_id>     Who's eligible and not blocked out
  not-responded [st_id]       People who haven't accepted/declined yet
  last-served <name>          When did this person last serve
  volunteer-report [st_id]    Service counts per person (fairness check)

Scheduling:
  needs                       Dry run — show unfilled positions + candidates
  schedule                    Live schedule (fills unfilled positions)
  status                      Current status (JSON)

Declines:
  poll                        Check for new declines, recommend replacements
  approve                     Approve all pending replacements
  summary                     Morning summary (sends Telegram too)

Discovery:
  service-types               List all service types
  teams <st_id>               List teams for a service type
  plans <st_id> [days]        List upcoming plans
  show-plan <st_id> <plan_id> Show who's on a specific plan
HELP
    ;;
esac

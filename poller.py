#!/usr/bin/env python3
"""Decline detection poller — finds declines, recommends replacements, notifies Kirk."""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from pco_client import PCOClient
from scheduler import VolunteerScheduler, SchedulingNeed, normalize_status

load_dotenv(os.path.join(os.path.dirname(__file__), "config.env"))

DATA_DIR = Path(__file__).parent / "data"
LAST_POLL_FILE = DATA_DIR / "last_poll.json"
STATUS_FILE = Path("/tmp/pco-scheduler-status.json")
PENDING_FILE = DATA_DIR / "pending_replacements.json"
SEND_TELEGRAM = Path(os.path.expanduser("~/.local/bin/send-telegram.sh"))


def notify(message: str):
    if not SEND_TELEGRAM.exists():
        print(f"[NOTIFY] {message}")
        return
    try:
        subprocess.run([str(SEND_TELEGRAM), message], timeout=10, capture_output=True)
    except Exception:
        print(f"[NOTIFY FAILED] {message}")


def load_last_poll() -> dict:
    if LAST_POLL_FILE.exists():
        with open(LAST_POLL_FILE) as f:
            return json.load(f)
    return {"last_checked": None, "known_declines": []}


def save_last_poll(data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    tmp = str(LAST_POLL_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.rename(tmp, str(LAST_POLL_FILE))


def load_pending() -> list[dict]:
    if PENDING_FILE.exists():
        with open(PENDING_FILE) as f:
            return json.load(f)
    return []


def save_pending(pending: list[dict]):
    # Prune entries older than 30 days that are no longer pending
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    pruned = []
    for item in pending:
        if item.get("status") == "pending_approval":
            pruned.append(item)  # Always keep pending items
        elif item.get("timestamp"):
            try:
                ts = datetime.fromisoformat(item["timestamp"])
                if ts > cutoff:
                    pruned.append(item)  # Keep recent completed/errored
            except ValueError:
                pruned.append(item)
        else:
            pruned.append(item)

    DATA_DIR.mkdir(exist_ok=True)
    tmp = str(PENDING_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(pruned, f, indent=2)
    os.rename(tmp, str(PENDING_FILE))


def poll_for_declines():
    """Check for new declines and recommend replacements (notify-first mode)."""
    client = PCOClient()
    scheduler = VolunteerScheduler(client)
    last_poll = load_last_poll()
    known_declines = set(tuple(d) for d in last_poll.get("known_declines", []))

    service_type_ids = [
        s.strip()
        for s in os.getenv("PCO_SERVICE_TYPE_IDS", "").split(",")
        if s.strip()
    ]

    new_declines = []
    pending_replacements = load_pending()

    for st_id in service_type_ids:
        plans = client.get_upcoming_plans(st_id, int(os.getenv("SCHEDULE_ADVANCE_DAYS", "21")))

        for plan in plans:
            plan_id = plan["id"]
            plan_date = plan["attributes"].get("sort_date", "")[:10]
            team_members = client.get_plan_team_members(st_id, plan_id)

            for tm in team_members:
                attrs = tm["attributes"]
                status = attrs.get("status", "")

                if normalize_status(status) != "declined":
                    continue

                person_name = attrs.get("name", "Unknown")
                position = attrs.get("team_position_name", "Unknown")
                decline_key = (st_id, plan_id, tm["id"])

                if decline_key in known_declines:
                    continue

                # New decline found
                known_declines.add(decline_key)
                new_declines.append({
                    "service_type_id": st_id,
                    "plan_id": plan_id,
                    "plan_date": plan_date,
                    "team_member_id": tm["id"],
                    "person_name": person_name,
                    "position": position,
                })

                # Find the team_id for this position
                team_id = ""
                rels = tm.get("relationships", {})
                team_data = rels.get("team", {}).get("data", {})
                if team_data.get("id"):
                    team_id = team_data["id"]

                # Build replacement candidates
                if team_id:
                    need = SchedulingNeed(
                        service_type_id=st_id,
                        service_type_name="",
                        plan_id=plan_id,
                        plan_date=plan_date,
                        team_id=team_id,
                        team_name="",
                        position_name=position,
                    )
                    candidates = scheduler.build_eligibility_list(need)

                    if candidates:
                        best = candidates[0]
                        # Save as pending replacement (notify-first mode)
                        pending_replacements.append({
                            "decline_person": person_name,
                            "position": position,
                            "plan_date": plan_date,
                            "service_type_id": st_id,
                            "plan_id": plan_id,
                            "team_id": team_id,
                            "recommended_person_id": best.person_id,
                            "recommended_name": best.name,
                            "recommended_last_served": best.last_served,
                            "recommended_days_since": best.days_since,
                            "status": "pending_approval",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

                        notify(
                            f"PCO: {person_name} declined {position} on {plan_date}\n"
                            f"Recommended replacement: {best.name} "
                            f"(last served {best.last_served}, {best.days_since}d ago)\n"
                            f"Reply to Stephen with '/schedule approve' to confirm."
                        )
                    else:
                        # No candidates — escalate
                        notify(
                            f"PCO: {person_name} declined {position} on {plan_date}\n"
                            f"No eligible replacements found. Manual action needed."
                        )
                else:
                    notify(
                        f"PCO: {person_name} declined {position} on {plan_date}\n"
                        f"Could not determine team for auto-replacement."
                    )

    # Save state
    save_last_poll({
        "last_checked": datetime.now(timezone.utc).isoformat(),
        "known_declines": [list(d) for d in known_declines],
    })
    save_pending(pending_replacements)

    # Update status file
    scheduler.write_status()

    if new_declines:
        print(f"Found {len(new_declines)} new decline(s).")
    else:
        print("No new declines.")

    return new_declines


def approve_pending():
    """Approve all pending replacements and schedule them."""
    client = PCOClient()
    pending = load_pending()
    approved = []

    for item in pending:
        if item["status"] != "pending_approval":
            continue

        try:
            result = client.schedule_person(
                item["service_type_id"],
                item["plan_id"],
                item["recommended_person_id"],
                item["team_id"],
            )
            item["status"] = "approved"
            approved.append(item)
            print(f"Scheduled {item['recommended_name']} for {item['position']} on {item['plan_date']}")
            notify(
                f"PCO: Approved — {item['recommended_name']} scheduled for "
                f"{item['position']} on {item['plan_date']}"
            )
        except Exception as e:
            print(f"Error scheduling {item['recommended_name']}: {e}")
            item["status"] = "error"
            item["error"] = str(e)

    save_pending(pending)
    print(f"Approved {len(approved)} replacement(s).")
    return approved


def generate_summary():
    """Generate and send morning summary."""
    client = PCOClient()
    scheduler = VolunteerScheduler(client)
    scheduler.write_status()

    with open(STATUS_FILE) as f:
        status = json.load(f)

    lines = [f"PCO Scheduling — {datetime.now().strftime('%b %d')}"]
    lines.append("")

    for plan in status.get("upcoming_plans", []):
        needed = plan.get("needed", 0)
        pending = plan.get("pending", 0)
        confirmed = plan.get("confirmed", 0)
        declined = plan.get("declined", 0)

        status_parts = []
        if needed:
            status_parts.append(f"{needed} unfilled")
        if pending:
            status_parts.append(f"{pending} pending")
        if confirmed:
            status_parts.append(f"{confirmed} confirmed")
        if declined:
            status_parts.append(f"{declined} declined")

        if not status_parts:
            status_parts = ["fully staffed"]

        lines.append(f"  {plan['date']}: {', '.join(status_parts)}")

    # Check pending replacements
    pending_reps = load_pending()
    awaiting = [p for p in pending_reps if p["status"] == "pending_approval"]
    if awaiting:
        lines.append(f"\n{len(awaiting)} replacement(s) awaiting your approval.")
        lines.append("Reply '/schedule approve' to confirm all.")

    if not status.get("upcoming_plans"):
        lines.append("  No upcoming plans found.")

    summary = "\n".join(lines)
    print(summary)
    notify(summary)


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        cmd = sys.argv[1]
        if cmd == "--summary":
            generate_summary()
        elif cmd == "--approve":
            approve_pending()
        elif cmd == "--status":
            # Just write status, no decline handling
            scheduler = VolunteerScheduler()
            scheduler.write_status()
            with open(STATUS_FILE) as f:
                print(json.dumps(json.load(f), indent=2))
        else:
            print(f"Unknown flag: {cmd}")
            print("Usage: python3 poller.py [--summary|--approve|--status]")
            sys.exit(1)
    else:
        poll_for_declines()

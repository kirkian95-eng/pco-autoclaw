#!/usr/bin/env python3
"""Core volunteer scheduling logic — scan needs, rank candidates, schedule."""

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from pco_client import PCOClient

load_dotenv(os.path.join(os.path.dirname(__file__), "config.env"))

DATA_DIR = Path(__file__).parent / "data"
LOG_FILE = DATA_DIR / "schedule_log.jsonl"
STATUS_FILE = Path("/tmp/pco-scheduler-status.json")
SEND_TELEGRAM = Path(os.path.expanduser("~/.local/bin/send-telegram.sh"))


@dataclass
class SchedulingNeed:
    service_type_id: str
    service_type_name: str
    plan_id: str
    plan_date: str
    team_id: str
    team_name: str
    position_name: str
    quantity: int = 1


@dataclass
class Candidate:
    person_id: str
    name: str
    last_served: str  # ISO date or "never"
    days_since: int = 999  # days since last served


class VolunteerScheduler:
    def __init__(self, client: PCOClient = None):
        self.client = client or PCOClient()
        self.advance_days = int(os.getenv("SCHEDULE_ADVANCE_DAYS", "21"))
        self.min_days_between = int(os.getenv("SCHEDULE_MIN_DAYS_BETWEEN", "14"))
        self.lookback_months = int(os.getenv("SCHEDULE_LOOKBACK_MONTHS", "6"))
        self.service_type_ids = [
            s.strip()
            for s in os.getenv("PCO_SERVICE_TYPE_IDS", "").split(",")
            if s.strip()
        ]
        self.notify = os.getenv("TELEGRAM_NOTIFY", "1") == "1"
        DATA_DIR.mkdir(exist_ok=True)

    def scan_upcoming_needs(self) -> list[SchedulingNeed]:
        """Find all unfilled positions across configured service types."""
        needs = []
        for st_id in self.service_type_ids:
            # Get service type name
            service_types = self.client.get_service_types()
            st_name = next(
                (st["attributes"]["name"] for st in service_types if st["id"] == st_id),
                f"ServiceType#{st_id}",
            )

            plans = self.client.get_upcoming_plans(st_id, self.advance_days)
            for plan in plans:
                plan_id = plan["id"]
                plan_date = plan["attributes"].get("sort_date", "unknown")

                needed = self.client.get_needed_positions(st_id, plan_id)
                for pos in needed:
                    attrs = pos["attributes"]
                    # Try to extract team info from the needed position
                    team_id = ""
                    team_name = ""
                    if "relationships" in pos:
                        team_rel = pos["relationships"].get("team", {})
                        if team_rel.get("data"):
                            team_id = team_rel["data"]["id"]

                    needs.append(SchedulingNeed(
                        service_type_id=st_id,
                        service_type_name=st_name,
                        plan_id=plan_id,
                        plan_date=plan_date[:10] if len(plan_date) >= 10 else plan_date,
                        team_id=team_id,
                        team_name=attrs.get("team_position_name", attrs.get("title", "Unknown")),
                        position_name=attrs.get("team_position_name", attrs.get("title", "Unknown")),
                        quantity=attrs.get("quantity", 1),
                    ))
        return needs

    def build_eligibility_list(self, need: SchedulingNeed) -> list[Candidate]:
        """Build a ranked list of eligible candidates for a position."""
        if not need.team_id:
            return []

        # Get team roster
        roster = self.client.get_team_members(need.service_type_id, need.team_id)

        # Get who's already on this plan
        existing = self.client.get_plan_team_members(need.service_type_id, need.plan_id)
        existing_person_ids = set()
        for tm in existing:
            rels = tm.get("relationships", {})
            person_data = rels.get("person", {}).get("data", {})
            if person_data.get("id"):
                existing_person_ids.add(person_data["id"])

        now = datetime.now(timezone.utc)
        candidates = []

        for member in roster:
            person_id = None
            rels = member.get("relationships", {})
            person_data = rels.get("person", {}).get("data", {})
            if person_data.get("id"):
                person_id = person_data["id"]

            if not person_id:
                continue

            # Skip if already on this plan
            if person_id in existing_person_ids:
                continue

            name = member["attributes"].get("name", f"Person#{person_id}")

            # Check blockout dates
            try:
                blockouts = self.client.get_blockout_dates(person_id)
                blocked = self._is_blocked_out(blockouts, need.plan_date)
                if blocked:
                    continue
            except Exception:
                pass  # If we can't check blockouts, don't block the person

            # Get schedule history for rotation fairness
            last_served, days_since = self._get_last_served(person_id, now)

            # Skip if served too recently
            if days_since < self.min_days_between:
                continue

            candidates.append(Candidate(
                person_id=person_id,
                name=name,
                last_served=last_served,
                days_since=days_since,
            ))

        # Sort by longest wait first
        candidates.sort(key=lambda c: -c.days_since)
        return candidates

    def _is_blocked_out(self, blockouts: list[dict], plan_date: str) -> bool:
        """Check if any blockout overlaps with the plan date."""
        try:
            plan_dt = datetime.strptime(plan_date[:10], "%Y-%m-%d").date()
        except ValueError:
            return False

        for bo in blockouts:
            attrs = bo.get("attributes", {})
            starts = attrs.get("starts_at", "")
            ends = attrs.get("ends_at", "")
            if starts and ends:
                try:
                    start_dt = datetime.fromisoformat(starts.replace("Z", "+00:00")).date()
                    end_dt = datetime.fromisoformat(ends.replace("Z", "+00:00")).date()
                    if start_dt <= plan_dt <= end_dt:
                        return True
                except ValueError:
                    continue
        return False

    def _get_last_served(self, person_id: str, now: datetime) -> tuple[str, int]:
        """Get the last date a person served and days since."""
        try:
            schedules = self.client.get_person_schedules(person_id, self.lookback_months)
            if not schedules:
                return "never", 999

            # Find the most recent confirmed schedule
            latest = None
            for sched in schedules:
                attrs = sched.get("attributes", {})
                status = attrs.get("status", "")
                if status in ("C", "confirmed", "Confirmed"):
                    plan_date = attrs.get("sort_date", attrs.get("created_at", ""))
                    if plan_date and (latest is None or plan_date > latest):
                        latest = plan_date

            if not latest:
                return "never", 999

            last_dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
            days = (now - last_dt).days
            return latest[:10], max(days, 0)
        except Exception:
            return "unknown", 500

    def schedule_candidate(
        self, need: SchedulingNeed, candidate: Candidate, dry_run: bool = False
    ) -> dict:
        """Schedule a candidate for a position."""
        action = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "schedule",
            "service_type_id": need.service_type_id,
            "plan_id": need.plan_id,
            "plan_date": need.plan_date,
            "position": need.position_name,
            "team_id": need.team_id,
            "person_id": candidate.person_id,
            "person_name": candidate.name,
            "last_served": candidate.last_served,
            "days_since": candidate.days_since,
            "dry_run": dry_run,
        }

        if dry_run:
            action["result"] = "dry_run"
            print(f"  [DRY RUN] Would schedule {candidate.name} for {need.position_name} "
                  f"on {need.plan_date} (last served: {candidate.last_served}, "
                  f"{candidate.days_since} days ago)")
        else:
            # Check idempotency
            if self._already_scheduled(need, candidate):
                action["result"] = "already_scheduled"
                print(f"  [SKIP] {candidate.name} already scheduled for this position")
                return action

            try:
                result = self.client.schedule_person(
                    need.service_type_id, need.plan_id,
                    candidate.person_id, need.team_id,
                )
                action["result"] = "scheduled"
                action["api_response_id"] = result.get("data", {}).get("id", "")
                print(f"  [SCHEDULED] {candidate.name} for {need.position_name} "
                      f"on {need.plan_date}")
                self._notify(
                    f"PCO: Scheduled {candidate.name} for {need.position_name} "
                    f"on {need.plan_date} ({need.service_type_name})\n"
                    f"Reason: longest wait (last served {candidate.last_served}, "
                    f"{candidate.days_since} days ago)"
                )
            except Exception as e:
                action["result"] = "error"
                action["error"] = str(e)
                print(f"  [ERROR] Failed to schedule {candidate.name}: {e}")

        self._log_action(action)
        return action

    def fill_all_needs(self, dry_run: bool = False) -> list[dict]:
        """Main entry point: scan all needs and schedule candidates."""
        print(f"Scanning for unfilled positions (next {self.advance_days} days)...")
        needs = self.scan_upcoming_needs()

        if not needs:
            print("No unfilled positions found.")
            return []

        print(f"Found {len(needs)} unfilled position(s).\n")
        results = []

        for need in needs:
            print(f"{need.plan_date} — {need.service_type_name} — {need.position_name}:")
            candidates = self.build_eligibility_list(need)

            if not candidates:
                msg = f"  [NO CANDIDATES] No eligible volunteers for {need.position_name}"
                print(msg)
                if not dry_run:
                    self._notify(
                        f"PCO: No eligible volunteers for {need.position_name} "
                        f"on {need.plan_date} ({need.service_type_name}). "
                        f"Manual action needed."
                    )
                results.append({
                    "need": need.__dict__,
                    "result": "no_candidates",
                })
                continue

            if dry_run:
                print(f"  Eligible candidates (ranked):")
                for i, c in enumerate(candidates[:5], 1):
                    print(f"    {i}. {c.name} — last served: {c.last_served} ({c.days_since}d ago)")

            best = candidates[0]
            result = self.schedule_candidate(need, best, dry_run=dry_run)
            results.append(result)

        return results

    def write_status(self):
        """Write status to /tmp/ for Stephen to read."""
        status = {
            "checked": datetime.now(timezone.utc).isoformat(),
            "service_types": self.service_type_ids,
            "upcoming_plans": [],
            "unfilled_count": 0,
            "pending_count": 0,
        }

        for st_id in self.service_type_ids:
            plans = self.client.get_upcoming_plans(st_id, self.advance_days)
            for plan in plans:
                plan_id = plan["id"]
                plan_date = plan["attributes"].get("sort_date", "")[:10]

                needed = self.client.get_needed_positions(st_id, plan_id)
                team_members = self.client.get_plan_team_members(st_id, plan_id)

                pending = [tm for tm in team_members
                           if tm["attributes"].get("status") in ("U", "unconfirmed", "Pending")]
                confirmed = [tm for tm in team_members
                             if tm["attributes"].get("status") in ("C", "confirmed", "Confirmed")]
                declined = [tm for tm in team_members
                            if tm["attributes"].get("status") in ("D", "declined", "Declined")]

                status["upcoming_plans"].append({
                    "plan_id": plan_id,
                    "date": plan_date,
                    "needed": len(needed),
                    "pending": len(pending),
                    "confirmed": len(confirmed),
                    "declined": len(declined),
                })
                status["unfilled_count"] += len(needed)
                status["pending_count"] += len(pending)

        # Atomic write
        tmp = str(STATUS_FILE) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(status, f, indent=2)
        os.rename(tmp, str(STATUS_FILE))

    def _already_scheduled(self, need: SchedulingNeed, candidate: Candidate) -> bool:
        """Check if this person is already on the plan."""
        existing = self.client.get_plan_team_members(need.service_type_id, need.plan_id)
        for tm in existing:
            rels = tm.get("relationships", {})
            person_data = rels.get("person", {}).get("data", {})
            if person_data.get("id") == candidate.person_id:
                return True
        return False

    def _log_action(self, action: dict):
        """Append to schedule log."""
        DATA_DIR.mkdir(exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(action) + "\n")

    def _notify(self, message: str):
        """Send Telegram notification."""
        if not self.notify or not SEND_TELEGRAM.exists():
            return
        try:
            subprocess.run(
                [str(SEND_TELEGRAM), message],
                timeout=10,
                capture_output=True,
            )
        except Exception:
            pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PCO Volunteer Scheduler")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without scheduling")
    parser.add_argument("--status", action="store_true", help="Write status to /tmp/ and print summary")
    parser.add_argument("--plan", help="Only fill needs for a specific plan ID")
    args = parser.parse_args()

    scheduler = VolunteerScheduler()

    if args.status:
        scheduler.write_status()
        with open(STATUS_FILE) as f:
            status = json.load(f)
        print(json.dumps(status, indent=2))
    else:
        results = scheduler.fill_all_needs(dry_run=args.dry_run)
        if not args.dry_run:
            scheduler.write_status()
        print(f"\nDone. {len(results)} action(s) taken.")

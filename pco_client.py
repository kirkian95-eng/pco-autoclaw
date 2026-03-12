#!/usr/bin/env python3
"""PCO Services API client — wraps pypco with scheduling-specific helpers."""

import os
import sys
from datetime import datetime, timedelta, timezone

import pypco
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "config.env"))


class PCOClient:
    def __init__(self, app_id: str = None, secret: str = None):
        self.app_id = app_id or os.environ["PCO_APP_ID"]
        self.secret = secret or os.environ["PCO_SECRET"]
        self.pco = pypco.PCO(self.app_id, self.secret)

    # ── Service Types ──────────────────────────────────────────

    def get_service_types(self) -> list[dict]:
        results = []
        for item in self.pco.iterate("/services/v2/service_types"):
            results.append(item["data"])
        return results

    # ── Plans ──────────────────────────────────────────────────

    def get_upcoming_plans(self, service_type_id: str, days_ahead: int = 21) -> list[dict]:
        cutoff = datetime.now(timezone.utc) + timedelta(days=days_ahead)
        results = []
        for item in self.pco.iterate(
            f"/services/v2/service_types/{service_type_id}/plans",
            filter="future",
        ):
            plan = item["data"]
            sort_date = plan["attributes"].get("sort_date", "")
            if sort_date:
                plan_dt = datetime.fromisoformat(sort_date.replace("Z", "+00:00"))
                if plan_dt <= cutoff:
                    results.append(plan)
        return results

    def get_plan_times(self, service_type_id: str, plan_id: str) -> list[dict]:
        results = []
        for item in self.pco.iterate(
            f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/plan_times"
        ):
            results.append(item["data"])
        return results

    # ── Team Members (scheduled people on a plan) ──────────────

    def get_plan_team_members(self, service_type_id: str, plan_id: str) -> list[dict]:
        results = []
        for item in self.pco.iterate(
            f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/team_members",
            include="person",
        ):
            results.append(item["data"])
        return results

    # ── Needed Positions ───────────────────────────────────────

    def get_needed_positions(self, service_type_id: str, plan_id: str) -> list[dict]:
        results = []
        for item in self.pco.iterate(
            f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/needed_positions"
        ):
            results.append(item["data"])
        return results

    # ── Teams (rosters) ────────────────────────────────────────

    def get_teams(self, service_type_id: str) -> list[dict]:
        results = []
        for item in self.pco.iterate(
            f"/services/v2/service_types/{service_type_id}/teams"
        ):
            results.append(item["data"])
        return results

    def get_team_members(self, service_type_id: str, team_id: str) -> list[dict]:
        results = []
        for item in self.pco.iterate(
            f"/services/v2/service_types/{service_type_id}/teams/{team_id}/team_members",
            include="person",
        ):
            results.append(item["data"])
        return results

    # ── Blockout Dates ─────────────────────────────────────────

    def get_blockout_dates(self, person_id: str) -> list[dict]:
        results = []
        for item in self.pco.iterate(
            f"/services/v2/people/{person_id}/blockout_dates"
        ):
            results.append(item["data"])
        return results

    # ── Schedule History ───────────────────────────────────────

    def get_person_schedules(self, person_id: str, months_back: int = 6) -> list[dict]:
        results = []
        for item in self.pco.iterate(
            f"/services/v2/people/{person_id}/plan_people"
        ):
            results.append(item["data"])
        return results

    # ── Scheduling (write) ─────────────────────────────────────

    def schedule_person(
        self,
        service_type_id: str,
        plan_id: str,
        person_id: str,
        team_id: str,
    ) -> dict:
        payload = {
            "data": {
                "type": "PlanPerson",
                "attributes": {},
                "relationships": {
                    "person": {"data": {"type": "Person", "id": person_id}},
                    "team": {"data": {"type": "Team", "id": team_id}},
                },
            }
        }
        result = self.pco.post(
            f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/team_members",
            payload,
        )
        return result

    # ── People lookup ──────────────────────────────────────────

    def get_person(self, person_id: str) -> dict:
        result = self.pco.get(f"/services/v2/people/{person_id}")
        return result["data"]


# ── Helpers ────────────────────────────────────────────────────

def _get_default_st_id() -> str:
    ids = os.getenv("PCO_SERVICE_TYPE_IDS", "")
    parts = [s.strip() for s in ids.split(",") if s.strip()]
    if not parts:
        print("ERROR: PCO_SERVICE_TYPE_IDS not set in config.env")
        sys.exit(1)
    return parts[0]


def _get_next_plan(client: PCOClient, st_id: str) -> dict | None:
    plans = client.get_upcoming_plans(st_id, 21)
    return plans[0] if plans else None


# ── CLI discovery commands ─────────────────────────────────────

def cmd_list_service_types(client: PCOClient):
    print("Service Types:")
    print("-" * 60)
    for st in client.get_service_types():
        attrs = st["attributes"]
        print(f"  ID: {st['id']}  Name: {attrs.get('name', 'N/A')}")

def cmd_list_teams(client: PCOClient, service_type_id: str):
    print(f"Teams for service type {service_type_id}:")
    print("-" * 60)
    for team in client.get_teams(service_type_id):
        attrs = team["attributes"]
        print(f"  ID: {team['id']}  Name: {attrs.get('name', 'N/A')}")

def cmd_list_plans(client: PCOClient, service_type_id: str, days: int = 21):
    print(f"Upcoming plans (next {days} days) for service type {service_type_id}:")
    print("-" * 60)
    for plan in client.get_upcoming_plans(service_type_id, days):
        attrs = plan["attributes"]
        print(f"  ID: {plan['id']}  Date: {attrs.get('sort_date', 'N/A')}  Title: {attrs.get('title', 'N/A')}")

def cmd_show_plan(client: PCOClient, service_type_id: str, plan_id: str):
    print(f"Plan {plan_id} details:")
    print("-" * 60)

    print("\nTeam Members:")
    for tm in client.get_plan_team_members(service_type_id, plan_id):
        attrs = tm["attributes"]
        print(f"  {attrs.get('name', 'N/A'):30s}  Status: {attrs.get('status', '?'):10s}  Team: {attrs.get('team_position_name', 'N/A')}")

    print("\nNeeded Positions:")
    for np in client.get_needed_positions(service_type_id, plan_id):
        attrs = np["attributes"]
        print(f"  {attrs.get('team_position_name', attrs.get('title', 'N/A')):30s}  Quantity: {attrs.get('quantity', '?')}")


# ── Volunteer lookup commands ──────────────────────────────────

def cmd_who_serving(client: PCOClient, st_id: str = None):
    """Show who's on the next upcoming plan."""
    st_id = st_id or _get_default_st_id()
    plan = _get_next_plan(client, st_id)
    if not plan:
        print("No upcoming plans found.")
        return

    plan_date = plan["attributes"].get("sort_date", "")[:10]
    plan_title = plan["attributes"].get("title", "")
    print(f"Serving {plan_date}" + (f" — {plan_title}" if plan_title else ""))
    print("-" * 50)

    members = client.get_plan_team_members(st_id, plan["id"])
    if not members:
        print("  No one scheduled yet.")
        return

    # Group by status
    confirmed = []
    pending = []
    declined = []
    for tm in members:
        a = tm["attributes"]
        entry = f"  {a.get('name', '?'):25s}  {a.get('team_position_name', '?')}"
        status = a.get("status", "")
        if status in ("C", "confirmed", "Confirmed"):
            confirmed.append(entry)
        elif status in ("D", "declined", "Declined"):
            declined.append(entry)
        else:
            pending.append(entry)

    if confirmed:
        print(f"Confirmed ({len(confirmed)}):")
        print("\n".join(confirmed))
    if pending:
        print(f"Pending ({len(pending)}):")
        print("\n".join(pending))
    if declined:
        print(f"Declined ({len(declined)}):")
        print("\n".join(declined))

    needed = client.get_needed_positions(st_id, plan["id"])
    if needed:
        print(f"\nStill needed ({len(needed)}):")
        for np in needed:
            a = np["attributes"]
            print(f"  {a.get('team_position_name', a.get('title', '?'))}")


def cmd_not_responded(client: PCOClient, st_id: str = None):
    """Show people who haven't accepted/declined yet."""
    st_id = st_id or _get_default_st_id()
    plan = _get_next_plan(client, st_id)
    if not plan:
        print("No upcoming plans found.")
        return

    plan_date = plan["attributes"].get("sort_date", "")[:10]
    members = client.get_plan_team_members(st_id, plan["id"])

    pending = []
    for tm in members:
        a = tm["attributes"]
        status = a.get("status", "")
        if status not in ("C", "confirmed", "Confirmed", "D", "declined", "Declined"):
            pending.append(a)

    if not pending:
        print(f"Everyone has responded for {plan_date}.")
        return

    print(f"Haven't responded for {plan_date} ({len(pending)}):")
    for p in pending:
        print(f"  {p.get('name', '?'):25s}  {p.get('team_position_name', '?')}")


def cmd_who_available(client: PCOClient, team_id: str, st_id: str = None):
    """Show who's eligible for a team and not blocked out for the next plan."""
    st_id = st_id or _get_default_st_id()
    plan = _get_next_plan(client, st_id)
    plan_date = plan["attributes"].get("sort_date", "")[:10] if plan else "unknown"

    roster = client.get_team_members(st_id, team_id)
    if not roster:
        print(f"No members found for team {team_id}.")
        return

    # Get who's already on the plan
    existing_ids = set()
    if plan:
        existing = client.get_plan_team_members(st_id, plan["id"])
        for tm in existing:
            rels = tm.get("relationships", {})
            pid = rels.get("person", {}).get("data", {}).get("id")
            if pid:
                existing_ids.add(pid)

    print(f"Available for {plan_date}:")
    print("-" * 50)
    available = 0
    for member in roster:
        name = member["attributes"].get("name", "?")
        rels = member.get("relationships", {})
        pid = rels.get("person", {}).get("data", {}).get("id")

        status = ""
        if pid and pid in existing_ids:
            status = " (already scheduled)"
        elif pid and plan:
            try:
                blockouts = client.get_blockout_dates(pid)
                for bo in blockouts:
                    ba = bo.get("attributes", {})
                    starts = ba.get("starts_at", "")
                    ends = ba.get("ends_at", "")
                    if starts and ends:
                        from datetime import date as d
                        s = datetime.fromisoformat(starts.replace("Z", "+00:00")).date()
                        e = datetime.fromisoformat(ends.replace("Z", "+00:00")).date()
                        pd = datetime.strptime(plan_date, "%Y-%m-%d").date()
                        if s <= pd <= e:
                            status = " (blocked out)"
                            break
            except Exception:
                pass

        if not status:
            available += 1
        print(f"  {name:25s}{status}")

    print(f"\n{available} available out of {len(roster)} total")


def cmd_last_served(client: PCOClient, name_query: str):
    """Look up when a person last served by name search."""
    # Search across all configured service types for matching team members
    st_ids = [s.strip() for s in os.getenv("PCO_SERVICE_TYPE_IDS", "").split(",") if s.strip()]
    query = name_query.lower()
    seen = {}  # person_id -> name

    for st_id in st_ids:
        teams = client.get_teams(st_id)
        for team in teams:
            members = client.get_team_members(st_id, team["id"])
            for m in members:
                name = m["attributes"].get("name", "")
                rels = m.get("relationships", {})
                pid = rels.get("person", {}).get("data", {}).get("id")
                if pid and query in name.lower() and pid not in seen:
                    seen[pid] = name

    if not seen:
        print(f"No volunteers found matching '{name_query}'.")
        return

    for pid, name in seen.items():
        schedules = client.get_person_schedules(pid)
        if not schedules:
            print(f"{name}: never served (no schedule history)")
            continue

        # Find most recent confirmed
        latest = None
        count = 0
        for s in schedules:
            a = s.get("attributes", {})
            status = a.get("status", "")
            if status in ("C", "confirmed", "Confirmed"):
                count += 1
                sd = a.get("sort_date", a.get("created_at", ""))
                if sd and (latest is None or sd > latest):
                    latest = sd

        if latest:
            days = (datetime.now(timezone.utc) - datetime.fromisoformat(latest.replace("Z", "+00:00"))).days
            print(f"{name}: last served {latest[:10]} ({days} days ago), {count} times in last 6 months")
        else:
            print(f"{name}: no confirmed services found")


def cmd_volunteer_report(client: PCOClient, st_id: str = None):
    """Show service counts per volunteer for fairness checking."""
    st_id = st_id or _get_default_st_id()
    teams = client.get_teams(st_id)
    seen = {}  # pid -> {name, count, last, team}

    for team in teams:
        team_name = team["attributes"].get("name", "?")
        members = client.get_team_members(st_id, team["id"])
        for m in members:
            rels = m.get("relationships", {})
            pid = rels.get("person", {}).get("data", {}).get("id")
            name = m["attributes"].get("name", "?")
            if not pid or pid in seen:
                continue

            schedules = client.get_person_schedules(pid)
            count = 0
            latest = None
            for s in schedules:
                a = s.get("attributes", {})
                if a.get("status") in ("C", "confirmed", "Confirmed"):
                    count += 1
                    sd = a.get("sort_date", a.get("created_at", ""))
                    if sd and (latest is None or sd > latest):
                        latest = sd

            seen[pid] = {
                "name": name,
                "team": team_name,
                "count": count,
                "last": latest[:10] if latest else "never",
            }

    if not seen:
        print("No volunteers found.")
        return

    # Sort by count ascending (least served first)
    entries = sorted(seen.values(), key=lambda x: x["count"])
    print(f"Volunteer Report (last {os.getenv('SCHEDULE_LOOKBACK_MONTHS', '6')} months)")
    print("-" * 60)
    print(f"  {'Name':25s}  {'Team':15s}  {'Times':5s}  Last Served")
    for e in entries:
        print(f"  {e['name']:25s}  {e['team']:15s}  {e['count']:5d}  {e['last']}")
    print(f"\n{len(entries)} volunteers total")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 pco_client.py list-service-types")
        print("  python3 pco_client.py list-teams <service_type_id>")
        print("  python3 pco_client.py list-plans <service_type_id> [days]")
        print("  python3 pco_client.py show-plan <service_type_id> <plan_id>")
        print("  python3 pco_client.py who-serving [service_type_id]")
        print("  python3 pco_client.py not-responded [service_type_id]")
        print("  python3 pco_client.py who-available <team_id> [service_type_id]")
        print("  python3 pco_client.py last-served <name>")
        print("  python3 pco_client.py volunteer-report [service_type_id]")
        sys.exit(1)

    client = PCOClient()
    cmd = sys.argv[1]

    if cmd == "list-service-types":
        cmd_list_service_types(client)
    elif cmd == "list-teams" and len(sys.argv) >= 3:
        cmd_list_teams(client, sys.argv[2])
    elif cmd == "list-plans" and len(sys.argv) >= 3:
        days = int(sys.argv[3]) if len(sys.argv) >= 4 else 21
        cmd_list_plans(client, sys.argv[2], days)
    elif cmd == "show-plan" and len(sys.argv) >= 4:
        cmd_show_plan(client, sys.argv[2], sys.argv[3])
    elif cmd == "who-serving":
        st = sys.argv[2] if len(sys.argv) >= 3 else None
        cmd_who_serving(client, st)
    elif cmd == "not-responded":
        st = sys.argv[2] if len(sys.argv) >= 3 else None
        cmd_not_responded(client, st)
    elif cmd == "who-available" and len(sys.argv) >= 3:
        st = sys.argv[3] if len(sys.argv) >= 4 else None
        cmd_who_available(client, sys.argv[2], st)
    elif cmd == "last-served" and len(sys.argv) >= 3:
        cmd_last_served(client, " ".join(sys.argv[2:]))
    elif cmd == "volunteer-report":
        st = sys.argv[2] if len(sys.argv) >= 3 else None
        cmd_volunteer_report(client, st)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 pco_client.py list-service-types")
        print("  python3 pco_client.py list-teams <service_type_id>")
        print("  python3 pco_client.py list-plans <service_type_id> [days]")
        print("  python3 pco_client.py show-plan <service_type_id> <plan_id>")
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
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

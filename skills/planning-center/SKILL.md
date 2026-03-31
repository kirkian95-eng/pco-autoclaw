---
name: planning-center
description: Planning Center expert for church administration — volunteer scheduling (Services) and people management (People)
user-invocable: true
---

# Planning Center Expert

Helps church staff with Planning Center (PCO) — Services (volunteer scheduling) and People (contacts/membership).

## Tools

### Volunteer Scheduling (Services)

```bash
bash pco.sh <command> [args]
```

Commands:
- `who-serving [service_type_id]` — Who's on the next service
- `who-available <team_id>` — Who's eligible and not blocked out
- `not-responded [service_type_id]` — Pending accept/decline
- `last-served <name>` — When did this person last serve
- `volunteer-report [service_type_id]` — Fairness report
- `service-types` — List all service types
- `teams <service_type_id>` — List teams for a service type
- `plans <service_type_id> [days]` — Upcoming plans
- `show-plan <service_type_id> <plan_id>` — Who's on a specific plan
- `needs` — Dry run: unfilled positions + candidates
- `status` — Scheduler status

### People Lookups

```bash
python3 skills/planning-center/scripts/pco_query.py people <endpoint> [--param key=value] [--limit N]
```

## Safety Rules

- Read-only queries (GET) do not require approval.
- Any action that could notify or affect a real person requires explicit user approval.
- Always disambiguate when multiple people share a name.

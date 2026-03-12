# PCO API Notes

Living reference of Planning Center Services API behavior discovered during development.

**Official docs**: https://developer.planning.center/docs/
**Base URL**: `https://api.planningcenteronline.com/services/v2/`
**Spec**: JSON:API 1.0
**Rate limit**: 100 requests per 20 seconds
**Auth**: HTTP Basic with app_id:secret (Personal Access Token)

## Endpoints Used

### Service Types
- `GET /services/v2/service_types` — list all service types (e.g., "Sunday Morning")

### Plans
- `GET /services/v2/service_types/{st_id}/plans?filter=future` — upcoming plans
- Plans have `sort_date` attribute for ordering

### Team Members (scheduled people)
- `GET /services/v2/service_types/{st_id}/plans/{plan_id}/team_members` — who's on a plan
- Status values: `C` (confirmed), `U` (unconfirmed/pending), `D` (declined)
- Includes `?include=person` to get person details in one call

### Needed Positions
- `GET /services/v2/service_types/{st_id}/plans/{plan_id}/needed_positions` — unfilled slots

### Teams (rosters)
- `GET /services/v2/service_types/{st_id}/teams` — list teams
- `GET /services/v2/service_types/{st_id}/teams/{team_id}/team_members` — eligible people

### Blockout Dates
- `GET /services/v2/people/{person_id}/blockout_dates` — unavailable dates

### Schedule History
- `GET /services/v2/people/{person_id}/plan_people` — past assignments

### Scheduling (write)
- `POST /services/v2/service_types/{st_id}/plans/{plan_id}/team_members` — assign person
- PCO automatically sends the accept/decline notification

## Notes

- pypco `iterate()` handles pagination transparently
- pypco auto-pauses on rate limit (100 req / 20 sec)
- All responses follow JSON:API format: `{"data": {...}, "included": [...], "meta": {...}}`

## TODO — verify during Phase 1
- [ ] Exact status field values for team_members (C/U/D or full words?)
- [ ] Whether POST to team_members sends a "request" (can decline) vs hard "confirm"
- [ ] Blockout date format (date range vs individual dates)
- [ ] Best way to query schedule history with date filtering
- [ ] Relationship between needed_positions and teams

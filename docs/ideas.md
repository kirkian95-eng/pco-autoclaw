# 25 Ways AI Agents Can Work With Planning Center

Text "Stephen" on Telegram in plain English. He reads and writes to Planning Center's API, handles scheduling, and reports back — no app-clicking required.

## Volunteers & Scheduling

1. **Auto-Fill Positions** — Scans upcoming services for unfilled slots and sends scheduling requests to eligible volunteers, prioritizing those who haven't served recently.
2. **Decline Replacement** — Detects declines every 30 min, finds the next best candidate, and texts you the recommendation. Reply "approve" to schedule.
3. **Morning Schedule Summary** — Daily text with who's confirmed, who hasn't responded, and what's still open for Sunday.
4. **"Who's Available?"** — Text "who can run sound Sunday?" and get a ranked list filtered by blockout dates and last-served.
5. **Volunteer Load Report** — Monthly breakdown of how often each person served. Flags overuse and disengagement.
6. **Blockout Date Reminders** — Texts volunteers at the start of each month to update their availability.
7. **New Volunteer Onboarding** — Detects when someone is added to a team and offers to schedule them for a shadow shift.

## Events & Calendar

8. **Weekly Event Digest** — Monday morning summary of all events, room bookings, and resource needs for the week.
9. **Room Conflict Detection** — Checks for double-bookings before an event is submitted.
10. **Event Setup Reminders** — 48 hours before an event, texts the responsible team with what rooms and resources are needed.
11. **Recurring Event Health Check** — Monthly report on which recurring events are active, stale, or poorly attended.

## People & Follow-Up

12. **New Visitor Pipeline** — Notifies the welcome team when a new person is added. Escalates if no follow-up within 3 days.
13. **Birthday & Anniversary Alerts** — Daily text: "3 birthdays this week: John (Tue), Maria (Thu), David (Sat)."
14. **Membership Dashboard** — Text "membership report" for a breakdown of active, inactive, and pending members.
15. **Contact Info Cleanup** — Periodic scan for missing emails, phones, or addresses. Generates a data quality report.
16. **Workflow Step Reminders** — Nudges the responsible person when a workflow card has been stuck for over a week.

## Check-Ins & Attendance

17. **Real-Time Attendance** — Texts check-in counts during services with week-over-week comparison.
18. **Attendance Trends** — Weekly/monthly report with averages by service time, growth rates, and seasonal patterns.
19. **Missing Attendee Alerts** — Flags regulars who've missed 2+ Sundays in a row.
20. **Children's Ministry Ratios** — Alerts if child-to-volunteer ratios in a room exceed your safety threshold.

## Groups

21. **Group Health Dashboard** — Monthly report on every active group: size, meeting frequency, attendance trends.
22. **Group Placement** — Text "find a group for Sarah, North Dallas, young adults" and get matching open groups.
23. **Group Leader Check-In** — Weekly prompt to leaders asking how their group is doing. Flags pastoral needs.

## Giving

24. **Giving Summary** — Weekly/monthly totals by fund with comparison to last year and unique donor count.
25. **First-Time Donor Alert** — Notifies the pastor when someone gives for the first time so they can send a personal thank-you.

---

## Getting Started

1. Get an **admin-level Personal Access Token** from Planning Center (Settings > API)
2. Pick 2-3 ideas to start with
3. Ideas 1-5 are **already built** and ready to test

---

## API Reference

Each idea maps to specific Planning Center API calls. All endpoints follow the pattern `https://api.planningcenteronline.com/{product}/v2/...`

| # | Key Endpoints |
|---|---|
| 1 | `GET .../needed_positions`, `GET .../teams/{id}/team_members`, `POST .../plans/{id}/team_members` |
| 2 | `GET .../team_members` (status=D), `GET .../blockout_dates`, `GET .../plan_people`, `POST .../team_members` |
| 3 | `GET .../plans/{id}/team_members?include=person` |
| 4 | `GET .../teams/{id}/team_members`, `GET .../people/{id}/blockout_dates` |
| 5 | `GET /services/v2/people/{id}/plan_people` (aggregated) |
| 6 | `GET .../teams/{id}/team_members` + external messaging |
| 7 | `GET .../teams/{id}/team_members` (poll for additions), `POST .../team_members` |
| 8 | `GET /calendar/v2/event_instances?filter=future` |
| 9 | `GET /calendar/v2/event_instances`, `GET .../event_resource_requests` |
| 10 | `GET /calendar/v2/event_instances`, `GET .../event_resource_requests` |
| 11 | `GET /calendar/v2/events?filter=future` + Check-Ins cross-ref |
| 12 | `GET /people/v2/people?order=-created_at`, `POST .../workflow_cards` |
| 13 | `GET /people/v2/people` (birthday/anniversary fields) |
| 14 | `GET /people/v2/people?where[membership]=...`, `GET /people/v2/lists` |
| 15 | `GET /people/v2/people?include=emails,phone_numbers,addresses` |
| 16 | `GET /people/v2/workflows/{id}/cards` |
| 17 | `GET /check-ins/v2/events/{id}/event_times/{id}/headcounts` |
| 18 | `GET /check-ins/v2/events/{id}/event_times` (aggregated) |
| 19 | `GET /check-ins/v2/people/{id}/check_ins` |
| 20 | `GET /check-ins/v2/.../check_ins` (by location) + Services volunteer counts |
| 21 | `GET /groups/v2/groups?filter=active`, `.../memberships`, `.../events`, `.../attendance` |
| 22 | `GET /groups/v2/groups?filter=enrollment_open`, `.../memberships` |
| 23 | `GET /groups/v2/groups?filter=active` + external messaging |
| 24 | `GET /giving/v2/donations` (date-filtered), `GET /giving/v2/funds` |
| 25 | Webhook: `profile.first_donated` or `GET /giving/v2/donations?order=-created_at` |

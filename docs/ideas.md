# 25 Ways AI Agents Can Work With Planning Center

A practical guide for church leadership on how AI agents (like our "Stephen" assistant on Telegram) can automate and enhance church operations through the Planning Center API.

> **How it works:** Planning Center has a full REST API that lets software read and write data across all PCO products — Services, Calendar, People, Check-Ins, Groups, and Giving. An AI agent can call this API on your behalf, triggered by text messages, schedules, or events. The agent understands context, so you can interact with it in plain English rather than clicking through menus.

---

## Volunteers & Scheduling (Services API)

### 1. Auto-Fill Volunteer Positions
**What:** When a new service plan is created, the agent scans for unfilled positions and automatically sends scheduling requests to eligible volunteers, prioritizing those who haven't served recently.
**API:** `GET /services/v2/service_types/{id}/plans/{id}/needed_positions` to find gaps, `GET .../teams/{id}/team_members` to find eligible people, `POST .../plans/{id}/team_members` to schedule them. PCO sends the accept/decline notification automatically.
**Value:** Eliminates the weekly grind of manually filling every slot. Fair rotation means no one gets burned out or forgotten.

### 2. Decline Auto-Replacement
**What:** The agent polls for declined scheduling requests every 30 minutes. When someone declines, it finds the next best candidate (factoring in last-served date and blockout dates) and texts you the recommendation. You reply "approve" and the replacement is scheduled.
**API:** `GET .../plans/{id}/team_members` (check for status `D`), `GET /services/v2/people/{id}/blockout_dates`, `GET /services/v2/people/{id}/plan_people` (schedule history), then `POST .../team_members` to assign.
**Value:** No more scrambling on Saturday night when someone backs out. The agent handles the search; you just confirm.

### 3. Morning Schedule Summary
**What:** Every morning (or any time you text "schedule update"), the agent sends a Telegram summary: who's confirmed, who hasn't responded, and what positions are still open for this Sunday.
**API:** `GET .../plans/{id}/team_members?include=person` — status field shows confirmed/unconfirmed/declined for each person.
**Value:** One glance tells you where things stand instead of opening the PCO app and clicking through each team.

### 4. "Who's Available This Sunday?" Query
**What:** Text the agent "who can run sound this Sunday?" and it checks the Sound team roster, cross-references blockout dates, and returns a ranked list of available people.
**API:** `GET .../teams/{id}/team_members`, `GET /services/v2/people/{id}/blockout_dates` for each person.
**Value:** Instant answer when you need to make a phone call. No manual roster-checking.

### 5. Volunteer Load Balancing Report
**What:** The agent generates a monthly report showing how many times each volunteer served, highlighting anyone who's being over-used or hasn't served in months.
**API:** `GET /services/v2/people/{id}/plan_people` for each team member — aggregated by date range.
**Value:** Prevents volunteer burnout and identifies people who may be disengaging. Data-driven pastoral care.

### 6. Blockout Date Reminders
**What:** The agent texts volunteers a reminder to update their blockout dates at the start of each month: "Hey! Planning next month's services — please update your unavailable dates in Planning Center."
**API:** `GET .../teams/{id}/team_members` to get the roster, then send Telegram/SMS reminders with a deep link to PCO.
**Value:** Fewer scheduling conflicts because people actually keep their availability current.

### 7. New Volunteer Onboarding Tracker
**What:** When someone is added to a Services team, the agent notices and starts a follow-up sequence — texts you "Sarah was added to the Greeting team. Want me to schedule her for a shadow shift in the next 2 weeks?"
**API:** `GET .../teams/{id}/team_members` (poll for new additions), `POST .../plans/{id}/team_members` to schedule a shadow/training slot.
**Value:** New volunteers don't fall through the cracks. They get scheduled quickly while motivation is high.

---

## Events & Calendar (Calendar API)

### 8. Weekly Event Digest
**What:** Every Monday morning, the agent sends a summary of all events happening this week — room bookings, event times, and any resource conflicts.
**API:** `GET /calendar/v2/event_instances?filter=future&per_page=50` with date filtering, includes event name, location, start/end times.
**Value:** One message replaces checking the calendar app. Everyone on the leadership team stays informed.

### 9. Room Conflict Detection
**What:** When a new event is being planned, the agent checks for room/resource conflicts before you submit it. "Heads up — the Fellowship Hall is already booked for VBS setup that Saturday."
**API:** `GET /calendar/v2/event_instances` filtered by date range, `GET /calendar/v2/events/{id}/event_resource_requests` to check room assignments.
**Value:** Prevents double-booking embarrassments. Catches conflicts before they become problems.

### 10. Event Setup Checklist Automation
**What:** 48 hours before any event, the agent sends a checklist to the responsible team: "Men's Breakfast Saturday 7AM — tables, coffee setup, projector needed. Is this handled?"
**API:** `GET /calendar/v2/event_instances` (upcoming), `GET /calendar/v2/events/{id}/event_resource_requests` (what resources/rooms are needed).
**Value:** Setup details don't get missed. The responsible person gets a direct reminder with specifics.

### 11. Recurring Event Health Check
**What:** Monthly report on which recurring events are still active, which have low/no attendance, and which might need to be cleaned up.
**API:** `GET /calendar/v2/events?filter=future` — check recurrence patterns and cross-reference with Check-Ins attendance data.
**Value:** Keeps the calendar clean. Surfaces "zombie" events that are on the books but nobody's attending.

---

## People & Follow-Up (People API)

### 12. New Visitor Follow-Up Pipeline
**What:** When a new person is added to PCO (via check-in or manual entry), the agent starts a follow-up workflow — notifies the welcome team leader, tracks whether a follow-up card was sent, and escalates if no contact is made within 3 days.
**API:** `GET /people/v2/people?order=-created_at` (newest people), `GET /people/v2/people/{id}/emails`, `GET /people/v2/people/{id}/workflows` (check workflow status), `POST /people/v2/people/{id}/workflow_cards` (add to a workflow).
**Value:** No visitor falls through the cracks. Systematic follow-up without a spreadsheet.

### 13. Birthday & Anniversary Notifications
**What:** Every morning, the agent checks for upcoming birthdays and anniversaries and texts the pastor: "3 birthdays this week: John (Tue), Maria (Thu), David (Sat)."
**API:** `GET /people/v2/people?per_page=100` — the `birthday` and `anniversary` fields on each person record, filtered by date range.
**Value:** Personal pastoral touch at scale. A quick "happy birthday" text from the pastor means a lot.

### 14. Membership Status Dashboard
**What:** Text "membership report" and get a breakdown: active members, inactive, pending, recently changed status.
**API:** `GET /people/v2/people?where[membership]=Member` (and other status values), or use `GET /people/v2/lists` for pre-built PCO lists.
**Value:** Leadership has real numbers for elder meetings without someone pulling a manual report.

### 15. Contact Info Cleanup Alerts
**What:** The agent periodically scans for people with missing emails, phone numbers, or addresses and generates a "data quality" report.
**API:** `GET /people/v2/people?include=emails,phone_numbers,addresses` — flag records where key fields are empty.
**Value:** Cleaner data means communications actually reach people. Catches issues before they matter.

### 16. Workflow Step Reminders
**What:** If someone has been sitting on a workflow step (e.g., "Schedule meeting with pastor") for more than a week, the agent nudges the responsible person.
**API:** `GET /people/v2/workflows/{id}/cards` — check `updated_at` on each card vs. current date.
**Value:** Workflows actually move forward instead of stalling because someone forgot to check the dashboard.

---

## Check-Ins & Attendance (Check-Ins API)

### 17. Real-Time Attendance Alerts
**What:** During Sunday service, the agent monitors check-in numbers and texts leadership: "9:00 AM service: 145 checked in (up 12% from last week)."
**API:** `GET /check-ins/v2/events/{id}/event_times/{id}/headcounts` or count check-in records for the current event time.
**Value:** Leadership knows attendance trends in real time without waiting for a Monday report.

### 18. Attendance Trend Reports
**What:** Weekly or monthly, the agent generates a trend report: average attendance by service time, growth/decline percentages, seasonal patterns.
**API:** `GET /check-ins/v2/events/{id}/event_times` across multiple weeks, aggregate headcount data.
**Value:** Data-driven decisions about service times, room capacity, and staffing. Spots trends early.

### 19. Missing Regular Attendee Alerts
**What:** If someone who usually checks in every week misses 2+ Sundays in a row, the agent flags them: "Tom hasn't checked in for 3 weeks — might be worth a call."
**API:** `GET /check-ins/v2/people/{id}/check_ins` — compare recent check-in history against their normal pattern.
**Value:** Proactive pastoral care. Reach out before someone quietly drifts away.

### 20. Children's Ministry Ratio Monitoring
**What:** The agent tracks child check-ins vs. scheduled volunteers per room and alerts if ratios exceed your safety threshold: "Toddler room has 14 kids and 2 volunteers — below 1:6 ratio."
**API:** `GET /check-ins/v2/events/{id}/event_times/{id}/check_ins` (filter by location/room), cross-referenced with Services team member counts.
**Value:** Child safety compliance. Catches understaffing in real time while there's still time to pull in help.

---

## Groups (Groups API)

### 21. Group Health Dashboard
**What:** Monthly report on every active group: meeting frequency, member count, attendance trends, and leader engagement.
**API:** `GET /groups/v2/groups?filter=active`, `GET /groups/v2/groups/{id}/memberships`, `GET /groups/v2/groups/{id}/events` (meeting history), `GET /groups/v2/groups/{id}/attendance`.
**Value:** Small group ministry at a glance. Spots struggling groups before they fold.

### 22. Group Placement Assistant
**What:** When someone expresses interest in joining a group (via a form or conversation), text the agent: "Find a group for Sarah, she's in North Dallas and interested in young adults." It searches by location, group type, and openings.
**API:** `GET /groups/v2/groups?filter=enrollment_open` with group type filters, `GET /groups/v2/groups/{id}/memberships` (check capacity).
**Value:** Faster connection. People get plugged in while they're still motivated, not after weeks of back-and-forth.

### 23. Group Leader Check-In
**What:** The agent sends weekly prompts to group leaders: "How was your group this week? Any prayer requests or pastoral needs?" Responses are logged and flagged for follow-up.
**API:** `GET /groups/v2/groups?filter=active` to get leaders, combined with Telegram messaging for the conversational interface.
**Value:** Structured pastoral oversight without micromanaging. Leaders feel supported; issues surface early.

---

## Giving (Giving API)

### 24. Giving Summary for Leadership
**What:** Weekly or monthly, the agent generates a giving summary: total received, fund breakdowns, comparison to budget/last year, and number of unique donors.
**API:** `GET /giving/v2/donations?where[received_at][gte]=2024-01-01` with date ranges, `GET /giving/v2/funds` for fund names, aggregate designation amounts.
**Value:** Financial snapshot without logging into the giving dashboard. Elders and finance team stay informed.

### 25. First-Time Donor Thank You
**What:** When someone gives for the first time, the agent detects it and notifies the pastor: "New first-time donor: Rachel — $50 to General Fund." Pastor can send a personal thank-you.
**API:** Giving webhooks: `profile.first_donated` event fires when a person makes their first donation. Or poll `GET /giving/v2/donations?order=-created_at` and cross-reference donor history.
**Value:** First-time donors who get a personal thank-you within 48 hours are significantly more likely to give again. This makes it effortless.

---

## How It All Connects

All 25 of these ideas use the same architecture:

```
Planning Center API  <-->  Python scripts  <-->  AI Agent (Stephen)  <-->  Telegram
```

- **Scheduled tasks** (systemd timers) handle recurring jobs: polling for declines, morning summaries, attendance reports
- **On-demand queries** happen when you text Stephen: "who's available Sunday?", "membership report", "giving this month"
- **Approval workflows** keep humans in the loop: the agent recommends, you confirm

The API covers **read and write** across all products. The agent doesn't just report — it can take action (schedule volunteers, add people to workflows, etc.) with your approval.

### What's Needed to Get Started
1. **Admin-level Personal Access Token** from Planning Center (Settings > API)
2. Pick 2-3 ideas from this list to start with
3. We build and test incrementally — volunteer scheduling (ideas 1-3) is already built and ready to go

### Already Built (pco-autoclaw)
- Idea 1: Auto-fill volunteer positions
- Idea 2: Decline auto-replacement (notify-first)
- Idea 3: Morning schedule summary
- Idea 4: "Who's available?" queries
- Idea 5: Volunteer load balancing report

The rest can be added as modules — same agent, same Telegram interface, expanding capabilities over time.

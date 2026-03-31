# Sunday Booklet Engine

## Recommendation

Build the Sunday booklet workflow as a headless Python pipeline inside `pco-autoclaw`, not as a separate service.

The preferred architecture is:

1. Resolve the service date into a liturgical context using the ACNA 2019 Sunday lectionary.
2. Fetch the scripture text from the official Crossway ESV API at generation time.
3. Fetch songs and assigned participants from Planning Center Services.
4. Copy a pristine Google Docs template for the right template family.
5. Fill placeholders and machine-managed sections.
6. Persist document state in SQLite so a background sync job can update only safe sections later.

This keeps the system simple:

- one repo
- one CLI entrypoint
- one SQLite manifest
- one Google service account
- one `systemd --user` timer for sync

## Source Of Truth

### Lectionary

Use the ACNA 2019 Sunday, Holy Day, and Commemoration Lectionary as the source of truth for readings and observance naming.

- Official PDF: `https://bcp2019.anglicanchurch.net/wp-content/uploads/2022/03/tle328sundaylectionary.pdf`
- Official BCP site: `https://bcp2019.anglicanchurch.net/`

The PDF explicitly states that this lectionary provides a three-year cycle and that the ESV is the normative text for Scripture readings.

### Scripture Text

Do not use an unofficial or open-source ESV mirror as the authoritative source.

Use Crossway's official API:

- `https://api.esv.org/`
- `https://api.esv.org/docs/`

Design implication:

- fetch passages on demand
- cache minimally for performance if needed
- do not attempt to build or store a full local ESV corpus without confirming license terms

### Helper Resource

`Word to Worship` is useful as a helper for observance discovery and song ideation, but it should not be the canonical source of readings or booklet content.

- `https://wordtoworship.com/lectionary/acna`

## First Slice

Ship the narrowest useful slice first:

- weekly Sunday worship only
- template family: ordinary time after Pentecost
- generate one Google Doc from a pristine template
- fill readings, songs, and first-name participant slots
- support background sync for songs and participant names

Defer Advent, Lent, Palm Sunday, Easter, Pentecost, and special feast layouts until the data model is stable.

## Google Auth Model

Use a Google service account, not user OAuth, unless Drive sharing rules make that impossible.

Required GCP setup:

1. Enable Google Docs API
2. Enable Google Drive API
3. Create a service account
4. Download a JSON key
5. Share:
   - the yearly output folder
   - the template folder
   - each pristine template doc
   with the service account as `Editor`

This is the cleanest headless VM-compatible setup.

## Data Flow

### Generate

1. Hildy or a human runs:
   `python3 booklet_cli.py plan --date 2026-06-14 --template-family ordinary_after_pentecost`
2. CLI resolves config and initializes the manifest.
3. Lectionary adapter returns:
   - liturgical season
   - observance label
   - reading references
4. ESV adapter fetches passage text.
5. PCO adapter fetches:
   - plan ID
   - song titles
   - scheduled participants
6. Docs adapter copies the pristine template into the year folder.
7. Docs adapter fills placeholders and machine-managed sections.
8. Manifest records:
   - service date
   - plan ID
   - doc ID
   - section hashes
   - source hashes

### Sync

1. `systemd --user` timer runs `sync-upcoming`
2. Sync refetches PCO data for future services
3. Sync compares current source hash to last known source hash
4. If unchanged, do nothing
5. If changed:
   - fetch the current document section content
   - if the current section still matches the last machine-rendered hash, update it
   - if it differs, treat the human edit as authoritative and mark a conflict
6. Optionally send Hildy a concise Telegram update when a change was applied or skipped due to conflict

## Human-Authoritative Rule

Human edits must win.

That means we should never blindly overwrite a section in Google Docs once a person has changed it.

Recommended mechanism:

- store a per-section `rendered_hash` in SQLite
- on sync, read the current text of each managed section
- if `current_doc_hash != rendered_hash`, the section was edited by a human
- mark the section as `conflict` and skip any overwrite

This is more reliable than trying to infer authorship from Drive revision metadata.

## Template Strategy

Preferred mode: hybrid.

- Copy a pristine family template doc
- Replace simple placeholders like:
  - `[[SERVICE_TITLE]]`
  - `[[SERVICE_DATE]]`
  - `[[SONG_1]]`
  - `[[PREACHER_FIRST_NAME]]`
- Replace machine-managed blocks delimited by sentinel paragraphs:
  - `[[AUTO:READINGS:BEGIN]]`
  - `[[AUTO:READINGS:END]]`
  - `[[AUTO:SONGS:BEGIN]]`
  - `[[AUTO:SONGS:END]]`
  - `[[AUTO:ROLES:BEGIN]]`
  - `[[AUTO:ROLES:END]]`

Why hybrid:

- easier to preserve polished formatting
- easier for humans to maintain pristine templates in Docs
- easier to sync just the sections that change

## Ownership Boundaries

### `booklet/planner.py`

Owns orchestration and turns a date + template family into a persisted plan.

### `booklet/manifest.py`

Owns SQLite schema and conflict-tracking state.

### `booklet/sources/lectionary.py`

Owns liturgical metadata and reading references.

### `booklet/sources/esv.py`

Owns scripture text retrieval from the official ESV API.

### `booklet/sources/pco_services.py`

Owns PCO reads for songs, plan IDs, and assigned participants.

### `booklet/sources/google_docs.py`

Owns template copy and section updates through Drive + Docs APIs.

## Planned CLI

### `booklet_cli.py init-manifest`

Create the SQLite manifest schema.

### `booklet_cli.py plan --date YYYY-MM-DD --template-family FAMILY`

Persist a planned document record for a service date.

### `booklet_cli.py generate --date YYYY-MM-DD`

Future command:

- resolve data
- create the Google Doc
- write managed sections

### `booklet_cli.py sync-upcoming --days 14`

Future command:

- recheck PCO
- update safe sections only

## Failure Modes

### Lectionary mismatch

If the date-to-observance mapping is wrong, the whole booklet is wrong.

Mitigation:

- keep the lectionary resolver isolated
- test a fixture set of known Sundays across seasons

### ESV API unavailable

Mitigation:

- fail generation cleanly
- never substitute guessed text
- optionally allow a cached retry for the exact same passage

### Google Docs shape drift

Humans may alter a pristine template in ways that break placeholder replacement.

Mitigation:

- validate that required placeholders exist before generation
- fail with a specific missing-placeholder report

### PCO data ambiguity

Songs may still be placeholder labels like `Song 2`; participant slot names may drift.

Mitigation:

- separate "slot label" from "resolved assigned title"
- keep role mapping configurable rather than hard-coded

### Human edits during sync

Mitigation:

- section hash conflict detection
- never overwrite a diverged section

## Test Matrix

### Lectionary

- ordinary time after Pentecost
- Advent
- Lent
- Palm Sunday
- Easter Day
- Pentecost

### Docs

- placeholder replacement in a pristine template
- section replacement inside auto-managed sentinels
- conflict detection when a managed section is edited manually

### PCO

- plan found for date
- plan missing for date
- songs still unresolved (`Song 1`, `Song 2`)
- participant names present

### Sync

- no source changes
- song changes only
- participant changes only
- source changed but doc section manually edited

## Open Questions

- Which exact Google Docs represent the pristine ordinary-time-after-Pentecost template family?
- Which PCO item type and field should be considered the canonical song title?
- Which role slots must always appear in the booklet, and which are optional?
- How should Psalm formatting work when the liturgical template expects responsive reading or a refrain?

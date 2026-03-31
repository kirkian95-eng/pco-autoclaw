# pco-autoclaw

Church operations automation for [Planning Center](https://www.planningcenter.com/) — volunteer scheduling, Sunday liturgy booklets, and event graphics.

Built for [St. Luke's Anglican](https://stlukemd.org/) and designed to be reusable by any ACNA church plant.

## What It Does

### Volunteer Scheduling (Services)
Scans upcoming services for unfilled positions, ranks eligible volunteers by fairness (longest since last served), sends scheduling requests via the PCO API, detects declines, and recommends replacements.

### Sunday Liturgy Booklets
Generates weekly worship booklets as Google Docs by combining:
- ACNA 2019 lectionary (observance, readings, collect, proper preface)
- ESV scripture text from [Crossway's API](https://api.esv.org/)
- Songs and participant names from a planning workbook and Planning Center
- A pristine Google Docs template (copy-and-fill, not freehand generation)

Exports as PDF and attaches to the matching Planning Center service plan. Tracks generated docs in SQLite with per-section conflict detection so human edits are never overwritten.

### Event Graphics
Generates 1080×1080 announcement images using Pillow — Playfair Display + Outfit fonts, liturgical color palette, optional stock photo backgrounds via Pexels.

### OpenClaw Integration
All three capabilities are registered as [OpenClaw](https://github.com/openclaw) skills, making them available through a Telegram bot interface.

## Prerequisites

- Python 3.10+
- A Planning Center account with admin-level Personal Access Token
- Google Cloud project with Docs + Drive APIs enabled (for booklets)
- [ESV API key](https://api.esv.org/) (for scripture text)
- [Pexels API key](https://www.pexels.com/api/) (for event graphic backgrounds)

## Setup

1. **Clone and install**

   ```bash
   git clone https://github.com/kirkian95-eng/pco-autoclaw.git
   cd pco-autoclaw
   pip install -r requirements.txt
   cp config.env.example config.env
   ```

2. **Configure credentials** — edit `config.env` with your API keys and file paths. See `config.env.example` for documentation on each variable.

3. **Google auth for booklets** — set up a service account or OAuth client, share your template and output folders with it. See `docs/booklet-engine.md` for the full auth model.

4. **Discover your PCO service types**

   ```bash
   python3 pco_client.py list-service-types
   python3 pco_client.py list-teams <service_type_id>
   ```

## Usage

### Volunteer Scheduling

All scheduling commands go through `pco.sh`:

```bash
./pco.sh who-serving              # Who's on the next service
./pco.sh not-responded            # Who hasn't accepted/declined
./pco.sh last-served "John"       # When did John last serve
./pco.sh volunteer-report         # Fairness report (sorted by least served)
./pco.sh needs                    # Dry run — show unfilled positions + candidates
./pco.sh schedule                 # Live schedule (fills unfilled positions)
./pco.sh poll                     # Check for declines, recommend replacements
./pco.sh plans <st_id> [days]     # List upcoming plans
./pco.sh help                     # Full command list
```

### Sunday Booklets

All booklet commands go through `booklet.sh`:

```bash
./booklet.sh preview 2026-06-07              # Preview assembled service data
./booklet.sh preview-no-pco 2026-06-07       # Preview without Planning Center
./booklet.sh make-reply 2026-06-07 ordinary_time  # Generate doc + attach PDF to PCO
./booklet.sh update-reply 2026-06-07 ordinary_time # Update existing doc in place
./booklet.sh link-reply 2026-06-07           # Get existing doc URL
./booklet.sh route-reply "make a booklet for Trinity Sunday"  # Natural language
```

### Event Graphics

```bash
python3 generate_event_graphic.py \
    --name "Men's Coffee" \
    --date "Friday, March 27" \
    --time "7:30 AM" \
    --location "Westside Coffee" \
    --output /tmp/event.png
```

Optional: `--bg-search "coffee latte cup"` for stock backgrounds, `--bg-image photo.jpg` for a custom background, `--color "#3d6b4f"` for a specific color.

## Project Structure

```
pco-autoclaw/
├── pco.sh                  # Volunteer scheduling CLI
├── pco_client.py           # Planning Center API wrapper
├── scheduler.py            # Auto-scheduling logic
├── poller.py               # Decline detection + replacements
├── booklet.sh              # Booklet generation CLI
├── booklet_cli.py          # Booklet CLI entrypoint
├── booklet/                # Booklet pipeline package
│   ├── assembler.py        # Combines all data sources
│   ├── config.py           # Config loader
│   ├── manifest.py         # SQLite doc tracking
│   ├── models.py           # Data models
│   ├── document_renderer.py # Google Docs fill logic
│   ├── pco_pdf_publish.py  # PDF export + PCO attachment
│   ├── reference_resolver.py # Natural language date resolution
│   ├── request_router.py   # Route requests to actions
│   ├── response_formatter.py # Human-readable output
│   └── sources/            # External data adapters
│       ├── esv.py          # ESV API
│       ├── google_docs.py  # Google Docs/Drive API
│       ├── pco_services.py # Planning Center data
│       └── planning_worksheet.py # Planning spreadsheet
├── generate_event_graphic.py # Event graphic generator
├── reference_resolver.py   # Top-level reference resolver
├── request_router.py       # Top-level request router
├── response_formatter.py   # Top-level response formatter
├── tests/                  # Test suite
├── docs/                   # Architecture docs
├── config.env.example      # Config template
└── requirements.txt        # Python dependencies
```

## Configuration

See `config.env.example` for all options. Key variables:

| Variable | Description |
|---|---|
| `PCO_APP_ID` / `PCO_SECRET` | Planning Center Personal Access Token |
| `ESV_API_TOKEN` | Crossway ESV API key |
| `PEXELS_API_KEY` | Pexels stock photo API key |
| `BOOKLET_SERVICE_TYPE_ID` | Default PCO service type for booklets |
| `BOOKLET_ORDINARY_TEMPLATE_DOC_ID` | Google Docs template for ordinary time |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Path to Google service account JSON |

## Dependencies

All dependencies are permissively licensed (MIT, Apache 2.0, BSD-3):

- [pypco](https://github.com/billdeitrick/pypco) — Planning Center API client (MIT)
- [google-api-python-client](https://github.com/googleapis/google-api-python-client) — Google APIs (Apache 2.0)
- [Pillow](https://python-pillow.org/) — Image generation (HPND)
- [httpx](https://www.python-httpx.org/) — HTTP client (BSD-3)
- [openpyxl](https://openpyxl.readthedocs.io/) — Excel file reading (MIT)
- [python-dotenv](https://github.com/theskumar/python-dotenv) — Env file loading (BSD-3)

## License

MIT

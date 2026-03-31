# pco-autoclaw

Open-source church operations toolkit — volunteer scheduling, liturgy booklets, event graphics, and sermon transcription. Built for ACNA churches using Planning Center, designed to work standalone or as an AI assistant via [OpenClaw](https://github.com/openclaw).

## What It Does

| Capability | Description |
|-----------|-------------|
| **Volunteer Scheduling** | Scans upcoming services for unfilled positions, ranks candidates by fairness (longest since last served), sends scheduling requests, detects declines, recommends replacements |
| **Sunday Booklets** | Generates weekly liturgy booklets as Google Docs from ACNA lectionary + ESV scripture + Planning Center data + a Google Docs template. Exports PDF and attaches to PCO plans |
| **Event Graphics** | Generates 1080x1080 announcement images with your church name/logo, liturgical color palette, and optional stock photo backgrounds |
| **Sermon Transcription** | Batch-transcribes sermons from Subsplash using OpenAI Whisper. Produces .txt, .json, .srt, .vtt, .tsv per sermon |

Each capability works as a standalone CLI tool. For AI-assisted usage, OpenClaw skill definitions are included in `skills/`.

## Quick Start

```bash
git clone https://github.com/kirkian95-eng/pco-autoclaw.git
cd pco-autoclaw
pip3 install -r requirements.txt
bash setup.sh
```

The interactive `setup.sh` walks you through configuration and creates `config.env`. You can also copy `config.env.example` and fill it in manually.

### Replace the Logo

Replace `logo_white.png` with your church's logo (white on transparent PNG, any size — it gets resized to 70x70).

### Install Fonts (for event graphics)

Download [Playfair Display](https://fonts.google.com/specimen/Playfair+Display) and [Outfit](https://fonts.google.com/specimen/Outfit) from Google Fonts, place the variable `.ttf` files in `~/.local/share/fonts/`.

## Usage

### Volunteer Scheduling

```bash
./pco.sh who-serving              # Who's on the next service
./pco.sh not-responded            # Pending accept/decline
./pco.sh last-served "John"       # When did John last serve
./pco.sh volunteer-report         # Fairness report
./pco.sh needs                    # Unfilled positions + candidates
./pco.sh schedule                 # Fill positions (sends PCO notifications)
./pco.sh plans <st_id> [days]     # Upcoming plans
./pco.sh help                     # Full command list
```

### Sunday Booklets

```bash
./booklet.sh preview 2026-06-07                        # Preview assembled data
./booklet.sh make-reply 2026-06-07 ordinary_time       # Generate doc + PDF
./booklet.sh update-reply 2026-06-07 ordinary_time     # Update existing doc
./booklet.sh link-reply 2026-06-07                     # Get doc URL
./booklet.sh route-reply "make a booklet for Trinity Sunday"  # Natural language
```

### Event Graphics

```bash
python3 generate_event_graphic.py \
    --name "Men's Coffee" \
    --date "Friday, March 27" \
    --time "7:30 AM" \
    --location "Fellowship Hall" \
    --output /tmp/event.png \
    --bg-search "coffee latte cup"
```

### Sermon Transcription

```bash
# One-time manifest build (requires Playwright + Node.js)
SUBSPLASH_APP_KEY=YOUR_KEY node transcribe/fetch_manifest.js
SUBSPLASH_APP_KEY=YOUR_KEY bash transcribe/enrich_manifest.sh

# Transcribe all sermons (idempotent, safe to re-run)
bash transcribe/transcribe_all.sh
```

## Configuration

All configuration lives in `config.env`. Run `setup.sh` to generate it interactively, or see `config.env.example` for documentation.

| Variable | Description |
|---|---|
| `CHURCH_NAME` | Your church name (displayed on graphics) |
| `CHURCH_LOGO_PATH` | Path to your logo file |
| `PCO_APP_ID` / `PCO_SECRET` | Planning Center Personal Access Token |
| `BOOKLET_SERVICE_TYPE_ID` | PCO service type for weekly worship |
| `ESV_API_TOKEN` | Crossway ESV API key |
| `PEXELS_API_KEY` | Pexels stock photo API key |
| `NAME_ALIASES` | Map worksheet initials to names (e.g. `JAM:James,KT:Kim`) |
| `SUBSPLASH_APP_KEY` | Your Subsplash app key (for transcription) |

See `config.env.example` for the full list with documentation.

## Project Structure

```
pco-autoclaw/
├── setup.sh                     # Interactive onboarding
├── config.env.example           # Config template
├── church.yaml.example          # Church-specific config template
├── logo_white.png               # Replace with your logo
├── pco.sh / pco_client.py       # Volunteer scheduling
├── scheduler.py / poller.py     # Auto-scheduling + decline detection
├── booklet.sh / booklet_cli.py  # Booklet generation CLI
├── booklet/                     # Booklet pipeline package
│   ├── assembler.py             # Combines data sources
│   ├── config.py                # Config loader
│   ├── manifest.py              # SQLite doc tracking
│   ├── document_renderer.py     # Google Docs fill logic
│   ├── pco_pdf_publish.py       # PDF export + PCO attachment
│   ├── reference_resolver.py    # Natural language date resolution
│   ├── request_router.py        # Route requests to actions
│   └── sources/                 # External data adapters
│       ├── esv.py               # ESV API
│       ├── google_docs.py       # Google Docs/Drive
│       ├── pco_services.py      # Planning Center
│       └── planning_worksheet.py
├── generate_event_graphic.py    # Event graphic generator
├── transcribe/                  # Sermon transcription pipeline
│   ├── transcribe_all.sh        # Main pipeline script
│   ├── fetch_manifest.js        # Build Subsplash manifest
│   └── enrich_manifest.sh       # Add CDN URLs to manifest
├── skills/                      # OpenClaw skill definitions
│   ├── planning-center/
│   ├── event-graphic/
│   ├── sunday-booklet/
│   └── sermon-transcription/
├── tests/
├── docs/                        # Architecture documentation
└── requirements.txt
```

## Prerequisites

- Python 3.10+
- For booklets: Google Cloud project with Docs + Drive APIs, ESV API key
- For graphics: Pillow, Playfair Display + Outfit fonts, Pexels API key
- For transcription: [OpenAI Whisper](https://github.com/openai/whisper), ffmpeg, Node.js + Playwright
- For AI assistant: [OpenClaw](https://github.com/openclaw) (optional)

## Dependencies

All permissively licensed (MIT/Apache 2.0/BSD-3/HPND):

| Package | License | Used for |
|---------|---------|----------|
| pypco | MIT | Planning Center API |
| google-api-python-client | Apache 2.0 | Google Docs/Drive |
| Pillow | HPND | Event graphics |
| httpx | BSD-3 | HTTP client |
| openpyxl | MIT | Planning workbook |
| python-dotenv | BSD-3 | Config loading |
| openai-whisper | MIT | Sermon transcription |

## OpenClaw Integration

To use with OpenClaw as a Telegram bot:

1. Copy `skills/` to your OpenClaw workspace
2. Symlink this repo into your workspace: `ln -s /path/to/pco-autoclaw ~/.openclaw/workspace/pco-autoclaw`
3. Configure your OpenClaw agent with the skill definitions

See `skills/*/SKILL.md` for each skill's capabilities and safety rules.

## License

MIT

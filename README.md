# pco-autoclaw

Automated volunteer scheduling for [Planning Center Services](https://www.planningcenter.com/services).

Scans upcoming services for unfilled positions, ranks eligible volunteers by fairness (longest since last served), sends scheduling requests, detects declines, and recommends replacements — all via the PCO API.

## Features

- **Smart rotation**: Ranks candidates by last-served date so everyone gets a fair turn
- **Decline handling**: Polls for declines and finds the best replacement
- **Blockout awareness**: Respects volunteer blockout dates
- **Telegram notifications**: Sends scheduling updates and morning summaries
- **OpenClaw integration**: Works as a skill for the [OpenClaw](https://github.com/openclaw) AI agent
- **Zero-token automation**: Systemd timers handle polling — no AI tokens burned for routine checks

## Prerequisites

- Python 3.10+
- A Planning Center account with **admin access** (or a Personal Access Token from your admin)
- [pypco](https://github.com/billdeitrick/pypco) (installed via requirements.txt)

## Setup

1. **Get PCO API credentials**

   Go to [api.planningcenteronline.com/oauth/applications](https://api.planningcenteronline.com/oauth/applications) and create a Personal Access Token.

2. **Clone and install**

   ```bash
   git clone https://github.com/kirkian95-eng/pco-autoclaw.git
   cd pco-autoclaw
   pip install -r requirements.txt
   cp config.env.example config.env
   # Edit config.env with your PCO credentials
   ```

3. **Discover your service types**

   ```bash
   python3 pco_client.py list-service-types
   python3 pco_client.py list-teams <service_type_id>
   ```

   Add the service type IDs to `config.env`.

## Usage

### Scan for unfilled positions (dry run)
```bash
python3 scheduler.py --dry-run
```

### Schedule volunteers
```bash
python3 scheduler.py
```

### Poll for declines
```bash
python3 poller.py
```

### Morning summary
```bash
python3 poller.py --summary
```

## Configuration

See `config.env.example` for all options:

| Variable | Default | Description |
|---|---|---|
| `PCO_APP_ID` | — | PCO Personal Access Token app ID |
| `PCO_SECRET` | — | PCO Personal Access Token secret |
| `PCO_SERVICE_TYPE_IDS` | — | Comma-separated service type IDs to manage |
| `SCHEDULE_ADVANCE_DAYS` | 21 | How far ahead to look for unfilled plans |
| `SCHEDULE_MIN_DAYS_BETWEEN` | 14 | Minimum days between serving for same person |
| `SCHEDULE_LOOKBACK_MONTHS` | 6 | How far back to check service history |
| `TELEGRAM_NOTIFY` | 1 | Send Telegram notifications (requires send-telegram.sh) |

## Systemd Timers (optional)

For automated polling, create systemd user timers. See `docs/` for example unit files.

## How It Works

1. **Scan**: Queries upcoming plans for `needed_positions`
2. **Rank**: For each unfilled slot, gets the team roster, filters by blockouts/recent service, sorts by longest wait
3. **Schedule**: Assigns the top candidate via the PCO API (PCO sends the accept/decline notification)
4. **Poll**: Every 30 minutes, checks for declines and recommends replacements
5. **Notify**: Sends Telegram messages for all scheduling actions

## License

MIT

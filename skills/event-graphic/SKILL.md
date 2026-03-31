---
name: event-graphic
description: Generate 1080x1080 event/announcement graphics. Use when someone asks to make, create, or generate a graphic, flyer, image, or announcement.
user-invocable: true
---

# Event & Announcement Graphic Generator

## Required Info

| Flag | What it renders | Required |
|------|----------------|----------|
| `--name` | Big headline (center) | Yes |
| `--date` | First info line (bottom) | Yes |
| `--time` | Second info line (bottom) | No |
| `--location` | Third info line (bottom) | Yes |
| `--address` | Fourth info line (bottom) | No |
| `--subtitle` | Italic text under headline | No |
| `--color` | Background color hex | No |

## Usage

```bash
python3 generate_event_graphic.py \
    --name "Event Name" \
    --date "Saturday, April 5" \
    --time "9:00 AM" \
    --location "Fellowship Hall" \
    --output /tmp/event.png
```

Optional backgrounds:
- `--bg-search "coffee latte cup"` for Pexels stock photos
- `--bg-image photo.jpg` for a custom image
- `--color "#3d6b4f"` for a specific background color

## Configuration

Set in `config.env`:
- `CHURCH_NAME` — displayed at top of graphic
- `CHURCH_LOGO_PATH` — path to your logo (white on transparent PNG works best)
- `PEXELS_API_KEY` — for stock photo backgrounds

## Colors

| Mood | Hex | Use for |
|------|-----|---------|
| Solemn | `#6b6b6b` | Ash Wednesday, Good Friday |
| Green | `#3d6b4f` | General events |
| Coral | `#c75050` | Women's events |
| Gold | `#d4a030` | Easter, celebration |
| Blue | `#5b8fad` | Informational |
| Brown | `#8b6b4a` | Fellowship, coffee |

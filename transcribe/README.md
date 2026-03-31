# Sermon Transcription Pipeline

Batch-transcribe sermons from Subsplash using OpenAI Whisper. Downloads audio from CDN, converts to optimal format, transcribes, and produces multiple output formats (.txt, .json, .srt, .vtt, .tsv).

## Prerequisites

- Python 3.10+
- [OpenAI Whisper](https://github.com/openai/whisper): `pip install openai-whisper`
- ffmpeg: `sudo apt install ffmpeg`
- Node.js 18+ and Playwright (for manifest fetching only): `npx playwright install chromium`

## Setup

1. Find your Subsplash app key — it's in any embed URL: `subsplash.com/u/-APPKEY/...`

2. Build the manifest:
   ```bash
   SUBSPLASH_APP_KEY=YOUR_KEY node fetch_manifest.js
   SUBSPLASH_APP_KEY=YOUR_KEY bash enrich_manifest.sh
   ```

3. Run the transcription pipeline:
   ```bash
   bash transcribe_all.sh
   ```

## Manifest Format

`manifest.json` is an array of objects. Each entry needs at minimum:

```json
{
  "title": "Sermon Title",
  "date": "2026-03-22",
  "speaker": "Pastor Name",
  "slug": "sermon-slug",
  "cdn_mp3_url": "https://cdn.subsplash.com/audios/..."
}
```

If your sermons aren't on Subsplash, you can create `manifest.json` manually with direct MP3 URLs from any source.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `base` | Whisper model size (tiny, base, small, medium, large) |
| `SUBSPLASH_APP_KEY` | — | Your Subsplash app key |

## Output

Each sermon produces 5 files in `transcripts/`:
- `.txt` — Plain text with metadata header
- `.json` — Timestamped segments
- `.srt` — SubRip subtitles
- `.vtt` — WebVTT subtitles
- `.tsv` — Tab-separated timestamps

The pipeline is idempotent — safe to re-run, skips already-transcribed sermons.

---
name: sermon-transcription
description: Transcribe sermons from Subsplash using OpenAI Whisper. Use when someone asks to transcribe, get transcripts, or process sermon audio.
user-invocable: true
---

# Sermon Transcription

Batch-transcribe sermons from Subsplash CDN using OpenAI Whisper.

## Commands

```bash
# Build the manifest (one-time)
SUBSPLASH_APP_KEY=YOUR_KEY node transcribe/fetch_manifest.js
SUBSPLASH_APP_KEY=YOUR_KEY bash transcribe/enrich_manifest.sh

# Run transcription
bash transcribe/transcribe_all.sh
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `base` | Whisper model (tiny/base/small/medium/large) |
| `SUBSPLASH_APP_KEY` | — | Your church's Subsplash app key |

## Output

Each sermon produces 5 files: `.txt`, `.json`, `.srt`, `.vtt`, `.tsv`

The pipeline is idempotent — safe to re-run.

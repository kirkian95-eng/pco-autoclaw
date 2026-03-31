#!/usr/bin/env bash
set -euo pipefail

# Sermon Transcription Pipeline
# Downloads audio from a manifest of sermon URLs, converts to 16kHz mono WAV
# (optimal for Whisper), transcribes, and cleans up audio.
# Safe to re-run — skips already-transcribed sermons.
# Designed to run unattended in tmux.
#
# Prerequisites: whisper (pip install openai-whisper), ffmpeg, python3, curl

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
AUDIO_DIR="$BASE_DIR/audio"
TRANSCRIPT_DIR="$BASE_DIR/transcripts"
MANIFEST="$BASE_DIR/manifest.json"
LOG="$BASE_DIR/transcribe.log"
MODEL="${WHISPER_MODEL:-base}"

mkdir -p "$AUDIO_DIR" "$TRANSCRIPT_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

# ── Pre-flight ───────────────────────────────────────────────────────
if [[ ! -f "$MANIFEST" ]]; then
  log "ERROR: No manifest.json found. Create one first (see README)."
  log "  manifest.json should be an array of objects with: title, date, speaker, slug, cdn_mp3_url"
  exit 1
fi

TOTAL=$(python3 -c "import json; print(len([i for i in json.load(open('$MANIFEST')) if i.get('cdn_mp3_url')]))")
log "Starting transcription pipeline: $TOTAL sermons, model=$MODEL"
log "Transcript dir: $TRANSCRIPT_DIR"
echo ""

# ── Process each sermon ──────────────────────────────────────────────
COUNT=0
DONE=0
SKIPPED=0
FAILED=0

python3 -c "
import json
items = json.load(open('$MANIFEST'))
for i in items:
    url = i.get('cdn_mp3_url', '')
    if url:
        print(f\"{url}\t{i['date']}\t{i['slug']}\t{i['title']}\t{i.get('speaker','')}\")
" | while IFS=$'\t' read -r CDN_URL DATE SLUG TITLE SPEAKER; do
  COUNT=$((COUNT + 1))
  SAFE_NAME="${DATE}_${SLUG}"
  MP3_FILE="$AUDIO_DIR/${SAFE_NAME}.mp3"
  WAV_FILE="$AUDIO_DIR/${SAFE_NAME}.wav"
  TRANSCRIPT_FILE="$TRANSCRIPT_DIR/${SAFE_NAME}.txt"

  # Skip if already transcribed
  if [[ -f "$TRANSCRIPT_FILE" ]]; then
    SKIPPED=$((SKIPPED + 1))
    log "[$COUNT/$TOTAL] SKIP: $TITLE"
    continue
  fi

  log "[$COUNT/$TOTAL] $TITLE ($DATE, $SPEAKER)"

  # Download MP3 from CDN
  if [[ ! -f "$WAV_FILE" ]]; then
    log "  Downloading MP3..."
    HTTP_CODE=$(curl -sL -o "$MP3_FILE" -w "%{http_code}" "$CDN_URL")

    if [[ "$HTTP_CODE" != "200" ]] || [[ ! -s "$MP3_FILE" ]]; then
      log "  ERROR: Download failed (HTTP $HTTP_CODE)"
      rm -f "$MP3_FILE"
      FAILED=$((FAILED + 1))
      continue
    fi
    log "  Downloaded: $(du -h "$MP3_FILE" | cut -f1)"

    # Convert to 16kHz mono WAV (Whisper's native format)
    log "  Converting to 16kHz mono WAV..."
    if ffmpeg -y -i "$MP3_FILE" -ar 16000 -ac 1 -c:a pcm_s16le "$WAV_FILE" </dev/null 2>/dev/null; then
      rm -f "$MP3_FILE"
      log "  Converted: $(du -h "$WAV_FILE" | cut -f1)"
    else
      log "  WARNING: ffmpeg failed, using MP3 directly"
      mv "$MP3_FILE" "$WAV_FILE"
    fi
  fi

  # Transcribe
  log "  Transcribing..."
  if whisper "$WAV_FILE" \
      --model "$MODEL" \
      --language en \
      --output_format all \
      --output_dir "$TRANSCRIPT_DIR" \
      2>&1 | tail -1 | tee -a "$LOG"; then
    # Prepend metadata header to .txt
    if [[ -f "$TRANSCRIPT_FILE" ]]; then
      HEADER="Title: ${TITLE}\nDate: ${DATE}\nSpeaker: ${SPEAKER}\n---\n\n"
      printf "%b" "$HEADER" | cat - "$TRANSCRIPT_FILE" > "$TRANSCRIPT_FILE.tmp"
      mv "$TRANSCRIPT_FILE.tmp" "$TRANSCRIPT_FILE"
    fi
    DONE=$((DONE + 1))
    log "  Done [$DONE completed]"
  else
    log "  ERROR: Transcription failed"
    FAILED=$((FAILED + 1))
  fi

  # Clean up audio
  rm -f "$WAV_FILE" "$MP3_FILE"
  echo ""
done

log "========================================"
log "Pipeline complete!"
log "  Total: $TOTAL, Done: $DONE, Skipped: $SKIPPED, Failed: $FAILED"
log "========================================"

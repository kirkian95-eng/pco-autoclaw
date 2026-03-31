#!/usr/bin/env bash
set -euo pipefail

# Enriches manifest.json with direct CDN MP3 URLs by scraping each sermon's
# Subsplash embed page. No auth required for CDN downloads.
#
# Usage:
#   SUBSPLASH_APP_KEY=YOUR_KEY bash enrich_manifest.sh
#   # or edit APP_KEY below

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
MANIFEST="$BASE_DIR/manifest.json"
APP_KEY="${SUBSPLASH_APP_KEY:-CHANGE_ME}"

if [[ "$APP_KEY" == "CHANGE_ME" ]]; then
  echo "Set SUBSPLASH_APP_KEY env var or edit APP_KEY in this script."
  exit 1
fi

if [[ ! -f "$MANIFEST" ]]; then
  echo "No manifest.json found. Run fetch_manifest.js first."
  exit 1
fi

TOTAL=$(python3 -c "import json; print(len(json.load(open('$MANIFEST'))))")
echo "Enriching $TOTAL items with CDN MP3 URLs..."

python3 << PYEOF
import json, subprocess, re, sys, time, os

manifest_path = "$MANIFEST"
with open(manifest_path) as f:
    manifest = json.load(f)

app_key = "$APP_KEY"
updated = 0
failed = 0

for i, item in enumerate(manifest):
    if item.get("cdn_mp3_url"):
        continue  # already enriched

    short_code = item["short_code"]
    url = f"https://subsplash.com/u/-{app_key}/media/embed/d/{short_code}?&info=0"

    try:
        result = subprocess.run(
            ["curl", "-sL", url],
            capture_output=True, text=True, timeout=15
        )
        html = result.stdout

        # Find CDN MP3 URL pattern
        match = re.search(
            r'cdn\.subsplash\.com/audios/' + app_key + r'/([0-9a-f-]+)/audio\.mp3',
            html
        )
        if match:
            cdn_url = f"https://{match.group(0)}"
            item["cdn_mp3_url"] = cdn_url
            item["audio_output_id"] = match.group(1)
            updated += 1
        else:
            # Try the source URL as fallback
            match_src = re.search(
                r'cdn\.subsplash\.com/audios/' + app_key + r'/_source/([0-9a-f-]+)/audio',
                html
            )
            if match_src:
                item["cdn_source_url"] = f"https://{match_src.group(0)}"
                updated += 1
            else:
                print(f"  WARN: No audio URL for [{i+1}] {item['title']}", file=sys.stderr)
                failed += 1

    except Exception as e:
        print(f"  ERROR: [{i+1}] {item['title']}: {e}", file=sys.stderr)
        failed += 1

    if (i + 1) % 25 == 0:
        print(f"  {i+1}/{len(manifest)} done")
        # Save progress
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

    # Small delay to be nice
    time.sleep(0.2)

# Final save
with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2)

print(f"\nDone. Updated: {updated}, Failed: {failed}")
mp3_count = sum(1 for m in manifest if m.get("cdn_mp3_url"))
src_count = sum(1 for m in manifest if m.get("cdn_source_url") and not m.get("cdn_mp3_url"))
print(f"  CDN MP3: {mp3_count}, Source only: {src_count}, No audio: {failed}")
PYEOF

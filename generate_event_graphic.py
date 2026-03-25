#!/usr/bin/env python3
"""Generate event announcement graphics for St. Luke Anglican Church.

Usage:
    python3 generate_event_graphic.py \
        --name "Men's Coffee" \
        --date "Friday, March 27" \
        --time "7:30 AM" \
        --location "Westside Coffee" \
        --address "4711 Westside Drive, Dallas, TX 75209" \
        --output /tmp/event.png
"""

import argparse
import random
import os
import tempfile
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# --- Constants ---

PALETTE = [
    "#6b6b6b",  # warm gray
    "#3d6b4f",  # forest green
    "#c75050",  # coral
    "#d4a030",  # marigold
    "#5b8fad",  # steel blue
    "#8b6b4a",  # warm brown
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.expanduser("~/.local/share/fonts")
FONT_SERIF = os.path.join(FONT_DIR, "PlayfairDisplay.ttf")
FONT_SERIF_ITALIC = os.path.join(FONT_DIR, "PlayfairDisplay-Italic.ttf")
FONT_SANS = os.path.join(FONT_DIR, "Outfit.ttf")
LOGO_PATH = os.path.join(SCRIPT_DIR, "logo_white.png")

PEXELS_API_KEY = "94TlRoIxPVYrRnwGqv7EJTANCRTwd5dKblQE6ZGYEV5QWmxfz5rmo2YX"

WIDTH = 1080
HEIGHT = 1080
PADDING = 90  # horizontal padding on each side
MAX_TEXT_W = WIDTH - (PADDING * 2)  # 900px
WHITE = "#FFFFFF"


def fetch_pexels_images(query, count=2):
    """Search Pexels for photos, return list of PIL Images (up to count).
    Automatically excludes photos with people."""
    import requests
    safe_query = f"{query} no people no person no portrait"
    try:
        resp = requests.get("https://api.pexels.com/v1/search", params={
            "query": safe_query,
            "per_page": min(count * 3, 15),  # fetch extra for variety
            "orientation": "square",
        }, headers={"Authorization": PEXELS_API_KEY}, timeout=10)
        data = resp.json()
        if not data.get("photos"):
            return []
        # Shuffle and take up to count
        photos = data["photos"]
        random.shuffle(photos)
        results = []
        for photo in photos[:count]:
            try:
                img_url = photo["src"]["large2x"]
                img_resp = requests.get(img_url, timeout=15)
                img_resp.raise_for_status()
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                    f.write(img_resp.content)
                    tmp = f.name
                img = Image.open(tmp).convert("RGB")
                os.unlink(tmp)
                results.append(img)
            except Exception:
                continue
        return results
    except Exception as e:
        print(f"Pexels fetch failed: {e}")
        return []


def prepare_bg_image(photo, bg_color_hex, opacity=0.35):
    """Crop photo to square, overlay with color tint. Returns 1080x1080 RGB image."""
    w, h = photo.size
    # Center-crop to square
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    photo = photo.crop((left, top, left + side, top + side))
    photo = photo.resize((WIDTH, HEIGHT), Image.LANCZOS)

    # Darken the photo slightly
    photo = ImageEnhance.Brightness(photo).enhance(0.6)

    # Create color overlay
    color = Image.new("RGB", (WIDTH, HEIGHT), bg_color_hex)

    # Blend: photo * opacity + color * (1 - opacity)
    blended = Image.blend(color, photo, opacity)
    return blended


def font(path, size, weight=None):
    """Load a font at given size. For variable fonts, set weight axis."""
    f = ImageFont.truetype(path, size)
    if weight is not None:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass  # not a variable font or no weight axis
    return f


def measure(draw, text, f):
    """Return (width, height) of rendered text."""
    bbox = draw.textbbox((0, 0), text, font=f)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_centered(draw, y, text, f, fill=WHITE):
    """Draw text centered horizontally at y."""
    w, _ = measure(draw, text, f)
    draw.text(((WIDTH - w) // 2, y), text, fill=fill, font=f)


def wrap_words_pixel(draw, words, f, max_w):
    """Wrap a list of words into lines, splitting only at word boundaries,
    using actual pixel measurements. Returns list of line strings."""
    lines = []
    current = words[0]
    for word in words[1:]:
        test = current + " " + word
        if measure(draw, test, f)[0] <= max_w:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def wrap_text_pixel(draw, text, f, max_w):
    """Wrap text to fit within max_w pixels. Returns list of lines."""
    words = text.split()
    if not words:
        return [""]
    return wrap_words_pixel(draw, words, f, max_w)


def fit_title(draw, name, max_lines=3):
    """Auto-size the event name. Returns (lines, font, line_height, block_height).

    Preserves original casing — does NOT force uppercase.
    Uses pixel-based word wrapping (never breaks mid-word).
    Starts large and shrinks until text fits within MAX_TEXT_W in <= max_lines.
    Prefers 1-2 lines at large size over 3-4 lines at huge size.
    """
    for size in range(130, 35, -2):
        f = font(FONT_SERIF, size, weight=700)
        line_h = measure(draw, "Ag", f)[1]

        # Try single line
        if measure(draw, name, f)[0] <= MAX_TEXT_W:
            return [name], f, line_h, line_h

        # Try word-wrapping
        words = name.split()
        if len(words) < 2:
            continue

        lines = wrap_words_pixel(draw, words, f, MAX_TEXT_W)
        if len(lines) <= max_lines:
            spacing = int(line_h * 0.15)
            block_h = line_h * len(lines) + spacing * (len(lines) - 1)
            return lines, f, line_h, block_h

    # Fallback: smallest size
    f = font(FONT_SERIF, 36)
    line_h = measure(draw, "Ag", f)[1]
    lines = wrap_words_pixel(draw, name.split(), f, MAX_TEXT_W)
    spacing = int(line_h * 0.15)
    block_h = line_h * len(lines) + spacing * (len(lines) - 1)
    return lines, f, line_h, block_h


def generate(args):
    bg = args.color or random.choice(PALETTE)

    # Build list of background images to render
    # Each entry: (label, PIL Image or None)
    bg_variants = []

    if args.bg_image:
        # User-provided image + solid color backup
        try:
            user_photo = Image.open(args.bg_image).convert("RGB")
            bg_variants.append(("photo", prepare_bg_image(user_photo, bg, opacity=0.35)))
        except Exception as e:
            print(f"Could not load bg image: {e}")
        bg_variants.append(("plain", None))
    elif args.bg_search:
        # Two stock photos + solid color
        photos = fetch_pexels_images(args.bg_search, count=2)
        for i, photo in enumerate(photos):
            bg_variants.append((f"stock{i+1}", prepare_bg_image(photo, bg, opacity=0.35)))
        bg_variants.append(("plain", None))
    else:
        # Just solid color
        bg_variants.append(("plain", None))

    # Generate one image per variant
    base, ext = os.path.splitext(args.output)
    output_paths = []

    for label, bg_img in bg_variants:
        if bg_img:
            img = bg_img.copy()
        else:
            img = Image.new("RGB", (WIDTH, HEIGHT), bg)

        draw = ImageDraw.Draw(img)
        _render_content(draw, img, args, bg)

        if len(bg_variants) == 1:
            path = args.output
        else:
            path = f"{base}_{label}{ext}"

        img.save(path, "PNG")
        output_paths.append(path)
        print(f"Saved {path} ({WIDTH}x{HEIGHT})")

    return output_paths


def _render_content(draw, img, args, bg):
    """Render all text and logo onto the image."""
    # --- Fonts ---
    church_f = font(FONT_SANS, 42, weight=600)
    date_f = font(FONT_SANS, 48, weight=500)
    time_f = font(FONT_SANS, 48, weight=500)
    loc_f = font(FONT_SANS, 46, weight=600)
    addr_f = font(FONT_SANS, 36, weight=400)
    subtitle_f = font(FONT_SERIF_ITALIC, 38, weight=400) if args.subtitle else None

    # --- Measure ---
    church_text = "St. Luke Anglican Church"
    church_h = measure(draw, church_text, church_f)[1]

    title_lines, title_f, title_line_h, title_block_h = fit_title(draw, args.name)
    title_spacing = int(title_line_h * 0.15)

    subtitle_lines = []
    subtitle_line_h = 0
    subtitle_block_h = 0
    if args.subtitle:
        subtitle_lines = wrap_text_pixel(draw, args.subtitle, subtitle_f, MAX_TEXT_W)
        subtitle_line_h = measure(draw, "Ag", subtitle_f)[1]
        sub_sp = int(subtitle_line_h * 0.15)
        subtitle_block_h = subtitle_line_h * len(subtitle_lines) + sub_sp * (len(subtitle_lines) - 1)

    date_h = measure(draw, args.date, date_f)[1]
    time_h = measure(draw, args.time, time_f)[1] if args.time else 0
    loc_h = measure(draw, args.location, loc_f)[1]
    addr_h = measure(draw, args.address, addr_f)[1] if args.address else 0

    # --- Layout ---
    margin = 80
    church_y = margin + 55

    dt_line_gap = 8
    when_where_gap = 40
    loc_line_gap = 12

    dt_block_h = date_h + (dt_line_gap + time_h if args.time else 0)
    loc_block_h = loc_h + (loc_line_gap + addr_h if args.address else 0)
    info_block_h = dt_block_h + when_where_gap + loc_block_h

    info_top = HEIGHT - margin - info_block_h
    date_y = info_top
    loc_y = date_y + dt_block_h + when_where_gap

    center_top = church_y + church_h
    center_bottom = info_top

    subtitle_total = 0
    if args.subtitle:
        subtitle_total = 30 + subtitle_block_h

    title_total_h = title_block_h + subtitle_total
    title_y = center_top + (center_bottom - center_top - title_total_h) // 2
    title_y = max(center_top + 20, title_y)

    # --- Draw ---

    # Logo
    logo_size = 70
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        logo_x = (WIDTH - logo_size) // 2
        logo_y = church_y - logo_size - 12
        if logo_y >= 20:
            img.paste(logo, (logo_x, logo_y), logo)
    except FileNotFoundError:
        pass

    # Church name
    draw_centered(draw, church_y, church_text, church_f)

    # Event name
    y = title_y
    for line in title_lines:
        draw_centered(draw, y, line, title_f)
        y += title_line_h + title_spacing

    # Subtitle
    if args.subtitle and subtitle_f and subtitle_lines:
        sy = title_y + title_block_h + 35
        sub_sp = int(subtitle_line_h * 0.15)
        for sline in subtitle_lines:
            draw_centered(draw, sy, sline, subtitle_f)
            sy += subtitle_line_h + sub_sp

    # Date + time
    draw_centered(draw, date_y, args.date, date_f)
    if args.time:
        draw_centered(draw, date_y + date_h + dt_line_gap, args.time, time_f)

    # Location + address
    draw_centered(draw, loc_y, args.location, loc_f)
    if args.address:
        draw_centered(draw, loc_y + loc_h + loc_line_gap, args.address, addr_f)


def main():
    p = argparse.ArgumentParser(description="Generate St. Luke event graphic")
    p.add_argument("--name", required=True, help="Headline text (event name or announcement title)")
    p.add_argument("--date", required=True, help="First info line, e.g. 'Friday, March 27' or 'Order by March 30'")
    p.add_argument("--time", default="", help="Second info line, e.g. '7:30 AM' or 'Email kim@stlukemd.org' (optional)")
    p.add_argument("--location", required=True, help="Third info line, e.g. venue name or 'St. Luke Anglican Church'")
    p.add_argument("--address", help="Street address (optional)")
    p.add_argument("--subtitle", help="Subtitle below event name (optional)")
    p.add_argument("--color", help="Background hex color override, e.g. '#3d6b4f'")
    p.add_argument("--bg-image", help="Path to a background photo (will be tinted)")
    p.add_argument("--bg-search", help="Pexels search query for background photo, e.g. 'coffee shop'")
    p.add_argument("--output", required=True, help="Output PNG file path")
    args = p.parse_args()
    generate(args)


if __name__ == "__main__":
    main()

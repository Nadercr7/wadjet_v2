"""Generate OG default image for social sharing (1200x630)."""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1200, 630
bg = "#0A0A0A"
gold = "#D4AF37"
ivory = "#F5F0E8"
sand = "#C4A265"

img = Image.new("RGB", (W, H), bg)
draw = ImageDraw.Draw(img)

# Gold border
for i in range(3):
    draw.rectangle([i, i, W - 1 - i, H - 1 - i], outline=gold)

# Subtle inner border
draw.rectangle([20, 20, W - 21, H - 21], outline="#2A2A2A")

# Eye of Horus (Gardiner D10 = U+13080)
hiero_font = ImageFont.truetype(
    "app/static/fonts/NotoSansEgyptianHieroglyphs-Regular.ttf", 120
)
eye = "\U00013080"
bbox = draw.textbbox((0, 0), eye, font=hiero_font)
ew = bbox[2] - bbox[0]
draw.text(((W - ew) // 2, 100), eye, fill=gold, font=hiero_font)

# Fonts
try:
    title_font = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 72)
    sub_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 28)
    small_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
except Exception:
    title_font = ImageFont.load_default()
    sub_font = ImageFont.load_default()
    small_font = ImageFont.load_default()

# Title
title = "Wadjet"
bbox = draw.textbbox((0, 0), title, font=title_font)
tw = bbox[2] - bbox[0]
draw.text(((W - tw) // 2, 280), title, fill=gold, font=title_font)

# Subtitle
subtitle = "Decode Ancient Egypt with AI"
bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
sw = bbox[2] - bbox[0]
draw.text(((W - sw) // 2, 380), subtitle, fill=ivory, font=sub_font)

# Tagline
tagline = "Scan hieroglyphs \u2022 Explore landmarks \u2022 Learn from Thoth"
bbox = draw.textbbox((0, 0), tagline, font=small_font)
tagw = bbox[2] - bbox[0]
draw.text(((W - tagw) // 2, 440), tagline, fill=sand, font=small_font)

# Gold accent line
line_w = 200
draw.line([(W // 2 - line_w // 2, 500), (W // 2 + line_w // 2, 500)], fill=gold, width=2)

# Footer URL
footer = "wadjet.onrender.com"
bbox = draw.textbbox((0, 0), footer, font=small_font)
fw = bbox[2] - bbox[0]
draw.text(((W - fw) // 2, 540), footer, fill=sand, font=small_font)

out = "app/static/images/og-default.png"
os.makedirs(os.path.dirname(out), exist_ok=True)
img.save(out, "PNG", optimize=True)
size = os.path.getsize(out)
print(f"Created {out} ({size:,} bytes)")

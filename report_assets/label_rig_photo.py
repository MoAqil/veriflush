"""Label the as-built rig photo for report Figure 2.

python report_assets/label_rig_photo.py <photo.jpeg> <out.png>
"""
import sys

from PIL import Image, ImageDraw, ImageFont

src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
dr = ImageDraw.Draw(im)
font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 30)
NAVY = (31, 58, 95)

# (text, point on the component, top-left of the label)
tags = [("TK-101 feed tank + P-101 pump", (200, 470), (15, 600)),
        ("TT-100 feed probe", (285, 400), (15, 180)),
        ("Y splitter", (520, 468), (430, 655)),
        ("Manual valves", (565, 345), (300, 250)),
        ("FT-101 YF-S401", (760, 470), (700, 385)),
        ("Diversion", (800, 560), (790, 655)),
        ("Reference", (950, 330), (870, 240)),
        ("Monitored coil", (1090, 480), (1000, 560)),
        ("TT-101 probe", (1225, 330), (1250, 245)),
        ("Outlet valve", (1390, 560), (1180, 655)),
        ("Arduino Uno R3", (640, 190), (720, 110))]
for text, target, (x, y) in tags:
    w, h = dr.textbbox((0, 0), text, font=font)[2:]
    box = (x - 8, y - 5, x + w + 8, y + h + 9)
    cx = min(max(target[0], box[0]), box[2])
    cy = box[1] if target[1] < box[1] else box[3]
    dr.line([target, (cx, cy)], fill=NAVY, width=4)
    dr.ellipse([target[0] - 6, target[1] - 6, target[0] + 6, target[1] + 6], fill=NAVY)
    dr.rectangle(box, fill=(255, 255, 255), outline=NAVY, width=3)
    dr.text((x, y), text, fill=NAVY, font=font)
im.save(dst)
print("saved", dst)

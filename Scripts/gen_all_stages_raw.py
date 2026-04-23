# gen_all_stages_raw.py
from PIL import Image, ImageDraw
import numpy as np
import os

W, H = 64, 64

def save_raw(img, path):
    rgba = img.convert("RGBA")
    with open(path, "wb") as f:
        f.write(rgba.tobytes())

# Stage 1: Two objects moving apart
N1 = 10
os.makedirs("raw_stage1", exist_ok=True)
for i in range(N1):
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    x1, x2 = 10 + i * 2, 40 - i * 2
    draw.rectangle((x1, 20, x1+8, 28), fill="black")
    draw.rectangle((x2, 20, x2+8, 28), fill="black")
    save_raw(img, f"raw_stage1/frame_{i:02d}.raw")

# Stage 2: Rotating L-shape
N2 = 12
os.makedirs("raw_stage2", exist_ok=True)
for i in range(N2):
    base = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(base)
    d.rectangle((20, 20, 28, 44), fill=0)
    d.rectangle((20, 44, 44, 52), fill=0)
    rot = base.rotate(i * 15, resample=Image.NEAREST, fillcolor=255)
    save_raw(rot, f"raw_stage2/frame_{i:02d}.raw")

# Stage 3: Moving Cross
N3 = 10
os.makedirs("raw_stage3", exist_ok=True)
for i in range(N3):
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    cx = 32 + (i - N3//2) * 2
    cy = 32
    draw.rectangle((cx-2, cy-10, cx+2, cy+10), fill="black")
    draw.rectangle((cx-10, cy-2, cx+10, cy+2), fill="black")
    save_raw(img, f"raw_stage3/frame_{i:02d}.raw")

# Stage 4: Shaded Sphere
N4 = 12
os.makedirs("raw_stage4", exist_ok=True)
for i in range(N4):
    img = Image.new("L", (W, H), 255)
    cx, cy, r = 32, 32, 20
    light_angle = np.deg2rad(i * 30)
    lx, ly = np.cos(light_angle), np.sin(light_angle)
    for y in range(H):
        for x in range(W):
            dx, dy = x - cx, y - cy
            dist = np.sqrt(dx*dx + dy*dy)
            if dist <= r:
                nx, ny = dx / (dist + 1e-6), dy / (dist + 1e-6)
                shade = (nx*lx + ny*ly + 1) * 0.5
                val = int(255 * (1 - shade))
                img.putpixel((x,y), val)
    save_raw(img, f"raw_stage4/frame_{i:02d}.raw")

print("Generated all stages in raw format.")

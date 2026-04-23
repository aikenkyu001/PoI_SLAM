# gen_test_frames.py
from PIL import Image, ImageDraw
import os

W, H = 64, 64
N = 10

os.makedirs("frames", exist_ok=True)

for i in range(N):
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    # 左から右へ動く黒い矩形
    x0 = 5 + i * 3
    y0 = 20
    x1 = x0 + 10
    y1 = y0 + 10

    draw.rectangle((x0, y0, x1, y1), fill="black")
    img.save(f"frames/frame_{i:02d}.png")

print("generated", N, "frames in ./frames")

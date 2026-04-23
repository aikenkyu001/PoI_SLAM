# gen_raw_frames.py
from PIL import Image, ImageDraw
import os

W, H = 64, 64
N = 10

os.makedirs("raw_frames", exist_ok=True)

for i in range(N):
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    # 左から右へ動く黒い矩形
    x0 = 5 + i * 3
    y0 = 20
    x1 = x0 + 10
    y1 = y0 + 10

    draw.rectangle((x0, y0, x1, y1), fill="black")
    
    # RGBA に変換して保存 (A=255)
    rgba = img.convert("RGBA")
    with open(f"raw_frames/frame_{i:02d}.raw", "wb") as f:
        f.write(rgba.tobytes())

print("generated", N, "raw frames in ./raw_frames")

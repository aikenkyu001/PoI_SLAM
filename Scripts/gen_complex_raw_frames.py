# gen_complex_raw_frames.py
from PIL import Image, ImageDraw
import os

W, H = 64, 64
N = 10

os.makedirs("raw_frames_complex", exist_ok=True)

for i in range(N):
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    # 固定された矩形1
    draw.rectangle((10, 10, 15, 15), fill="black")

    # 右へ動く矩形2（矩形1から離れていく）
    x0 = 25 + i * 3
    y0 = 30
    x1 = x0 + 5
    y1 = y0 + 5

    draw.rectangle((x0, y0, x1, y1), fill="black")
    
    rgba = img.convert("RGBA")
    with open(f"raw_frames_complex/frame_{i:02d}.raw", "wb") as f:
        f.write(rgba.tobytes())

print("generated", N, "complex raw frames in ./raw_frames_complex")

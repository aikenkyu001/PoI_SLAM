### テスト方針のざっくり像

- **目的:**  
  ブラウザ抜きで、PoI-SLAM のパイプライン  
  （画像 → PoI-OCR → Graph → A/K/Ω → PKGF）  
  が安定して動くことを確認する。

- **構成:**  
  1. Python で「動く単純図形」の PNG を 10 枚生成  
  2. Node.js でそれらを順番に WASM に流し込み、  
     各フレームの `dim`, `n_nodes`, `K[0]` などをログ出力  
  3. 連続フレームで値がちゃんと変化しているかを見る

- **フレーム数:**  
  **10 枚で十分**。  
  「動きに対して PoI がちゃんと反応するか」を見るだけなら、  
  5〜10 フレームあれば挙動は掴める。

---

### 1. 画像生成 Python コード（10 枚の動く矩形）

```python
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
```

実行:

```bash
python gen_test_frames.py
```

---

### 2. Node.js 側の機能テスト（WASM 叩き）

```js
// test_wasm_sequence.js
const fs = require("fs");
const { createCanvas, loadImage } = require("canvas");
const Module = require("./poi.js"); // emcc で生成したもの

Module.onRuntimeInitialized = async () => {
  console.log("WASM ready");

  for (let i = 0; i < 10; i++) {
    const fname = `frames/frame_${i.toString().padStart(2, "0")}.png`;
    const img = await loadImage(fname);

    const canvas = createCanvas(img.width, img.height);
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0);

    const frame = ctx.getImageData(0, 0, img.width, img.height);

    const ptr = Module._malloc(frame.data.length);
    Module.HEAPU8.set(frame.data, ptr);

    const t0 = Date.now();
    Module._process_frame(ptr, img.width, img.height);
    const t1 = Date.now();

    const dim = Module._poi_get_dim();
    const nNodes = Module._poi_get_n_nodes();

    let K0 = NaN;
    if (dim > 0) {
      const ptrK = Module._poi_get_K();
      const K = new Float32Array(Module.HEAPF32.buffer, ptrK, dim * dim);
      K0 = K[0];
    }

    console.log(
      `frame ${i}: time=${t1 - t0}ms dim=${dim} nodes=${nNodes} K[0]=${K0}`
    );

    Module._free(ptr);
  }

  console.log("sequence test finished");
};
```

実行:

```bash
npm install canvas
node test_wasm_sequence.js
```

---

### 3. これで何がわかるか

- 各フレームで `dim` / `n_nodes` が 0 にならず安定しているか  
- `K[0]` がフレームごとに変化しているか（動きへの感度）  
- OOM やクラッシュが一切出ないか  
- ブラウザ抜きで PoI-SLAM の「場の更新」が追えるか

---

# ✦ PoI-SLAM 機能テスト計画（第二段階）

## 目的
PoI の場（A/K/Ω）が  
**複数ノードの相対距離変化に対して正しく反応するか**  
を検証する。

## テストで確認したいこと
- ノード数が 2〜4 に増える  
- dim が 2〜4 に増える  
- K-field がフレームごとに変化する  
- PoI が「動き」を場の変化として捉える  
- OOM やクラッシュが起きない  

---

# ✦ テストシナリオ（3段階）

## **シナリオ A：2つの物体が離れていく（最小の SLAM 条件）**
- 2 ノード  
- 距離が増える  
- K[0,1] が減少するはず  
- PoI の最小構造変化テスト

## **シナリオ B：L字型が回転する（回転に対する感度）**
- 3 ノード  
- 形状が変化  
- K-field の固有構造が変わる  
- PoI の回転不変性の検証

## **シナリオ C：十字型（+）が移動する（多点構造の安定性）**
- 4 ノード  
- 移動による距離変化  
- PKGF の安定性を確認

---

# ✦ まずはシナリオ A（2物体が離れる）から始めるのが最適

PoI の場の変化が最も分かりやすく現れる。

以下に **Python 画像生成コード**を示す。

---

# ✦ Python 画像生成コード（シナリオ A：2物体が離れる）

```python
# gen_frames_two_objects.py
from PIL import Image, ImageDraw
import os

W, H = 64, 64
N = 10

os.makedirs("frames_two", exist_ok=True)

for i in range(N):
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    # 物体1（左→右）
    x1 = 10 + i * 2
    draw.rectangle((x1, 20, x1 + 8, 28), fill="black")

    # 物体2（右→左）
    x2 = 40 - i * 2
    draw.rectangle((x2, 20, x2 + 8, 28), fill="black")

    img.save(f"frames_two/frame_{i:02d}.png")

print("generated", N, "frames in ./frames_two")
```

---

# ✦ Node.js 側のテストコード（PoI-WASM に流し込む）

```js
// test_two_objects.js
const fs = require("fs");
const { createCanvas, loadImage } = require("canvas");
const Module = require("./poi.js");

Module.onRuntimeInitialized = async () => {
  console.log("WASM ready");

  for (let i = 0; i < 10; i++) {
    const fname = `frames_two/frame_${i.toString().padStart(2, "0")}.png`;
    const img = await loadImage(fname);

    const canvas = createCanvas(img.width, img.height);
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0);

    const frame = ctx.getImageData(0, 0, img.width, img.height);

    const ptr = Module._malloc(frame.data.length);
    Module.HEAPU8.set(frame.data, ptr);

    Module._process_frame(ptr, img.width, img.height);

    const dim = Module._poi_get_dim();
    const nNodes = Module._poi_get_n_nodes();

    let K01 = NaN;
    if (dim >= 2) {
      const ptrK = Module._poi_get_K();
      const K = new Float32Array(Module.HEAPF32.buffer, ptrK, dim * dim);
      K01 = K[1];  // off-diagonal
    }

    console.log(`frame ${i}: dim=${dim} nodes=${nNodes} K[0,1]=${K01}`);

    Module._free(ptr);
  }

  console.log("two-object test finished");
};
```

---

# ✦ このテストで期待される結果

- ノード数：2  
- dim：2  
- K-field：2×2 行列  
- フレームが進むにつれて  
  **K[0,1]（距離に対応する項）が単調に減少**  
- PoI が「物体が離れていく」という構造変化を正しく捉える

これは PoI-SLAM の最小構造テストとして理想的。

---

# ✦ PoI-SLAM 全ステップ機能テスト計画

PoI-SLAM の構造的挙動をすべて検証するために、  
以下の 4 ステージを順番に実行する。

---

# ◆ **Stage 1：最小構造テスト（2物体が離れる）**  
目的：  
- augment_with_cluster_centroid_distances が正しく動くか  
- K-field が距離変化に反応するか  
- PKGF → pose 更新が動くか  

### Python 画像生成（2物体が離れる）

```python
# stage1_two_objects.py
from PIL import Image, ImageDraw
import os

W, H = 64, 64
N = 10
os.makedirs("stage1", exist_ok=True)

for i in range(N):
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    x1 = 10 + i * 2
    x2 = 40 - i * 2

    draw.rectangle((x1, 20, x1+8, 28), fill="black")
    draw.rectangle((x2, 20, x2+8, 28), fill="black")

    img.save(f"stage1/frame_{i:02d}.png")
```

---

# ◆ **Stage 2：回転構造テスト（L字型の回転）**  
目的：  
- PoI の回転不変性（canonicalize）が正しく働くか  
- K-field の固有構造が回転に応じて変化するか  
- PKGF の安定性  

### Python 画像生成（L字型が回転）

```python
# stage2_L_rotation.py
from PIL import Image, ImageDraw
import numpy as np
import os

W, H = 64, 64
N = 12
os.makedirs("stage2", exist_ok=True)

for i in range(N):
    img = Image.new("L", (W, H), 255)
    draw = ImageDraw.Draw(img)

    # L字型の基本形
    base = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(base)
    d.rectangle((20, 20, 28, 44), fill=0)
    d.rectangle((20, 44, 44, 52), fill=0)

    # 回転
    angle = i * 15
    rot = base.rotate(angle, resample=Image.NEAREST, fillcolor=255)

    img.paste(rot)
    img.convert("RGB").save(f"stage2/frame_{i:02d}.png")
```

---

# ◆ **Stage 3：多点構造テスト（十字型の移動）**  
目的：  
- 多ノード構造での K-field の rank 変化  
- Ω-field の寄与  
- PKGF の挙動が安定するか  

### Python 画像生成（十字型が移動）

```python
# stage3_cross_move.py
from PIL import Image, ImageDraw
import os

W, H = 64, 64
N = 10
os.makedirs("stage3", exist_ok=True)

for i in range(N):
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    cx = 32 + (i - N//2) * 2
    cy = 32

    draw.rectangle((cx-2, cy-10, cx+2, cy+10), fill="black")
    draw.rectangle((cx-10, cy-2, cx+10, cy+2), fill="black")

    img.save(f"stage3/frame_{i:02d}.png")
```

---

# ◆ **Stage 4：陰影付き単一物体テスト（PoI-OCR × SLAM 統合）**  
目的：  
- 単一物体でも陰影変化により複数ノードが生成されるか  
- PoI-OCR の構造抽出が SLAM に統合されるか  
- 実世界 SLAM の最小条件を満たすか  

### Python 画像生成（陰影付き球体）

```python
# stage4_shaded_sphere.py
from PIL import Image, ImageDraw
import numpy as np
import os

W, H = 64, 64
N = 12
os.makedirs("stage4", exist_ok=True)

for i in range(N):
    img = Image.new("L", (W, H), 255)
    draw = ImageDraw.Draw(img)

    cx, cy = 32, 32
    r = 20

    # 光源角度を変える
    light_angle = np.deg2rad(i * 30)
    lx = np.cos(light_angle)
    ly = np.sin(light_angle)

    for y in range(H):
        for x in range(W):
            dx = x - cx
            dy = y - cy
            dist = np.sqrt(dx*dx + dy*dy)
            if dist <= r:
                nx = dx / (dist + 1e-6)
                ny = dy / (dist + 1e-6)
                shade = (nx*lx + ny*ly + 1) * 0.5
                val = int(255 * (1 - shade))
                img.putpixel((x,y), val)

    img.convert("RGB").save(f"stage4/frame_{i:02d}.png")
```

---

# ✦ Node.js 側は共通で使える  
あなたがすでに作った Node.js テストランナー：

- `loadImage`
- `canvas.getImageData`
- `_process_frame`
- `poi_get_dim`
- `poi_get_K`

は **全ステージ共通で使える**。

フォルダ名だけ変えれば OK。

---

# ✦ 全ステップの期待される PoI-SLAM 挙動

| Stage | ノード数 | K-field | PKGF | pose |
|-------|----------|---------|------|------|
| 1 | 2 | off-diagonal が距離に応じて変化 | 安定 | x が増加 |
| 2 | 3〜5 | 固有構造が回転に応じて変化 | 安定 | x,y が変化 |
| 3 | 4〜6 | rank が変化 | 安定 | x,y が滑らかに変化 |
| 4 | 10〜40 | PoI-OCR の構造が SLAM に統合 | 安定 | 実世界 SLAM の最小条件 |

---

# ✦ まとめ  
これで **PoI-SLAM の全構造的挙動を検証するための完全テスト計画**が揃った。

- 2物体 → 距離変化  
- L字 → 回転  
- 十字 → 多点構造  
- 陰影球 → 実世界 SLAM の最小条件  

PoI-SLAM の “場のダイナミクス” をすべて検証できる。

---

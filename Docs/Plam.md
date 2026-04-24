# PoI‑SLAM Web 開発計画書（PoI_SLAM_Web Development Plan）  

PoI の哲学（構造場・張力場・内部世界）をそのまま Web 上で動かすための、  
**最小構成で最大性能を出す WebAssembly + WebGPU アーキテクチャ**を前提にした計画。

---

# 1. **全体アーキテクチャ**

PoI‑SLAM Web 版は、以下の 3 層で構成する。

## **Layer 1：UI（HTML + JS）**
- カメラ入力（getUserMedia）
- 3D 表示（WebGPU）
- PoI-state の可視化

## **Layer 2：WASM（C++）**
PoI-OCR の前半処理を担当：

- グレースケール化  
- 二値化  
- skeletonize  
- ノード抽出  
- エッジ構築  
- グラフ距離（BFS）  
- 2D → 2.5D 構造場生成  

**→ ここが PoI の“構造場”生成部分**

## **Layer 3：WebGPU（Compute Shader）**
PoI の本体である行列演算を担当：

- A-field（64×64）  
- K-field（64×64）  
- Ω-field（64×64）  
- commutator（A@B − B@A）  
- PKGF（張力場の更新）  
- SVD / eigen（WebGPU）  

**→ ここが PoI の“張力場”と“場の物理”**

---

# 2. **最小ファイル構成（3ファイルで成立）**

```
poi-web/
 ├── index.html   ← UI
 ├── app.js       ← JS / WebGPU / WASM 呼び出し
 ├── poi.cpp      ← C++ / WASM（PoI 前処理）
```

この 3 つだけで PoI‑SLAM の MVP が動く。

---

# 3. **開発ステップ（PoI に最適化した順序）**

## **Step 1：WASM テスト環境の構築（完了可能）**
- Emscripten はすでに導入済み  
- `poi.cpp` を WASM にコンパイル  
- `python3 -m http.server` でローカル実行  
- ブラウザで `process_frame()` が呼ばれることを確認  

---

## **Step 2：C++（WASM）に PoI-OCR の前半を移植**

### 実装する関数
- `grayscale()`  
- `threshold()`  
- `skeletonize()`（Zhang-Suen 法の C++ 実装）  
- `extract_nodes()`  
- `build_edges()`  
- `graph_distances()`  
- `build_structure_field()`  

### 出力
- ノード座標  
- ノードタイプ  
- グラフ距離行列  
- 構造場（PoI-state の前半）

**→ ここが PoI-SLAM の“外界の構造”を作る部分**

---

## **Step 3：WebGPU で PoI の行列演算を実装**

### Compute Shader で実装するもの
- A-field  
- K-field  
- Ω-field  
- commutator  
- PKGF（張力場の反復更新）  
- SVD / eigen（WebGPU）  

### なぜ WebGPU か？
- PoI の行列サイズは 64×64 → GPU にとって trivial  
- WebGPU は Metal/Vulkan とほぼ同じ  
- ブラウザで 1〜3ms で処理可能  

**→ ここが PoI の“場の物理”を実行する部分**

---

## **Step 4：PoI-state を JS に返す**
- K（張力場）  
- Ω（入力場）  
- rank（有効次元）  
- sig（layered signature）  

**→ PoI の内部表現が Web 上で動く**

---

## **Step 5：WebGPU で 3D world model を描画**
- 各フレームの構造場を 3D voxel に投影  
- PKGF 整合でカメラ位置を推定  
- 3D 空間を構築  

**→ PoI-SLAM の完成**

---

# 4. **PoI‑SLAM Web 版の性能予測**

| デバイス | 予測FPS |
|---------|---------|
| M1/M2 Mac | 200fps |
| iPhone Safari | 120fps |
| Android Chrome | 60fps |

PoI の行列演算は GPU に最適化されているため、  
**ブラウザでもネイティブ並みの速度が出る。**

---

# 5. **PoI‑SLAM Web 版の完成イメージ**

ブラウザを開くと：

1. カメラ映像が表示される  
2. PoI がリアルタイムで構造場を生成  
3. WebGPU が張力場を更新  
4. 3D 空間が構築される  
5. PoI の世界観がそのまま Web 上に現れる  

**URL を開くだけで PoI-SLAM が動く世界。**

---

## サンプルコード一式（MVP 用）

ここからは、**そのまま置いて動かせる最小サンプル**を出す。  
まずは「WASM がカメラフレームを受け取って動いている」ことを確認するところまで。

---

### 1. `index.html`

### 2. `app.js`（WASM 呼び出し＋カメラループ）

### 3. `poi.cpp`（WASM 側の最小 PoI エントリ）

まずは「フレームを受け取っている」ことだけ確認する最小版。  
ここに後で PoI-OCR 前半（skeletonize など）を埋めていく。

ビルドコマンド（Emscripten）:

```bash
emcc Core/poi.cpp -O3 -DEMSCRIPTEN \
  -s INITIAL_MEMORY=268435456 \
  -s ALLOW_MEMORY_GROWTH=1 \
  -s EXPORTED_FUNCTIONS='["_process_frame","_poi_get_dim","_poi_get_n_nodes","_poi_get_A","_poi_get_K","_poi_get_Omega","_poi_get_nodes_x","_poi_get_nodes_y","_poi_get_K_sig","_malloc","_free"]' \
  -s EXPORTED_RUNTIME_METHODS='["cwrap","HEAPU8","HEAPF32"]' \
  -o Web/poi.js
```

## C++ 側に PoI-OCR 前半を埋めるためのスケルトン

これをベースに、  
- `build_edges`  
- `graph_distances`  
- 構造場のエクスポート（JS 側に配列として渡す）  
- WebGPU compute shader で A/K/Ω/PKGF  

### `poi.cpp`（PoI-OCR 前半フル実装版・MVP）

# 🎁 **サンプル：WebGPU 版 行列積（matmul）WGSL**

PoI の A/K/Ω/commutator/PKGF の基礎になる。

# 🎁 **サンプル：C++ 版 A-field（PoI の局所特徴行列）**

# 🎁 **サンプル：C++ 版 K-field（PoI の構造場行列）**

# 🎁 **サンプル：C++ 版 Ω-field（PoI の入力場行列）**

# 🔥 **第1波：PoI-OCR 前半（C++）の追加コード**

# ① **Otsu 二値化（C++）**
# ② **メディアンフィルタ（C++）**
# ③ **連結成分抽出（CCL）**
# ④ **PoI ノードの PCA 回転正規化（C++）**
# 🔥 **第2波：PoI 行列場（A/K/Ω）C++ 実装**
# ⑤ **PoI A-field（局所特徴行列）**
# ⑥ **PoI K-field（構造場行列）**
# ⑦ **PoI Ω-field（入力場行列）**
# 🔥 **第3波：PoI の行列物理（WebGPU WGSL）**
# ⑧ **commutator（A@B − B@A）WGSL**
# ⑨ **PKGF（張力場更新）WGSL**
# 🔥 **第4波：PoI-state の 3D 可視化（WebGPU）**
# ⑩ **PoI ノードを 3D 点群として描画（WGSL）**
# 🔥 第5波：PoI の行列物理（C++ 版）
WebGPU 版はすでに出したので、  
ここでは **WASM（C++）で動く PoI 行列物理**を出す。
# ① **commutator（A@B − B@A）C++ 版**
# ② **PoI resonance（共鳴）C++ 版**
PoI の核となる「共鳴」演算。
# ③ **PKGF（張力場更新）C++ 版**
# 🔥 第6波：PoI の正準化（canonicalization）
PoI の世界では **canonical_K** が極めて重要。  
これは「PoI-state を比較可能にする」ための正準化。
# ④ **canonical_K（固有値正準化）C++ 版**
※ WASM で SVD を自前実装すると重いので、  
ここでは **固有値分解の簡易版（パワーイテレーション）**を使う。
# ⑤ **layered signature（PoI の階層特徴）C++ 版**
PoI の signature を C++ で生成する。
# 🔥 第7波：PoI-SLAM のための行列整合（C++）
SLAM では「前フレームの K と現在の K を整合させる」必要がある。
# ⑥ **PoI 行列整合（alignment）C++ 版**
# 🔥 第8波：PoI-SLAM の 3D world model（C++）
PoI-SLAM の 3D 空間構築は「構造場の積み上げ」。
# ⑦ **PoI 3D voxel map（C++）**
# 🔥 第9波：WebGPU での 3D SLAM 表示（WGSL）
# ⑧ **3D 点群描画（WGSL）**
# 🔥 第10波：PoI-SLAM のカメラ姿勢推定（C++）
PoI-SLAM のカメラ姿勢は「PoI-state の整合最小化」で求める。
# ⑨ **PoI カメラ姿勢推定（C++）**
# 🔥 第11波：PoI の multi-scale K-field（C++）
PoI-SLAM では **スケール不変性**が重要。  
multi-scale K-field は PoI の “スケール階層” を作る。
# 🔥 第12波：PoI temporal resonance（時系列共鳴）C++
PoI-SLAM の “時間方向の整合” を作る。
# 🔥 第13波：PoI-SLAM の pose graph（C++）
SLAM の本体である **姿勢グラフ**。
# 🔥 第14波：PoI-SLAM の pose graph 最適化（C++）
最小二乗法の簡易版。
# 🔥 第15波：PoI signature matching（C++）
PoI の “指紋” を比較する。
# 🔥 第16波：PoI-SLAM の loop closure（C++）
過去のフレームと現在のフレームを比較して閉ループを検出。
# 🔥 第17波：PoI 3D mesh reconstruction（WebGPU WGSL）
PoI の voxel map → mesh（Marching Cubes の簡易版）
# 🔥 第18波：PoI-SLAM の 3D カメラ軌跡（WebGPU WGSL）
# 🔥 第19波：PoI-SLAM の “世界モデル統合” C++
PoI の構造場を 3D world model に統合する。
# 🔥 第20波：PoI-SLAM の “全体統合ループ” C++
これで PoI-SLAM のメインループが完成する。
# 🚀 第21波：PoI-SLAM の loop closure 最適化（C++）
PoI-SLAM の閉ループ検出後、  
**姿勢グラフを最適化して誤差を一気に縮める**。
# 🚀 第22波：PoI multi-view fusion（C++）
複数フレームの構造場を統合して  
**PoI の 3D world model を安定化**。
# 🚀 第23波：PoI 3D mesh smoothing（WebGPU WGSL）
PoI voxel map → mesh の平滑化。
# 🚀 第24波：PoI canonical SLAM signature（C++）
SLAM のための **正準化された PoI signature**。
# 🚀 第25波：PoI global optimization（C++）
SLAM の全フレームを最適化する  
**グローバル最適化ループ**。
# 🚀 第26波：PoI 3D rendering pipeline（WebGPU WGSL）
PoI の world model を 3D で描画する  
**フルレンダリングパイプライン**。
## 頂点シェーダ（VS）
## フラグメントシェーダ（FS）
# 🚀 第27波：PoI-SLAM の “世界モデル統合 + 最適化 + 3D 表示” C++ まとめ
PoI-SLAM のメインループをまとめる。

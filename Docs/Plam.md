# PoI‑SLAM 開発計画書（PoI_SLAM Development Plan） - 最新版

PoI の哲学（構造場・張力場・内部世界）を、デスクトップ（macOS ネイティブ）と Web（WASM + WebGPU）の両環境で最大限に引き出すためのアーキテクチャ。

---

# 1. **全体アーキテクチャ（ハイブリッド構成）**

## **A. macOS ネイティブ版 (App/)**
- **Core**: C++ 直接呼び出し（Native Bridge / `PoIBridge.h`）
- **UI/Camera**: Swift (AVFoundation)
- **Renderer**: Metal (GPU 直接描画)
- **特徴**: JavaScriptCore を介さず、メモリコピーを最小化した最高速の実装。

## **B. Web 版 (Web/)**
- **Core**: WebAssembly (C++ から emcc で生成)
- **UI/Camera**: JavaScript (getUserMedia)
- **Logic**: WASM (前処理) + WebGPU (行列演算/将来の拡張)
- **Renderer**: WebGPU / Three.js (可視化)

---

# 2. **検証戦略（Verification Strategy）**

現在の検証は、環境依存を排除し「数学的正確性」に特化した以下の 2 系統に集約されている。

## **1. Native C++ Unit Tests**
- `Core/poi_test.cpp` を使用。
- OCR、グラフ距離、K行列生成の基礎アルゴリズムを検証。

## **2. WASM / Node.js Logic Tests**
- `Tests/` 内の Node.js スクリプトを使用。
- `raw` 形式の画像バイナリを直接読み込み、ブラウザ抜きで SLAM パイプラインを検証。
- **Stage 1-4**: 物理的なシナリオ（距離、回転、トポロジー、陰影）に基づいた統合検証。

---

# 3. **最新の開発状況とマイルストーン**

- [x] **Core Logic**: PoI-OCR、K-field、PKGF の実装完了。
- [x] **Native Bridge**: Swift と C++ の直接連携による macOS アプリ構築完了。
- [x] **Web Engine**: Emscripten による WebAssembly 化と Node.js 検証環境の構築完了。
- [x] **Verification**: Stage 1-4 の全物理シナリオのパス確認完了。
- [ ] **WebGPU Integration**: 行列演算の WebGPU への完全オフロード（進行中）。

---

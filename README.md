# Physics of Intelligence: PoI-SLAM Web & Native Research

知能を物理多様体上の幾何学的ダイナミクスとして再定義する学問体系「Physics of Intelligence (PoI)」の実証実験、およびその応用である並行鍵幾何流（PKGF）を用いたSLAMシステムの研究リポジトリです。

## 🌌 プロジェクト概要

本プロジェクトは、以下の三相サイクル（C-D-Uサイクル）を工学的に実装し、自己位置推定と環境地図作成を実現します。

- **Cause (構築)**: 外部刺激からの幾何学的構造抽出（PoI-OCR）
- **Divergence (解体)**: ノイズの除去と構造の粗視化
- **Unification (統合)**: 幾何学的フロー（PKGF）による論理構造の安定化と地図化

## 📂 ディレクトリ構造

```text
.
├── App/          # macOSネイティブアプリ (Swift / Metal)
├── Core/         # PoI物理エンジン中核 (C++ / PKGF実装)
├── Data/         # 実験用データセット (Raw画像 / フレームデータ)
├── Docs/         # 実装計画・機能テスト仕様書
├── References/   # 理論的背景・数学的公理・研究用Pythonスクリプト
├── Scripts/      # ビルド自動化・データ生成スクリプト
├── Tests/        # ユニットテスト・統合テスト (JS / C++)
├── Web/          # Web実行環境 (WASM / JavaScript / HTML)
├── build.sh*     # マスタービルドスクリプト
└── build_macos/  # ビルド成果物 (バイナリ / 中間生成物)
```

## 🛠 ビルドと実行

### macOS ネイティブアプリ
プロジェクトのルートディレクトリで以下のコマンドを実行してください。

```bash
./build.sh
```

ビルド完了後、バイナリを実行します。
```bash
./build_macos/PoISLAMApp
```

### Web / WASM 環境
`Web/` ディレクトリ内の資産を Web サーバー（Node.js 等）でホストしてください。

## 🧪 テストの実行

プロジェクトの品質を担保するため、C++ ユニットテストと JS/WASM 統合テストが用意されています。

```bash
./Scripts/run_tests.sh
```

- **C++ Unit Tests**: 物理エンジンの基礎アルゴリズム（Otsu二値化、骨格化、グラフ距離）を検証します。
- **JS/WASM Integration Tests**: 4段階のテストステージ（幾何学形状の移動・回転）を通じて、WASMエンジンの挙動を検証します。

## 🔬 主要な理論コンポーネント

- **Parallel Key Geometric Flow (PKGF)**: 多様体上の並行鍵 $K$ と意味ポテンシャル $\Omega$ の相互作用を記述する場の方程式 $\nabla K = [\Omega, K]$。
- **Sector Decomposition**: 知能のモジュール性を担保する 32 次元、4 セクターの接束分解。
- **Substrate Invariance**: 電子、生物、シリコンを問わない媒体不変な知能物理法則。

## 📜 ライセンス・著者

- **Author**: Fumio Miyata (2026)
- **Reference**: [Physics of Intelligence Theory](./References/PoI_Theory_jp.md)

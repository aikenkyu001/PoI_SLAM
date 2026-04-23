#!/bin/bash

# プロジェクトルートに移動
cd "$(dirname "$0")/.."

# ディレクトリ設定 (整理後の新パス)
APP_DIR="App/PoISLAMApp"
SRC_DIR="$APP_DIR/Sources"
CORE_DIR="Core"
BUILD_DIR="build_macos"
mkdir -p $BUILD_DIR

echo "--- Building Metal Shaders ---"
xcrun -sdk macosx metal -c $SRC_DIR/Shaders.metal -o $BUILD_DIR/Shaders.air
xcrun -sdk macosx metallib $BUILD_DIR/Shaders.air -o $BUILD_DIR/default.metallib

echo "--- Compiling C++ Core (Native) ---"
clang++ -c $CORE_DIR/poi.cpp -o $BUILD_DIR/poi.o -std=c++17 -O3

echo "--- Compiling Swift Application ---"
swiftc -o $BUILD_DIR/PoISLAMApp \
    $SRC_DIR/main.swift \
    $SRC_DIR/PoISLAMCore.swift \
    $SRC_DIR/CameraCapture.swift \
    $SRC_DIR/GridRenderer.swift \
    -import-objc-header $SRC_DIR/PoIBridge.h \
    $BUILD_DIR/poi.o \
    -framework Cocoa \
    -framework Metal \
    -framework MetalKit \
    -framework AVFoundation \
    -framework JavaScriptCore \
    -framework CoreVideo \
    -lc++ \
    -O

echo "--- Build Completed ---"
echo "To run the app: ./$BUILD_DIR/PoISLAMApp"

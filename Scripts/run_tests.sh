#!/bin/bash
# PoI-SLAM Test Runner
cd "$(dirname "$0")/.."

echo "--- Running C++ Unit Tests ---"
mkdir -p build_tests
clang++ Core/poi_test.cpp -o build_tests/unit_test -std=c++17 -O3
./build_tests/unit_test

echo -e "\n--- Running JS/WASM Integration Tests (Stage 1-4) ---"
# node Web/node_modules/jest/bin/jest.js Web/ --config Web/package.json # Jest を使う場合
node Tests/test_all_stages_raw.js

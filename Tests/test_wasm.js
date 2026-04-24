// test_wasm.js
const fs = require("fs");
const path = require("path");

// emcc で生成した WASM モジュールを require
let Module;
try {
    Module = require("../Web/poi.js");
} catch (e) {
    console.error("Error: poi.js not found. Please build WASM first.");
    process.exit(1);
}

Module.onRuntimeInitialized = async () => {
    console.log("WASM ready");

    // ---- 構造的なテストデータ生成 (64x64 RGBA) ----
    // 白背景に黒の十字を描画する
    const w = 64, h = 64;
    const data = new Uint8Array(w * h * 4);
    data.fill(255); // 全体を白(背景)にする

    const centerX = 32;
    const centerY = 32;

    // 横線 (黒 = 0)
    for (let x = 16; x < 48; x++) {
        const idx = (centerY * w + x) * 4;
        data[idx + 0] = 0; data[idx + 1] = 0; data[idx + 2] = 0;
    }
    // 縦線 (黒 = 0)
    for (let y = 16; y < 48; y++) {
        const idx = (y * w + centerX) * 4;
        data[idx + 0] = 0; data[idx + 1] = 0; data[idx + 2] = 0;
    }

    // ---- WASM メモリにコピー ----
    const ptr = Module._malloc(data.length);
    Module.HEAPU8.set(data, ptr);

    // ---- PoI 処理 ----
    console.log("Calling process_frame with a cross pattern...");
    Module._process_frame(ptr, w, h);

    // ---- 結果を取得 ----
    const dim = Module._poi_get_dim();
    const nNodes = Module._poi_get_n_nodes();

    console.log("Result: dim =", dim, "nodes =", nNodes);

    if (dim > 0) {
        const ptrK = Module._poi_get_K();
        const K = new Float32Array(Module.HEAPF32.buffer, ptrK, dim * dim);
        console.log("K[0..3] =", K.slice(0, 4));
        
        // 対角成分が 1 に近い（exp(-0/sigma)）か確認
        console.log("K[diag(0)] =", K[0]);

        if (K[0] > 0.5) {
            console.log("[SUCCESS] WASM integration test passed with structural data.");
        } else {
            console.error("[FAILURE] K field value is unexpected.");
        }
    } else {
        console.error("[FAILURE] No nodes detected even with structural data.");
    }

    Module._free(ptr);
    console.log("WASM test finished");
};

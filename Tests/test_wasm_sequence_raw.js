// Source/test_wasm_sequence_raw.js
const fs = require("fs");
const path = require("path");
const Module = require("../Web/poi.js"); 

const W = 64, H = 64;

Module.onRuntimeInitialized = async () => {
  console.log("WASM ready (Raw Mode)");

  // Data/Raw/stage1 を利用してテスト
  const stageDir = path.join(__dirname, "../Data/Raw/stage1");
  if (!fs.existsSync(stageDir)) {
      console.error("Error: Data/Raw/stage1 not found.");
      process.exit(1);
  }

  for (let i = 0; i < 10; i++) {
    const fname = path.join(stageDir, `frame_${i.toString().padStart(2, "0")}.raw`);
    if (!fs.existsSync(fname)) continue;
    const buffer = fs.readFileSync(fname);

    const ptr = Module._malloc(buffer.length);
    Module.HEAPU8.set(new Uint8Array(buffer), ptr);

    const t0 = Date.now();
    Module._process_frame(ptr, W, H);
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
      `frame ${i}: time=${t1 - t0}ms dim=${dim} nodes=${nNodes} K[0]=${K0.toFixed(4)}`
    );

    Module._free(ptr);
  }

  console.log("sequence test finished");
};

// Source/test_wasm_sequence_complex.js
const fs = require("fs");
const path = require("path");
const Module = require("./poi.js"); 

const W = 64, H = 64;

Module.onRuntimeInitialized = async () => {
  console.log("WASM ready (Complex Sequence Mode)");

  for (let i = 0; i < 10; i++) {
    const fname = path.join(__dirname, `../raw_frames_complex/frame_${i.toString().padStart(2, "0")}.raw`);
    const buffer = fs.readFileSync(fname);

    const ptr = Module._malloc(buffer.length);
    Module.HEAPU8.set(new Uint8Array(buffer), ptr);

    Module._process_frame(ptr, W, H);

    const dim = Module._poi_get_dim();
    const nNodes = Module._poi_get_n_nodes();

    let K_vals = "";
    if (dim >= 2) {
      const ptrK = Module._poi_get_K();
      const K = new Float32Array(Module.HEAPF32.buffer, ptrK, dim * dim);
      // K[0,1] つまり K[1] (非対角成分) を表示して相関の変化を見る
      K_vals = `K[0,0]=${K[0].toFixed(4)} K[0,1]=${K[1].toFixed(4)}`;
    } else {
      K_vals = "dim < 2 (cannot observe correlation)";
    }

    console.log(
      `frame ${i}: nodes=${nNodes} dim=${dim} ${K_vals}`
    );

    Module._free(ptr);
  }

  console.log("complex sequence test finished");
};

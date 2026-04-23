// Source/test_wasm_sequence.js
const fs = require("fs");
const { createCanvas, loadImage } = require("canvas");
const Module = require("./poi.js"); 

Module.onRuntimeInitialized = async () => {
  console.log("WASM ready");

  for (let i = 0; i < 10; i++) {
    const fname = `./frames/frame_${i.toString().padStart(2, "0")}.png`;
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
      `frame ${i}: time=${t1 - t0}ms dim=${dim} nodes=${nNodes} K[0]=${K0.toFixed(4)}`
    );

    Module._free(ptr);
  }

  console.log("sequence test finished");
};

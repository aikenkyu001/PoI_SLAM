// Source/test_all_stages_raw.js
const fs = require("fs");
const path = require("path");
const Module = require("../Web/poi.js"); 

const W = 64, H = 64;

async function runStage(name, count) {
    console.log(`\n--- Stage: ${name} ---`);
    for (let i = 0; i < count; i++) {
        const fname = path.join(__dirname, `../Data/Raw/${name}/frame_${i.toString().padStart(2, "0")}.raw`);
        if (!fs.existsSync(fname)) continue;
        const buffer = fs.readFileSync(fname);

        const ptr = Module._malloc(buffer.length);
        Module.HEAPU8.set(new Uint8Array(buffer), ptr);

        Module._process_frame(ptr, W, H);

        const dim = Module._poi_get_dim();
        const nNodes = Module._poi_get_n_nodes();
        
        let kInfo = "";
        if (dim >= 2) {
            const ptrK = Module._poi_get_K();
            const K = new Float32Array(Module.HEAPF32.buffer, ptrK, dim * dim);
            kInfo = `K[0,1]=${K[1].toFixed(4)}`;
        }

        console.log(`frame ${i}: nodes=${nNodes} dim=${dim} ${kInfo}`);
        Module._free(ptr);
    }
}

Module.onRuntimeInitialized = async () => {
    await runStage("stage1", 10);
    await runStage("stage2", 12);
    await runStage("stage3", 10);
    await runStage("stage4", 12);
    console.log("\nAll stages completed.");
};

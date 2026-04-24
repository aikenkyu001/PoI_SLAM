console.log("app.js loaded");

const video = document.getElementById("cam");
const canvas = document.getElementById("view");
const ctx = canvas.getContext("2d", { willReadFrequently: true });
const flipBtn = document.getElementById("flip-btn");

// WASM 処理用の固定解像度
const PROC_W = 64;
const PROC_H = 64;
const offscreen = document.createElement("canvas");
offscreen.width = PROC_W;
offscreen.height = PROC_H;
const octx = offscreen.getContext("2d", { willReadFrequently: true });

let currentFacingMode = "environment";
let currentStream = null;

// Firefox 判定
const isFirefox = navigator.userAgent.toLowerCase().includes("firefox");

async function startCam() {
  if (currentStream) {
    currentStream.getTracks().forEach(track => track.stop());
    currentStream = null;
  }
  video.srcObject = null;

  const constraints = {
    video: { 
      facingMode: currentFacingMode 
    }
  };

  try {
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    currentStream = stream;
    video.srcObject = stream;
    video.setAttribute("playsinline", true);
    await video.play();
  } catch (err) {
    console.error("Camera access failed:", err);
    // 失敗した場合は最小限の構成でリトライ
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      currentStream = stream;
      video.srcObject = stream;
      await video.play();
    } catch (e) {
      alert("Error: " + e.message);
    }
  }
}

// Firefox の場合のみボタンを表示し、イベントを登録
if (isFirefox) {
  flipBtn.style.display = "block";
  flipBtn.addEventListener("click", async () => {
    if (flipBtn.disabled) return;
    flipBtn.disabled = true;
    flipBtn.textContent = "Switching...";
    
    currentFacingMode = (currentFacingMode === "user") ? "environment" : "user";
    await startCam();
    
    flipBtn.textContent = "Switch Camera";
    flipBtn.disabled = false;
  });
}

async function waitWasm() {
  if (window._wasmReady) return;
  await new Promise(resolve => {
    const timer = setInterval(() => {
      if (window._wasmReady) {
        clearInterval(timer);
        resolve();
      }
    }, 10);
  });
}

let ptr = null;

async function main() {
  await startCam();
  await waitWasm();

  const process    = Module.cwrap("process_frame", null, ["number", "number", "number"]);
  const getDim     = Module.cwrap("poi_get_dim", "number", []);
  const getNNodes  = Module.cwrap("poi_get_n_nodes", "number", []);
  const getNodesX  = Module.cwrap("poi_get_nodes_x", "number", []);
  const getNodesY  = Module.cwrap("poi_get_nodes_y", "number", []);
  const getK       = Module.cwrap("poi_get_K", "number", []);

  function loop() {
    if (video.videoWidth === 0) {
      requestAnimationFrame(loop);
      return;
    }

    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
    }

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    octx.drawImage(video, 0, 0, PROC_W, PROC_H);
    const frame = octx.getImageData(0, 0, PROC_W, PROC_H);

    if (!ptr) {
      ptr = Module._malloc(PROC_W * PROC_H * 4);
    }
    Module.HEAPU8.set(frame.data, ptr);

    process(ptr, PROC_W, PROC_H);

    const dim    = getDim();
    const nNodes = getNNodes();

    if (nNodes > 0 && dim > 0) {
      const ptrX = getNodesX();
      const ptrY = getNodesY();
      const ptrK = getK();

      const nodesX = new Float32Array(Module.HEAPF32.buffer, ptrX, nNodes);
      const nodesY = new Float32Array(Module.HEAPF32.buffer, ptrY, nNodes);
      const K      = new Float32Array(Module.HEAPF32.buffer, ptrK, dim * dim);

      for (let i = 0; i < nNodes; i++) {
        const px = (nodesX[i] + 1.0) * 0.5 * canvas.width;
        const py = (1.0 - nodesY[i]) * 0.5 * canvas.height;

        const zRaw = (i < dim) ? K[i * dim + i] : 0.0;
        const r = Math.min(255, Math.max(0, zRaw * 100));
        const g = Math.min(255, Math.max(0, 255 - Math.abs(zRaw - 0.5) * 255));
        const b = Math.min(255, Math.max(0, 255 - zRaw * 255));

        ctx.fillStyle = `rgba(${r},${g},${b},0.9)`;
        ctx.beginPath();
        ctx.arc(px, py, 4, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    requestAnimationFrame(loop);
  }
  loop();
}

main().catch(err => console.error(err));

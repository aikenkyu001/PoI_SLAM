/**
 * @jest-environment jsdom
 */

// Module (WASM) の完全モック
global.Module = {
  ready: Promise.resolve(),
  cwrap: jest.fn(() => jest.fn()),
  _malloc: jest.fn(() => 1234),
  _free: jest.fn(),
  HEAPU8: { set: jest.fn() },
  HEAPF32: { buffer: new ArrayBuffer(4096) },

  _poi_get_dim: jest.fn(() => 4),
  _poi_get_n_nodes: jest.fn(() => 10),
  _poi_get_K: jest.fn(() => 200),
  _poi_get_Omega: jest.fn(() => 300),
  _poi_get_A: jest.fn(() => 400),
};

// ブラウザ API のモック
navigator.mediaDevices = {
  getUserMedia: jest.fn(() => Promise.resolve({
    getTracks: () => [{ stop: jest.fn() }]
  }))
};

// HTML 要素のセットアップ
document.body.innerHTML = `
  <video id="cam"></video>
  <canvas id="view"></canvas>
`;

const video = document.getElementById("cam");
const canvas = document.getElementById("view");

// video のプロパティとメソッドをモック
Object.defineProperties(video, {
  videoWidth: { get: () => 640 },
  videoHeight: { get: () => 480 },
});

// Canvas API のモック
canvas.getContext = jest.fn(() => ({
  drawImage: jest.fn(),
  getImageData: jest.fn(() => ({
    data: new Uint8ClampedArray(640 * 480 * 4)
  })),
}));

// requestAnimationFrame のモック
global.requestAnimationFrame = jest.fn();

test("app.js main() initializes and processes a frame", async () => {
  jest.resetModules();
  
  // require する前に、startCam の Promise を解決させる仕掛けを施す
  // app.js の loop 開始まで進めるため、onloadedmetadata を即座に呼ぶ
  setTimeout(() => {
    if (video.onloadedmetadata) video.onloadedmetadata();
  }, 10);

  require("./app.js");

  // 非同期処理の連鎖を待つ
  for(let i=0; i<20; i++) {
    await new Promise(resolve => setTimeout(resolve, 50));
  }

  // Module.cwrap が呼ばれたか
  expect(global.Module.cwrap).toHaveBeenCalledWith("process_frame", null, ["number", "number", "number"]);
  
  // getUserMedia が呼ばれたか
  expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled();

  console.log("[SUCCESS] app.js initialization test passed.");
});

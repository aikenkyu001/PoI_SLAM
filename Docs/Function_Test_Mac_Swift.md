# ◆ Swift で PoI‑SLAM を動かすアプリ構築計画（全体像）

以下の 4 ステップでアプリが完成する：

1. **WASM（poi.wasm）を Swift からロードして関数を呼び出す**  
2. **AVFoundation で Mac のカメラ映像を取得し、64×64 RGBA に変換**  
3. **WASM の process_frame() に渡して PoI‑SLAM を実行**  
4. **MetalKit で格子（Grid）を Z 方向に変形して SLAM‑MAP を描画**

この 4 つが揃えば、  
**PoI‑SLAM がリアルタイムで世界をどう“見ているか”を可視化できるアプリ**が完成する。

---

# ◆ まずはアプリの構成図

```
┌──────────────────────────────┐
│        Swift macOS App        │
│  ┌────────────────────────┐  │
│  │  AVFoundation Camera    │──┐  64×64 RGBA
│  └────────────────────────┘  │
│                               ▼
│  ┌────────────────────────┐  │
│  │   WASM PoI‑SLAM Core    │  │
│  │  process_frame()        │  │
│  │  poi_get_K()            │  │
│  │  poi_get_world_voxels() │  │
│  └────────────────────────┘  │
│                               ▼
│  ┌────────────────────────┐  │
│  │   Metal Grid Renderer   │  │
│  │   Z = world_voxels(x,y) │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

---

# ◆ ステップ 1：WASM を Swift からロードする

Swift では **JavaScriptCore** を使うと WASM をそのまま実行できる。

以下は **poi.wasm を読み込み、process_frame を呼び出せる状態にする最小コード**。

```swift
import Foundation
import JavaScriptCore

class PoISLAM {
    private let context = JSContext()!
    private var exports: JSValue?

    init() {
        let wasmURL = Bundle.main.url(forResource: "poi", withExtension: "wasm")!
        let wasmData = try! Data(contentsOf: wasmURL)

        let js = """
        var wasmBytes = new Uint8Array(\(wasmData));
        WebAssembly.instantiate(wasmBytes, {}).then(result => {
            globalThis.exports = result.instance.exports;
        });
        """

        context.evaluateScript(js)

        // 少し待って exports がロードされるのを待つ
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            self.exports = self.context.objectForKeyedSubscript("exports")
        }
    }

    func processFrame(_ rgba: [UInt8], width: Int, height: Int) {
        guard let exports = exports else { return }

        let ptr = exports.objectForKeyedSubscript("malloc")!.call(withArguments: [rgba.count])!.toInt32()
        let heap = context.objectForKeyedSubscript("HEAPU8")!

        for i in 0..<rgba.count {
            heap.setObject(rgba[i], atIndexedSubscript: Int(ptr) + i)
        }

        exports.objectForKeyedSubscript("process_frame")!.call(withArguments: [ptr, width, height])
        exports.objectForKeyedSubscript("free")!.call(withArguments: [ptr])
    }
}
```

---

# ◆ ステップ 2：AVFoundation でカメラ映像を取得

以下は **64×64 の RGBA バッファを生成して WASM に渡すコード**。

```swift
import AVFoundation

class CameraCapture: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    var onFrame: (([UInt8]) -> Void)?

    func start() {
        let session = AVCaptureSession()
        session.sessionPreset = .vga640x480

        let device = AVCaptureDevice.default(for: .video)!
        let input = try! AVCaptureDeviceInput(device: device)
        session.addInput(input)

        let output = AVCaptureVideoDataOutput()
        output.setSampleBufferDelegate(self, queue: DispatchQueue(label: "cam"))
        session.addOutput(output)

        session.startRunning()
    }

    func captureOutput(_ output: AVCaptureOutput,
                       didOutput sampleBuffer: CMSampleBuffer,
                       from connection: AVCaptureConnection) {

        guard let pixel = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }

        CVPixelBufferLockBaseAddress(pixel, .readOnly)
        let width = CVPixelBufferGetWidth(pixel)
        let height = CVPixelBufferGetHeight(pixel)
        let base = CVPixelBufferGetBaseAddress(pixel)!.assumingMemoryBound(to: UInt8.self)

        // ここで 64×64 に縮小して RGBA を作る
        var rgba = [UInt8](repeating: 255, count: 64 * 64 * 4)

        for y in 0..<64 {
            for x in 0..<64 {
                let sx = x * width / 64
                let sy = y * height / 64
                let offset = (sy * width + sx) * 4

                rgba[(y*64 + x)*4 + 0] = base[offset + 0]
                rgba[(y*64 + x)*4 + 1] = base[offset + 1]
                rgba[(y*64 + x)*4 + 2] = base[offset + 2]
                rgba[(y*64 + x)*4 + 3] = 255
            }
        }

        CVPixelBufferUnlockBaseAddress(pixel, .readOnly)

        onFrame?(rgba)
    }
}
```

---

# ◆ ステップ 3：PoI‑SLAM にフレームを渡す

```swift
let slam = PoISLAM()
let cam = CameraCapture()

cam.onFrame = { rgba in
    slam.processFrame(rgba, width: 64, height: 64)
}

cam.start()
```

これで **リアルタイムで PoI‑SLAM が動く**。

---

# ◆ ステップ 4：Metal で格子を Z 変形して SLAM‑MAP を描画

以下は **MetalKit の最小レンダラー**で、  
PoI‑SLAM の world_voxels を Z として格子を変形するコード。

```swift
class GridRenderer: NSObject, MTKViewDelegate {
    var device: MTLDevice!
    var pipeline: MTLRenderPipelineState!
    var slam: PoISLAM!

    init(view: MTKView, slam: PoISLAM) {
        self.slam = slam
        self.device = view.device!
        super.init()

        let library = device.makeDefaultLibrary()!
        let desc = MTLRenderPipelineDescriptor()
        desc.vertexFunction = library.makeFunction(name: "grid_vertex")
        desc.fragmentFunction = library.makeFunction(name: "grid_frag")
        desc.colorAttachments[0].pixelFormat = view.colorPixelFormat

        pipeline = try! device.makeRenderPipelineState(descriptor: desc)
    }

    func draw(in view: MTKView) {
        guard let pass = view.currentRenderPassDescriptor,
              let cmd = device.makeCommandQueue()!.makeCommandBuffer(),
              let enc = cmd.makeRenderCommandEncoder(descriptor: pass)
        else { return }

        enc.setRenderPipelineState(pipeline)

        // ここで world_voxels から Z 値を取得してバッファに渡す
        // Z = world_voxels[x,y] の最大値

        enc.drawPrimitives(type: .triangle, vertexStart: 0, vertexCount: 6 * 32 * 32)
        enc.endEncoding()
        cmd.present(view.currentDrawable!)
        cmd.commit()
    }
}
```

Metal シェーダ（grid_vertex.metal）：

```metal
vertex float4 grid_vertex(uint vid [[vertex_id]],
                          constant float3 *pos [[buffer(0)]],
                          constant float *zmap [[buffer(1)]])
{
    float3 p = pos[vid];
    p.z = zmap[vid];
    return float4(p, 1.0);
}
```

---

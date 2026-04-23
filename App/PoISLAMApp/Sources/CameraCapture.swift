import AVFoundation
import CoreVideo

class CameraCapture: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    var onFrame: (([UInt8]) -> Void)?
    private let session = AVCaptureSession()
    private var frameCount = 0

    func start() {
        // print("[Camera] Starting session...")
        session.sessionPreset = .vga640x480
        guard let device = AVCaptureDevice.default(for: .video),
              let input = try? AVCaptureDeviceInput(device: device) else {
            // print("[Camera] ERROR: Could not find camera device.")
            return
        }
        
        if session.canAddInput(input) { session.addInput(input) }
        
        let output = AVCaptureVideoDataOutput()
        // BGRA 32bit に固定
        output.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA]
        output.setSampleBufferDelegate(self, queue: DispatchQueue(label: "cam_queue"))
        
        if session.canAddOutput(output) { session.addOutput(output) }
        
        session.startRunning()
        // print("[Camera] Session started.")
    }

    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        frameCount += 1
        /*
        if frameCount % 100 == 0 {
            print("[Camera] Captured frames: \(frameCount)")
        }
        */
        
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        
        CVPixelBufferLockBaseAddress(pixelBuffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly) }
        
        let width = CVPixelBufferGetWidth(pixelBuffer)
        let height = CVPixelBufferGetHeight(pixelBuffer)
        let bytesPerRow = CVPixelBufferGetBytesPerRow(pixelBuffer)
        
        guard let baseAddress = CVPixelBufferGetBaseAddress(pixelBuffer) else { return }
        let ptr = baseAddress.assumingMemoryBound(to: UInt8.self)
        
        // 64x64 RGBA にダウンサンプリング
        let targetDim = 64
        var rgba = [UInt8](repeating: 255, count: targetDim * targetDim * 4)
        
        for y in 0..<targetDim {
            for x in 0..<targetDim {
                let sx = x * width / targetDim
                let sy = y * height / targetDim
                
                // ストライド (bytesPerRow) を考慮したオフセット計算
                let offset = (sy * bytesPerRow) + (sx * 4)
                let targetIdx = (y * targetDim + x) * 4
                
                // BGRA -> RGBA 変換
                rgba[targetIdx + 0] = ptr[offset + 2] // R
                rgba[targetIdx + 1] = ptr[offset + 1] // G
                rgba[targetIdx + 2] = ptr[offset + 0] // B
                rgba[targetIdx + 3] = 255            // A
            }
        }
        
        onFrame?(rgba)
    }
}

import Cocoa
import MetalKit

class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    var mtkView: MTKView!
    var renderer: GridRenderer!
    var slam: PoISLAM!
    var cam: CameraCapture!

    func applicationDidFinishLaunching(_ notification: Notification) {
        // PoI-SLAM と カメラの初期化
        slam = PoISLAM()
        cam = CameraCapture()

        // ウィンドウの設定
        let rect = NSRect(x: 0, y: 0, width: 800, height: 600)
        window = NSWindow(contentRect: rect,
                          styleMask: [.titled, .closable, .miniaturizable, .resizable],
                          backing: .buffered, defer: false)
        window.center()
        window.title = "PoI-SLAM macOS Prototype"
        window.makeKeyAndOrderFront(nil)

        // MetalView の設定
        mtkView = MTKView(frame: window.contentView!.frame, device: MTLCreateSystemDefaultDevice())
        mtkView.autoresizingMask = [.width, .height]
        mtkView.clearColor = MTLClearColor(red: 0.1, green: 0.1, blue: 0.2, alpha: 1.0) // 濃紺
        window.contentView?.addSubview(mtkView)

        // レンダラーの設定
        renderer = GridRenderer(view: mtkView, slam: slam)
        mtkView.delegate = renderer

        // カメラループの開始
        cam.onFrame = { [weak self] rgba in
            self?.renderer.updateCameraTexture(rgba: rgba)
            self?.slam.processFrame(rgba, width: 64, height: 64)
        }
        cam.start()
        
        // print("Application launched. PoI-SLAM is running.")
    }
    
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}

// アプリの起動
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()

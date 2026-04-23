import Foundation
import JavaScriptCore

// 簡易版 PoISLAM クラス (Core部分のみ)
class PoISLAMTester {
    private let context = JSContext()!
    private var exports: JSValue?
    private var isReady = false

    init() {
        let wasmPath = "Source/poi.wasm"
        guard let wasmData = try? Data(contentsOf: URL(fileURLWithPath: wasmPath)) else {
            print("Error: Could not load poi.wasm")
            return
        }

        let js = """
        var wasmBytes = new Uint8Array([\(wasmData.map { String($0) }.joined(separator: ","))]);
        WebAssembly.instantiate(wasmBytes, {}).then(result => {
            globalThis.exports = result.instance.exports;
            globalThis.HEAPU8 = new Uint8Array(result.instance.exports.memory.buffer);
        });
        """
        context.evaluateScript(js)

        while self.context.objectForKeyedSubscript("exports").isUndefined {
            Thread.sleep(forTimeInterval: 0.1)
        }
        self.exports = self.context.objectForKeyedSubscript("exports")
        self.isReady = true
        print("PoI-SLAM WASM Core is Ready in Swift CLI")
    }

    func test() {
        guard isReady, let exports = exports else { return }
        let dim = exports.objectForKeyedSubscript("poi_get_dim")!.call(withArguments: [])!.toInt32()
        print("Initial PoI Dim in Swift: \(dim)")
    }
}

let tester = PoISLAMTester()
tester.test()

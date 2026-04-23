import MetalKit

class GridRenderer: NSObject, MTKViewDelegate {
    var device: MTLDevice!
    var commandQueue: MTLCommandQueue!
    var pipelineState: MTLRenderPipelineState!
    var bgPipelineState: MTLRenderPipelineState!
    var slam: PoISLAM!
    
    private var camTexture: MTLTexture?
    private let textureLoader = MTKTextureLoader(device: MTLCreateSystemDefaultDevice()!)

    init(view: MTKView, slam: PoISLAM) {
        self.slam = slam
        self.device = view.device!
        self.commandQueue = device.makeCommandQueue()
        super.init()

        // print("[Renderer] Loading Metal library...")
        let bundle = Bundle.main
        let libPath = bundle.path(forResource: "default", ofType: "metallib")
        
        guard let path = libPath, let library = try? device.makeLibrary(filepath: path) else {
            // print("[Renderer] ERROR: Could not load default.metallib")
            return
        }
        
        // Grid Pipeline
        let pipelineDescriptor = MTLRenderPipelineDescriptor()
        pipelineDescriptor.vertexFunction = library.makeFunction(name: "grid_vertex")
        pipelineDescriptor.fragmentFunction = library.makeFunction(name: "grid_frag")
        pipelineDescriptor.colorAttachments[0].pixelFormat = view.colorPixelFormat
        
        // Background Pipeline
        let bgDescriptor = MTLRenderPipelineDescriptor()
        bgDescriptor.vertexFunction = library.makeFunction(name: "bg_vertex")
        bgDescriptor.fragmentFunction = library.makeFunction(name: "bg_frag")
        bgDescriptor.colorAttachments[0].pixelFormat = view.colorPixelFormat

        do {
            pipelineState = try device.makeRenderPipelineState(descriptor: pipelineDescriptor)
            bgPipelineState = try device.makeRenderPipelineState(descriptor: bgDescriptor)
            // print("[Renderer] SUCCESS: Metal pipeline states created")
        } catch {
            print("[Renderer] ERROR: Failed to create pipeline state: \(error)")
        }
    }

    func updateCameraTexture(rgba: [UInt8]) {
        let descriptor = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: .rgba8Unorm,
                                                                 width: 64,
                                                                 height: 64,
                                                                 mipmapped: false)
        descriptor.usage = [.shaderRead]
        let texture = device.makeTexture(descriptor: descriptor)
        
        let region = MTLRegionMake2D(0, 0, 64, 64)
        texture?.replace(region: region, mipmapLevel: 0, withBytes: rgba, bytesPerRow: 64 * 4)
        self.camTexture = texture
    }

    func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) {}

    private var frameCount = 0

    func draw(in view: MTKView) {
        frameCount += 1
        guard let drawable = view.currentDrawable,
              let descriptor = view.currentRenderPassDescriptor,
              let commandBuffer = commandQueue.makeCommandBuffer(),
              let encoder = commandBuffer.makeRenderCommandEncoder(descriptor: descriptor) else { return }
        
        struct NodeVertex {
            var px, py, pz, pw: Float
            var r, g, b, a: Float
        }

        // 1. Background Camera View
        if let tex = camTexture {
            encoder.setRenderPipelineState(bgPipelineState)
            encoder.setFragmentTexture(tex, index: 0)
            encoder.drawPrimitives(type: .triangleStrip, vertexStart: 0, vertexCount: 4)
        }

        // 2. PoI Nodes (World Space View)
        let nodesX = slam.getNodesX()
        let nodesY = slam.getNodesY()
        let kMatrix = slam.getK()
        let dim = slam.getDim()
        let poseX = slam.getPoseX()
        
        let nNodes = nodesX.count
        if nNodes > 0 {
            encoder.setRenderPipelineState(pipelineState)
            
            var vertices = [NodeVertex]()
            for i in 0..<nNodes {
                let zRaw = (i < dim) ? kMatrix[i * dim + i] : 0
                
                // 現在のフレームの点は映像にピッタリ重ねるため補正なし(Camera Space)
                let px = nodesX[i]
                let py = nodesY[i]
                
                // 色合い調整
                let r = zRaw * 0.4
                let g = 1.0 - abs(zRaw - 0.5)
                let b = 1.0 - zRaw
                
                vertices.append(NodeVertex(
                    px: px, py: py, pz: zRaw * 0.3, pw: 1.0,
                    r: r, g: g, b: b, a: 0.9
                ))
            }
            
            let vBuffer = device.makeBuffer(bytes: vertices, length: vertices.count * MemoryLayout<NodeVertex>.stride, options: [])
            encoder.setVertexBuffer(vBuffer, offset: 0, index: 0)
            encoder.drawPrimitives(type: .point, vertexStart: 0, vertexCount: nNodes)
        }

        // 3. SLAM-MAP (Accumulated 3D Voxels)
        if frameCount % 5 == 0 {
            let voxels = slam.getVoxels()
            if !voxels.isEmpty {
                var mapVertices = [NodeVertex]()
                let step = 8 
                
                for zi in stride(from: 0, to: 64, by: 16) {
                    let layerOffset = zi * 128 * 128
                    for yi in stride(from: 0, to: 128, by: step) {
                        for xi in stride(from: 0, to: 128, by: step) {
                            let val = voxels[layerOffset + yi*128 + xi]
                            if val > 0.05 {
                                let mx = Float(xi) / 64.0 - 1.0 - (poseX * 0.5)
                                let my = 1.0 - Float(yi) / 64.0
                                let mz = Float(zi) / 64.0 - 0.5
                                
                                mapVertices.append(NodeVertex(
                                    px: mx, py: my, pz: mz, pw: 1.0,
                                    r: 0.5, g: 0.5, b: 0.6, a: 0.4
                                ))
                            }
                        }
                    }
                }
                
                if !mapVertices.isEmpty {
                    let mapBuffer = device.makeBuffer(bytes: mapVertices, length: mapVertices.count * MemoryLayout<NodeVertex>.stride, options: [])
                    encoder.setVertexBuffer(mapBuffer, offset: 0, index: 0)
                    encoder.drawPrimitives(type: .point, vertexStart: 0, vertexCount: mapVertices.count)
                }
            }
        }
        
        encoder.endEncoding()
        commandBuffer.present(drawable)
        commandBuffer.commit()
    }
}

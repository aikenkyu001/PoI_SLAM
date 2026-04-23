import Foundation

class PoISLAM {
    init() {
        // print("[PoI-Core] Initializing Native C++ Engine...")
    }

    func processFrame(_ rgba: [UInt8], width: Int, height: Int) {
        // Swift の配列ポインタを直接 C++ 関数に渡す
        var mutableRgba = rgba
        mutableRgba.withUnsafeMutableBufferPointer { buffer in
            if let baseAddress = buffer.baseAddress {
                process_frame(baseAddress, Int32(width), Int32(height))
            }
        }
        
        /*
        let nodes = poi_get_n_nodes()
        if nodes > 0 {
            print("[PoI-Core] Processed: nodes = \(nodes)")
        }
        */
    }

    func getDim() -> Int {
        return Int(poi_get_dim())
    }

    func getK() -> [Float] {
        let dim = Int(poi_get_dim())
        if dim == 0 { return [] }

        guard let ptrK = poi_get_K() else { return [] }
        
        let count = dim * dim
        let buffer = UnsafeBufferPointer(start: ptrK, count: count)
        return Array(buffer)
    }

    func getNodesX() -> [Float] {
        let n = Int(poi_get_n_nodes())
        if n == 0 { return [] }
        guard let ptr = poi_get_nodes_x() else { return [] }
        return Array(UnsafeBufferPointer(start: ptr, count: n))
    }

    func getNodesY() -> [Float] {
        let n = Int(poi_get_n_nodes())
        if n == 0 { return [] }
        guard let ptr = poi_get_nodes_y() else { return [] }
        return Array(UnsafeBufferPointer(start: ptr, count: n))
    }

    func getVoxels() -> [Float] {
        // 128 x 128 x 64 = 1,048,576 voxels
        let count = 128 * 128 * 64
        guard let ptr = poi_get_world_voxels() else { return [] }
        return Array(UnsafeBufferPointer(start: ptr, count: count))
    }

    func getPoseX() -> Float {
        return poi_get_pose_x()
    }
}

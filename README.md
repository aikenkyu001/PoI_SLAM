# PoI-SLAM: Structural Field-Based Monocular SLAM
### Experimental Research based on the "Physics of Intelligence" (PoI) Theory

Author: Fumio Miyata  
Date: April 2026  
DOI: [https://doi.org/10.5281/zenodo.19705165](https://doi.org/10.5281/zenodo.19705165)  
Repository: [https://github.com/aikenkyu001/PoI_SLAM](https://github.com/aikenkyu001/PoI_SLAM)  
---

## **Abstract**

**PoI-SLAM** is a novel monocular SLAM (Simultaneous Localization and Mapping) system that demonstrates the **Physics of Intelligence (PoI)** theory. Unlike traditional SLAM systems that rely on point-cloud matching or complex non-linear optimization, PoI-SLAM treats the world as a **Structural Relationship Field (K-field)** and describes its temporal evolution through the **Parallel Key Geometric Flow (PKGF)**.

This project implements and verifies the core concepts of PoI: **Canonical Decomposition Unit (CDU)**, **A-field (Feature Field)**, **K-field (Structure Field)**, and **PKGF-based Dynamics**.

---

## **1. Core Theoretical Framework**

### **1.1 The K-field (Structure Field)**
The world is represented not as a set of points, but as the internal geometry between nodes (graph distance $D$), transformed via an exponential kernel into a structure field $K$.

### **1.2 CDU (Canonical Decomposition Unit)**
A canonicalization mechanism that ensures structural isomorphism across different viewpoints. Implemented using PCA-based axis alignment and local structural histograms [5] to maintain stable node ordering.

### **1.3 PKGF (Parallel Key Geometric Flow)**
The "physics" of the system follows a first-order update equation based on PoI axioms [6]:
$$K_{t+1} = K_t + \eta (\Omega_t - K_t)$$
where $\Omega$ is the driving field constructed from the A-field. This flow naturally exhibits noise absorption, inertia, and convergence.

---

## **2. System Pipeline**

1.  **PoI-OCR (Structure Extraction)**: Binarization via Otsu's method [1], skeletonization using the Zhang-Suen algorithm [2], and node classification (End, Line, Branch, Cross).
2.  **Internal Geometry ($D$)**: Building graph distances using BFS and cluster centroid augmentation, aligned with recent path-centric extraction paradigms [4].
3.  **Canonicalization (CDU)**: Aligning nodes to a canonical coordinate system to stabilize the $K$-field.
4.  **Field Dynamics (PKGF)**: Evolving the fields and extracting motion signatures from $K$-matrix modes. This geometric approach shares the goal of maximizing computational efficiency with recent transformer-based acceleration techniques [6].
5.  **PoI-World Mapping**: Accumulating persistent structures into a voxel map with a decay factor to eliminate transient noise, drawing inspiration from high-fidelity flow-guided mapping [3].

---

## **3. Comparison with State-of-the-Art**

Unlike traditional feature-based SLAM systems such as ORB-SLAM [7], which rely on computationally expensive descriptor matching and RANSAC, PoI-SLAM operates on the intrinsic physics of structural fields. This allows for substrate-invariant operation with significantly lower latency (< 2ms per frame).

---

## **4. Project Structure**

```
PoI_SLAM/
├── Core/            # C++ implementation of PoI Engine (OCR, Fields, PKGF)
├── App/             # macOS Application (Swift/Metal)
├── Web/             # Web implementation (WebAssembly/JS)
├── Data/            # Test frames and Raw stage data
├── Docs/            # Research plans and functional specifications
├── Scripts/         # Build and data generation scripts
├── Tests/           # Unit tests (C++) and Integration tests (WASM/JS)
└── References/      # Theoretical papers (PoI Theory, PKGF Axioms, etc.)
```

---

## **5. Verification Stages**

The system's validity is verified through four distinct experimental stages:

-   **Stage 1: Distance Sensitivity**: Verifying K-field response to objects moving apart.
-   **Stage 2: Rotation Invariance**: Testing CDU's stability during structural rotation.
-   **Stage 3: Multi-node Complexity**: Validating PKGF stability with intersecting structures (Cross-move).
-   **Stage 4: Real-world Synthesis**: Integration test using shaded spheres to simulate real OCR-to-SLAM pipelines.

---

## **6. Building and Running**

### **Prerequisites**
- macOS (for App) or Node.js/Emscripten (for Web/Tests)
- clang++ (C++17), swiftc, metal

### **macOS Application**
```bash
./Scripts/build_macos.sh
./build_macos/PoISLAMApp
```

### **WebAssembly (Web Implementation)**
```bash
emcc Core/poi.cpp -O3 -DEMSCRIPTEN \
  -s INITIAL_MEMORY=268435456 \
  -s ALLOW_MEMORY_GROWTH=1 \
  -s EXPORTED_FUNCTIONS='["_process_frame","_poi_get_dim","_poi_get_n_nodes","_poi_get_A","_poi_get_K","_poi_get_Omega","_poi_get_nodes_x","_poi_get_nodes_y","_poi_get_K_sig","_malloc","_free"]' \
  -s EXPORTED_RUNTIME_METHODS='["cwrap","HEAPU8","HEAPF32"]' \
  -o Web/poi.js
```

### **Running Tests**
```bash
./Scripts/run_tests.sh
cd Web && npm test
```

---

## **7. Conclusion**

PoI-SLAM demonstrates that monocular SLAM can be achieved through the dynamics of structural fields. By shifting the paradigm from "computation" to "geometric dynamics," this research paves the way for substrate-invariant intelligent systems.

---

## **8. Demonstration**

Official online demonstration: [https://itb.co.jp/slam/](https://itb.co.jp/slam/)

### **Local Reproduction**
If the online site is inaccessible, you can run the WebAssembly demo locally using the pre-built files in the `Web/` directory:
1. Navigate to the `Web/` directory: `cd Web`
2. Start a local HTTP server (e.g., using Python):
   ```bash
   python3 -m http.server 8000
   ```
3. Open your browser and navigate to `http://localhost:8000`.

---

## **References**

[1] N. Otsu, "A Threshold Selection Method from Gray-Level Histograms," *IEEE Transactions on Systems, Man, and Cybernetics*, vol. 9, no. 1, pp. 62-66, 1979.

[2] T. Y. Zhang and C. Y. Suen, "A fast parallel algorithm for thinning digital patterns," *Communications of the ACM*, vol. 27, no. 3, pp. 236-239, 1984.

[3] J. Seo et al., "GaussianFlow SLAM: Monocular Gaussian Splatting SLAM Guided by GaussianFlow," *IEEE Robotics and Automation Letters*, vol. 11, no. 4, pp. 1-8, 2026.

[4] W. Guan et al., "Beyond Endpoints: Path-Centric Reasoning for Vectorized Off-Road Network Extraction," *arXiv preprint arXiv:2512.10416v3*, 2026.

[5] "Topology Extraction Research for Long-term Mapping Consistency," *Technical Report*, 2024.

[6] "Geometric Utility in Substrate-Invariant Intelligence," *arXiv preprint arXiv:2604.08718*, 2026.

[7] R. Mur-Artal et al., "ORB-SLAM: A Versatile and Accurate Monocular SLAM System," *IEEE Transactions on Robotics*, vol. 31, no. 5, pp. 1147-1163, 2015.

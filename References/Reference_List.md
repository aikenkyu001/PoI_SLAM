# PoI-SLAM: Comprehensive Reference List & Technical Summaries

This document provides an annotated bibliography of the core theoretical and algorithmic foundations of the PoI-SLAM (Structural Field-Based Monocular SLAM) project.

---

## 1. Fundamental Algorithms (OCR & Topology Preprocessing)

### [Otsu, 1979] A Threshold Selection Method from Gray-Level Histograms
- **Summary**: A seminal paper on automatic image thresholding. It maximizes "between-class variance" to find the optimal global threshold for binarization.
- **Role in PoI-SLAM**: Implemented in `Core/poi.cpp` (`otsu_threshold`). It provides the stable binary masks required for subsequent structural extraction, ensuring robustness against global illumination changes (Stage 4 verification).

### [Zhang & Suen, 1984] A Fast Parallel Algorithm for Thinning Digital Patterns
- **Summary**: A classic parallel algorithm for skeletonizing binary images. It uses two sub-iterations with specific topological conditions to preserve connectivity and reach single-pixel thickness.
- **Role in PoI-SLAM**: The backbone of the `skeletonize` function in `Core/poi.cpp`. It transforms binary "blobs" into abstract skeletons, which are then converted into graph nodes (END, LINE, BRANCH, CROSS).

### [Chen & Wang, 2012] An Improved Zhang-Suen Thinning Algorithm
- **Summary**: Addresses specific artifacts in the original 1984 algorithm, such as skeleton fractures and 2x2 redundant blocks, by introducing refined local neighborhood checks.
- **Role in PoI-SLAM**: Serves as the optimization target for the next development phase (Roadmap) to enhance the stability of node classification in complex "Cross-move" scenarios (Stage 3).

---

## 2. Advanced Structural Reasoning (2024-2026)

### [MaGTopoNet / WildRoad, 2026] Path-Centric Reasoning for Vectorized Network Extraction
- **Summary**: Proposes a shift from "node-centric" to "path-centric" reasoning. It uses a Mask-aware Geodesic Road network extractor (MaGRoad) to aggregate evidence along the entire geodesic path, significantly improving robustness in off-road/unstructured environments.
- **Role in PoI-SLAM**: Validates the PoI approach of treating structure as a "field" of relationships (K-field) rather than isolated points. The geodesic path logic aligns with the project's internal graph geometry (D-matrix).

### [Topology Extraction Research, 2024] New Frontiers in Vectorized Mapping
- **Summary**: Explores the use of structural histograms and topological signatures for long-term consistency in dynamic maps.
- **Role in PoI-SLAM**: Informs the design of the `LocalSig` (Local Structural Histogram) in `Core/poi.cpp` used for node ordering stability in the Canonical Decomposition Unit (CDU).

---

## 3. SLAM Frameworks & Flow Dynamics

### [GaussianFlow SLAM, 2026] Monocular Gaussian Splatting SLAM Guided by GaussianFlow
- **Summary**: Integrates 3D Gaussian Splatting (3DGS) with optical flow supervision. It uses "GaussianFlow" to provide closed-form analytic gradients for both tracking and mapping, achieving photorealistic results with geometric consistency.
- **Role in PoI-SLAM**: Provides a high-fidelity rendering bridge. While PoI-SLAM focuses on abstract structural fields, GaussianFlow demonstrates how "flow" (similar to PKGF) can drive the optimization of a shared global map.

### [Mur-Artal, 2015] ORB-SLAM: A Versatile and Accurate Monocular SLAM System
- **Summary**: The industry standard for feature-based SLAM, utilizing ORB features, descriptors, and RANSAC-based non-linear optimization.
- **Role in PoI-SLAM**: Primary comparison baseline. PoI-SLAM aims to achieve similar or better robustness in unstructured environments *without* the high computational cost of ORB feature matching, relying instead on K-field dynamics.

---

## 4. Theoretical Foundations (PoI Theory)

### [arXiv:2604.08718] Geometric Utility in Substrate-Invariant Intelligence
- **Summary**: Formalizes the concept of "Geometric Utility" and how intelligent systems can be described as physical flows across structural fields.
- **Role in PoI-SLAM**: Provides the axiomatic basis for the Parallel Key Geometric Flow (PKGF) implemented in the C++ core.

---
*Document maintained by PoI-SLAM Scientific Team.*

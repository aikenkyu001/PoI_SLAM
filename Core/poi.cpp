// ============================================================
//  PoI C++ / WASM Core
//  (PoI-OCR → Graph → A/K/Ω → Physics → SLAM)
// ============================================================

#ifdef EMSCRIPTEN
#include <emscripten.h>
#else
#define EMSCRIPTEN_KEEPALIVE
#endif
#include <stdint.h>
#include <stdio.h>
#include <vector>
#include <queue>
#include <cmath>
#include <algorithm>

// ---------------------------
// Structures
// ---------------------------
struct Node {
    int x, y;
    int type; // 0: END, 1: LINE, 2: BRANCH, 3: CROSS
};

struct CanonicalOrder {
    std::vector<int> order;
    std::vector<Node> nodes_rot;
};

struct LocalSig {
    double r;
    double th;
    float h0, h1, h2; // 近傍距離ヒストグラム
    int idx;
};

static void compute_local_signatures(
    const std::vector<Node>& nodes,
    const std::vector<float>& D,
    int n,
    std::vector<LocalSig>& sigs
) {
    sigs.resize(n);
    for (int i = 0; i < n; ++i) {
        float h0 = 0, h1 = 0, h2 = 0;
        for (int j = 0; j < n; ++j) {
            if (i == j) continue;
            float d = D[i*n + j];
            if (!std::isfinite(d)) continue;
            if (d < 2.0f) h0 += 1.0f;
            else if (d < 5.0f) h1 += 1.0f;
            else h2 += 1.0f;
        }
        sigs[i].h0 = h0;
        sigs[i].h1 = h1;
        sigs[i].h2 = h2;
        sigs[i].idx = i;
    }
}

struct Edge {
    int a, b;
};

struct Pose {
    float x, y, z;
    float yaw, pitch, roll;
};

struct Voxel {
    float value;
};

// ---------------------------
// Global PoI State / Buffers
// ---------------------------
static Pose current_pose = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
static std::vector<Voxel> world_voxels;
static const int VOX_W = 128;
static const int VOX_H = 128;
static const int VOX_D = 64;

// JavaScript から参照するためのグローバル行列バッファ
static std::vector<float> g_A;
static std::vector<float> g_K;
static std::vector<float> g_Omega;
static std::vector<float> K_prev;
static std::vector<float> g_nodes_x;
static std::vector<float> g_nodes_y;
static int g_dim = 0;
static int g_n_nodes = 0;

// Experiment / History State
static std::vector<float> g_K_sig;
static std::vector<Pose> pose_history;
static std::vector<std::vector<float>> sig_history;
static bool first_frame = true;
static const int K_DIM_MAX = 64; // PoI 標準の場次元

// ============================================================
//  PoI-OCR / Graph Functions
// ============================================================

static void to_grayscale(const uint8_t* rgba, int w, int h, std::vector<uint8_t>& gray) {
    gray.resize(w * h);
    for (int i = 0; i < w * h; ++i) {
        int r = rgba[4*i + 0];
        int g = rgba[4*i + 1];
        int b = rgba[4*i + 2];
        gray[i] = static_cast<uint8_t>(0.299*r + 0.587*g + 0.114*b);
    }
}

static int otsu_threshold(const std::vector<uint8_t>& gray) {
    int hist[256] = {0};
    for (uint8_t v : gray) hist[v]++;
    int total = gray.size();
    double sum = 0;
    for (int i = 0; i < 256; i++) sum += (double)i * hist[i];
    double sumB = 0;
    int wB = 0, wF = 0;
    double maxVar = 0;
    int threshold = 0;
    for (int t = 0; t < 256; t++) {
        wB += hist[t];
        if (wB == 0) continue;
        wF = total - wB;
        if (wF == 0) break;
        sumB += (double)t * hist[t];
        double mB = sumB / wB;
        double mF = (sum - sumB) / wF;
        double varBetween = (double)wB * (double)wF * (mB - mF) * (mB - mF);
        if (varBetween >= maxVar) {
            maxVar = varBetween;
            threshold = t;
        }
    }
    return threshold;
}

static void threshold_otsu(const std::vector<uint8_t>& gray, int w, int h, std::vector<uint8_t>& bin) {
    int th = otsu_threshold(gray);
    bin.resize(w*h);
    for (int i = 0; i < w*h; i++) bin[i] = (gray[i] < th) ? 1 : 0;
}

static void skeletonize(const std::vector<uint8_t>& bin, int w, int h, std::vector<uint8_t>& skel) {
    skel = bin;
    bool changed = true;
    auto idx = [w](int x, int y){ return y*w + x; };
    auto neighbors = [&](int x, int y, uint8_t* p){
        p[1] = skel[idx(x,y)]; p[2] = skel[idx(x,y-1)]; p[3] = skel[idx(x+1,y-1)];
        p[4] = skel[idx(x+1,y)]; p[5] = skel[idx(x+1,y+1)]; p[6] = skel[idx(x,y+1)];
        p[7] = skel[idx(x-1,y+1)]; p[8] = skel[idx(x-1,y)]; p[9] = skel[idx(x-1,y-1)];
    };
    while (changed) {
        changed = false;
        std::vector<uint8_t> to_remove(w*h, 0);
        for (int step = 1; step <= 2; ++step) {
            for (int y = 1; y < h-1; ++y) {
                for (int x = 1; x < w-1; ++x) {
                    if (skel[idx(x,y)] == 0) continue;
                    uint8_t p[10]; neighbors(x,y,p);
                    int A = 0;
                    for (int k = 2; k <= 9; ++k) {
                        int k2 = (k == 9) ? 2 : k+1;
                        if (p[k] == 0 && p[k2] == 1) A++;
                    }
                    int B = 0;
                    for (int k = 2; k <= 9; ++k) B += p[k];
                    if (B < 2 || B > 6 || A != 1) continue;
                    if (step == 1) {
                        if (p[2]*p[4]*p[6] != 0 || p[4]*p[6]*p[8] != 0) continue;
                    } else {
                        if (p[2]*p[4]*p[8] != 0 || p[2]*p[6]*p[8] != 0) continue;
                    }
                    to_remove[idx(x,y)] = 1;
                }
            }
            for (int i = 0; i < w*h; ++i) if (to_remove[i]) { skel[i] = 0; changed = true; }
            to_remove.assign(w*h, 0);
        }
    }
}

static int classify_node(const std::vector<uint8_t>& skel, int w, int h, int x, int y) {
    // Node classification based on local connectivity (Topology Analysis)
    // 0: END (Terminal node, degree 1)
    // 1: LINE (Continuation, degree 2)
    // 2: BRANCH (Bifurcation, degree 3)
    // 3: CROSS (Intersection, degree >= 4)
    int count = 0;
    for (int dy = -1; dy <= 1; ++dy) {
        for (int dx = -1; dx <= 1; ++dx) {
            if (dx == 0 && dy == 0) continue;
            int nx = x + dx, ny = y + dy;
            if (nx >= 0 && nx < w && ny >= 0 && ny < h && skel[ny*w + nx] != 0) count++;
        }
    }
    return (count == 1) ? 0 : (count == 2) ? 1 : (count == 3) ? 2 : 3;
}

static void extract_nodes(const std::vector<uint8_t>& skel, int w, int h,
                          std::vector<Node>& nodes, std::vector<int>& index_map) {
    nodes.clear(); index_map.assign(w*h, -1);
    int idx = 0;
    // MAX_NODES_LIMIT serves as a computational bottleneck control.
    // In PoI theory, the world is discretized into "islands of structure".
    const int MAX_NODES_LIMIT = 512; 

    for (int y = 1; y < h-1; ++y) {
        for (int x = 1; x < w-1; ++x) {
            if (skel[y*w + x] == 0) continue;
            int t = classify_node(skel, w, h, x, y);
            
            // Priority given to structural junction points (t >= 2).
            if (t >= 2 || (nodes.size() < MAX_NODES_LIMIT)) {
                nodes.push_back(Node{x, y, t});
                index_map[y*w + x] = idx++;
            }
            if (nodes.size() >= MAX_NODES_LIMIT) break;
        }
        if (nodes.size() >= MAX_NODES_LIMIT) break;
    }
}

static void build_edges(const std::vector<uint8_t>& skel, int w, int h,
                        const std::vector<Node>& nodes, const std::vector<int>& index_map,
                        std::vector<Edge>& edges) {
    edges.clear();
    int n = nodes.size();
    for (int i = 0; i < n; ++i) {
        int x0 = nodes[i].x, y0 = nodes[i].y;
        std::vector<int> visited(w*h, 0);
        std::queue<std::pair<int,int>> q;
        q.push({x0,y0}); visited[y0*w + x0] = 1;
        while (!q.empty()) {
            auto [cx, cy] = q.front(); q.pop();
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    if (dx == 0 && dy == 0) continue;
                    int nx = cx + dx, ny = cy + dy;
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h && skel[ny*w + nx] != 0 && !visited[ny*w + nx]) {
                        visited[ny*w + nx] = 1;
                        int j = index_map[ny*w + nx];
                        if (j >= 0 && j != i) { if (i < j) edges.push_back(Edge{i,j}); }
                        else q.push({nx,ny});
                    }
                }
            }
        }
    }
}

static void graph_distances(int n, const std::vector<Edge>& edges, std::vector<float>& D) {
    D.assign(n*n, INFINITY);
    std::vector<std::vector<int>> graph(n);
    for (auto& e : edges) { graph[e.a].push_back(e.b); graph[e.b].push_back(e.a); }
    for (int i = 0; i < n; ++i) {
        D[i*n + i] = 0.0f;
        std::queue<int> q; q.push(i);
        std::vector<int> visited(n, 0); visited[i] = 1;
        while (!q.empty()) {
            int cur = q.front(); q.pop();
            float dcur = D[i*n + cur];
            for (int nxt : graph[cur]) {
                if (!visited[nxt]) { visited[nxt] = 1; D[i*n + nxt] = dcur + 1.0f; q.push(nxt); }
            }
        }
    }
}

static void augment_with_cluster_centroid_distances(std::vector<float>& D, const std::vector<Node>& nodes, const std::vector<Edge>& edges) {
    int n = static_cast<int>(nodes.size());
    if (n == 0) return;

    std::vector<std::vector<int>> adj(n);
    for (auto& e : edges) {
        adj[e.a].push_back(e.b);
        adj[e.b].push_back(e.a);
    }

    std::vector<int> comp_id(n, -1);
    int comp_count = 0;
    for (int i = 0; i < n; ++i) {
        if (comp_id[i] != -1) continue;
        std::queue<int> q;
        q.push(i);
        comp_id[i] = comp_count;
        while (!q.empty()) {
            int v = q.front(); q.pop();
            for (int u : adj[v]) {
                if (comp_id[u] == -1) {
                    comp_id[u] = comp_count;
                    q.push(u);
                }
            }
        }
        ++comp_count;
    }

    if (comp_count <= 1) return;

    struct Centroid { double sx = 0, sy = 0; int count = 0; };
    std::vector<Centroid> centroids(comp_count);
    for (int i = 0; i < n; ++i) {
        int cid = comp_id[i];
        centroids[cid].sx += nodes[i].x;
        centroids[cid].sy += nodes[i].y;
        centroids[cid].count++;
    }

    std::vector<std::pair<double, double>> centers(comp_count);
    for (int c = 0; c < comp_count; ++c) {
        centers[c] = { centroids[c].sx / centroids[c].count, centroids[c].sy / centroids[c].count };
    }

    for (int i = 0; i < n; ++i) {
        int ci = comp_id[i];
        for (int j = 0; j < n; ++j) {
            int cj = comp_id[j];
            if (ci == cj) continue;
            if (std::isinf(D[i * n + j])) {
                double dx = centers[ci].first - centers[cj].first;
                double dy = centers[ci].second - centers[cj].second;
                D[i * n + j] = static_cast<float>(std::sqrt(dx * dx + dy * dy));
            }
        }
    }
}

static CanonicalOrder canonicalize_nodes(const std::vector<Node>& nodes, const std::vector<float>& D) {
    CanonicalOrder result;
    int n = (int)nodes.size();
    if (n == 0) return result;

    std::vector<double> xs(n), ys(n);
    double mx = 0.0, my = 0.0;
    for (int i = 0; i < n; ++i) {
        xs[i] = (double)nodes[i].x;
        ys[i] = (double)nodes[i].y;
        mx += xs[i]; my += ys[i];
    }
    mx /= n; my /= n;
    for (int i = 0; i < n; ++i) { xs[i] -= mx; ys[i] -= my; }

    double sxx = 0.0, syy = 0.0, sxy = 0.0;
    for (int i = 0; i < n; ++i) {
        sxx += xs[i] * xs[i]; syy += ys[i] * ys[i]; sxy += xs[i] * ys[i];
    }
    sxx /= n; syy /= n; sxy /= n;

    double tr = sxx + syy;
    double det = sxx * syy - sxy * sxy;
    double tmp = std::sqrt(std::max(0.0, tr*tr*0.25 - det));
    double lambda1 = tr * 0.5 + tmp;

    double vx = 1.0, vy = 0.0;
    if (std::abs(sxy) > 1e-12 || std::abs(sxx - lambda1) > 1e-12) {
        vx = sxy; vy = lambda1 - sxx;
        double norm = std::sqrt(vx*vx + vy*vy);
        if (norm > 1e-12) { vx /= norm; vy /= norm; }
        else { vx = 1.0; vy = 0.0; }
    }

    double angle = std::atan2(vy, vx);
    double ca = std::cos(-angle);
    double sa = std::sin(-angle);

    // --- 局所構造シグネチャの計算 ---
    std::vector<LocalSig> sigs;
    compute_local_signatures(nodes, D, n, sigs);

    struct Key { int idx; double r, th; float h0, h1, h2; };
    std::vector<Key> keys(n);
    for (int i = 0; i < n; ++i) {
        double rx = ca * xs[i] - sa * ys[i];
        double ry = sa * xs[i] + ca * ys[i];
        keys[i] = { 
            i, 
            std::sqrt(rx*rx + ry*ry), 
            std::atan2(ry, rx),
            sigs[i].h0,
            sigs[i].h1,
            sigs[i].h2
        };
    }

    std::sort(keys.begin(), keys.end(), [](const Key& a, const Key& b){
        if (a.r < b.r - 1e-6) return true;
        if (a.r > b.r + 1e-6) return false;
        // 局所構造の類似度で安定化
        if (a.h0 < b.h0 - 1e-3) return true;
        if (a.h0 > b.h0 + 1e-3) return false;
        if (a.h1 < b.h1 - 1e-3) return true;
        if (a.h1 > b.h1 + 1e-3) return false;
        if (a.h2 < b.h2 - 1e-3) return true;
        if (a.h2 > b.h2 + 1e-3) return false;
        return a.th < b.th;
    });

    result.order.resize(n);
    for (int i = 0; i < n; ++i) result.order[i] = keys[i].idx;
    return result;
}

static void reorder_D(std::vector<float>& D, int n, const std::vector<int>& order) {
    std::vector<float> D_new(n * n);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            D_new[i*n + j] = D[order[i]*n + order[j]];
        }
    }
    D.swap(D_new);
}

static void reorder_nodes(std::vector<Node>& nodes, const std::vector<int>& order) {
    std::vector<Node> tmp(nodes.size());
    for (int i = 0; i < (int)nodes.size(); ++i) tmp[i] = nodes[order[i]];
    nodes.swap(tmp);
}

// ============================================================
//  PoI Matrix / Physics / SLAM Functions
// ============================================================

static void build_A_field(const std::vector<Node>& nodes, const std::vector<float>& D, int n, std::vector<float>& A) {
    A.assign(n * 8, 0.0f);
    std::vector<int> deg(n, 0);
    int max_deg = 1;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) if (std::isfinite(D[i*n + j]) && i != j) deg[i]++;
        if (deg[i] > max_deg) max_deg = deg[i];
    }

    // 簡易クラスタサイズ（距離 < 3 のノード数）
    std::vector<float> local_cluster(n, 0.0f);
    for (int i = 0; i < n; ++i) {
        float cnt = 0.0f;
        for (int j = 0; j < n; ++j) {
            if (i == j) continue;
            float d = D[i*n + j];
            if (std::isfinite(d) && d < 3.0f) cnt += 1.0f;
        }
        local_cluster[i] = cnt;
    }

    float max_cluster = 1.0f;
    for (float v : local_cluster) if (v > max_cluster) max_cluster = v;

    for (int i = 0; i < n; i++) {
        A[i*8 + 0] = float(deg[i]) / float(max_deg);

        float sum = 0; int cnt = 0;
        for (int j = 0; j < n; j++) if (std::isfinite(D[i*n + j])) { sum += D[i*n + j]; cnt++; }
        A[i*8 + 1] = (cnt > 0) ? (sum / cnt) : 0.0f;

        int t = nodes[i].type;
        if (t >= 0 && t < 4) A[i*8 + (2 + t)] = 1.0f;

        // 追加: 局所クラスタサイズ（正規化）
        A[i*8 + 6] = local_cluster[i] / max_cluster;
    }
}

static void build_K_field(const std::vector<float>& D, int n, int dim, std::vector<float>& K) {
    K.assign(dim * dim, 0.0f);
    float max_finite = 0.1f;
    for (float v : D) if (std::isfinite(v) && v > max_finite) max_finite = v;
    const float sigma = 20.0f;
    int m = std::min(n, dim);
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < m; j++) {
            float d = std::isfinite(D[i*n + j]) ? D[i*n + j] : (max_finite + 1.0f);
            K[i*dim + j] = std::exp(-d / sigma);
        }
    }
    for (int i = 0; i < m; i++) {
        for (int j = i+1; j < m; j++) {
            float v = 0.5f * (K[i*dim + j] + K[j*dim + i]);
            K[i*dim + j] = K[j*dim + i] = v;
        }
    }
}

static void build_Omega(const std::vector<float>& A, int n, int dim, std::vector<float>& Omega) {
    Omega.assign(dim * dim, 0.0f);
    int m = std::min(n, dim);
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < m; j++) Omega[i*dim + j] = A[i*8 + (j % 8)];
    }
    float tr = 0.0f;
    for (int i = 0; i < dim; i++) tr += std::abs(Omega[i*dim + i]);
    if (tr > 1e-9f) for (float& v : Omega) v /= tr;
}

static void PKGF_update(const std::vector<float>& K, const std::vector<float>& Omega, int dim, float eta, std::vector<float>& K_next) {
    K_next.assign(dim * dim, 0.0f);
    for (int i = 0; i < dim * dim; i++) K_next[i] = K[i] + eta * (Omega[i] - K[i]);
}

static void normalize_K(std::vector<float>& K, int dim) {
    float norm = 0.0f;
    for (float v : K) norm += v*v;
    norm = std::sqrt(norm);
    if (norm > 1e-9f) for (float& v : K) v /= norm;
}

static void compute_K_signature(const std::vector<float>& K, int dim, std::vector<float>& sig) {
    sig.assign(4, 0.0f);
    float diag_sum = 0.0f;
    float upper_energy = 0.0f;
    float row0_energy = 0.0f;
    float row1_energy = 0.0f;

    for (int i = 0; i < dim; ++i) {
        diag_sum += K[i*dim + i];
        for (int j = i+1; j < dim; ++j) {
            float v = K[i*dim + j];
            upper_energy += v * v;
        }
    }
    for (int j = 0; j < dim; ++j) {
        float v0 = K[0*dim + j];
        float v1 = K[1*dim + j];
        row0_energy += v0 * v0;
        row1_energy += v1 * v1;
    }

    sig[0] = diag_sum;
    sig[1] = upper_energy;
    sig[2] = row0_energy;
    sig[3] = row1_energy;
}

static int find_loop_candidate(const std::vector<float>& sig,
                               const std::vector<std::vector<float>>& history,
                               float thresh, int min_gap) {
    int T = (int)history.size();
    if (T == 0) return -1;
    int best_idx = -1;
    float best_dist = 1e9f;
    for (int t = 0; t < T - min_gap; ++t) {
        const auto& s = history[t];
        if (s.size() != sig.size()) continue;
        float d = 0.0f;
        for (int k = 0; k < (int)sig.size(); ++k) {
            float diff = sig[k] - s[k];
            d += diff * diff;
        }
        d = std::sqrt(d);
        if (d < best_dist) {
            best_dist = d;
            best_idx = t;
        }
    }
    if (best_dist < thresh) return best_idx;
    return -1;
}

static void estimate_camera_motion_2d_modes(const std::vector<float>& K1,
                                            const std::vector<float>& K2,
                                            int dim,
                                            float& dx,
                                            float& dy) {
    // 対角成分の変化をモードとして扱う
    float sum_pos = 0.0f;
    float sum_neg = 0.0f;
    for (int i = 0; i < dim; ++i) {
        float d = K2[i*dim + i] - K1[i*dim + i];
        if (d > 0) sum_pos += d;
        else sum_neg += d;
    }

    // 前進/後退っぽさと、左右の揺れを分ける
    float forward = sum_pos + sum_neg;      // 全体の収縮/拡大
    float lateral = sum_pos - sum_neg;      // モードの偏り

    dx = 0.002f * forward;
    dy = 0.002f * lateral;
}

static void fuse_structure_fields(std::vector<Voxel>& vox, int W, int H, int D,
                                  const std::vector<Node>& nodes,
                                  const Pose& pose,
                                  float weight,
                                  float decay) {
    if (vox.empty()) vox.assign(W*H*D, {0.0f});

    // 全体に減衰をかける（観測されない構造は少しずつ弱くなる）
    int N = W*H*D;
    for (int i = 0; i < N; ++i) {
        vox[i].value *= (1.0f - decay);
    }

    for (auto& nd : nodes) {
        // 重要度の低いエンドポイント(0)はノイズの可能性が高いため地図には入れない
        if (nd.type < 1) continue;

        int xi = (int)((pose.x + nd.x * 0.01f) * W);
        int yi = (int)((pose.y + nd.y * 0.01f) * H);
        int zi = (int)(pose.z * D);
        if (xi >= 0 && xi < W && yi >= 0 && yi < H && zi >= 0 && zi < D) {
            int idx = zi*W*H + yi*W + xi;
            // 蓄積しきい値を上げ、持続的な構造のみを残す
            vox[idx].value = vox[idx].value * (1.0f - weight) + weight * 1.0f;
        }
    }
}

// ============================================================
//  WASM Entry Point & API
// ============================================================

extern "C" {

EMSCRIPTEN_KEEPALIVE
void process_frame(uint8_t* rgba, int w, int h) {
    std::vector<uint8_t> gray, bin, skel;
    std::vector<Node> nodes;
    std::vector<int> index_map;
    std::vector<Edge> edges;
    std::vector<float> D;

    // PoI-OCR & Graph
    to_grayscale(rgba, w, h, gray);

    // 自然画像ノイズ対策: 2次元空間平滑化 (3x3 平均)
    std::vector<uint8_t> smooth = gray;
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            int sum = 0;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    sum += gray[(y + dy) * w + (x + dx)];
                }
            }
            smooth[y * w + x] = static_cast<uint8_t>(sum / 9);
        }
    }

    threshold_otsu(smooth, w, h, bin);
    skeletonize(bin, w, h, skel);
    extract_nodes(skel, w, h, nodes, index_map);
    build_edges(skel, w, h, nodes, index_map, edges);
    graph_distances((int)nodes.size(), edges, D);
    augment_with_cluster_centroid_distances(D, nodes, edges);

    // ---- Canonicalization ----
    CanonicalOrder canon = canonicalize_nodes(nodes, D);
    reorder_D(D, (int)nodes.size(), canon.order);
    reorder_nodes(nodes, canon.order);

    // ---- PoI Matrix & Physics ----
    g_n_nodes = (int)nodes.size();
    if (g_n_nodes == 0) {
        g_A.clear(); g_K.clear(); g_Omega.clear(); g_dim = 0;
        return;
    }

    g_dim = std::min(g_n_nodes, K_DIM_MAX);

    build_A_field(nodes, D, g_n_nodes, g_A);
    build_K_field(D, g_n_nodes, g_dim, g_K);
    build_Omega(g_A, g_n_nodes, g_dim, g_Omega);

    // ---- PKGF & SLAM (フレーム間状態更新) ----
    if (K_prev.empty()) {
        K_prev.assign(g_dim * g_dim, 0.0f);
        for(int i=0; i<g_dim; i++) K_prev[i*g_dim+i] = 1.0f;
        current_pose = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f}; 
    }

    if (K_prev.size() == (size_t)(g_dim * g_dim)) {
        std::vector<float> K_next;
        PKGF_update(K_prev, g_Omega, g_dim, 0.1f, K_next); // 学習率を上げ、慣性を高める
        normalize_K(K_next, g_dim);

        // --- K のシグネチャを計算 ---
        compute_K_signature(K_next, g_dim, g_K_sig);
        if (!g_K_sig.empty()) {
            sig_history.push_back(g_K_sig);
            pose_history.push_back(current_pose);
        }

        if (!first_frame) {
            float dx=0, dy=0;
            estimate_camera_motion_2d_modes(K_prev, K_next, g_dim, dx, dy);
            current_pose.x += dx;
            current_pose.y += dy;
        }

        // 減衰付きの融合: 時間とともに安定構造だけが残る
        fuse_structure_fields(world_voxels, VOX_W, VOX_H, VOX_D, nodes, current_pose, 0.1f, 0.01f);

        // ループ候補検出
        if (sig_history.size() > 20) {
            int loop_idx = find_loop_candidate(g_K_sig, sig_history, 0.05f, 10);
            if (loop_idx >= 0) {
                printf("Loop candidate: now=%d, back=%d\n", (int)sig_history.size()-1, loop_idx);
            }
        }

        K_prev = K_next;
        first_frame = false;
    } else {
        K_prev = g_K;
    }

    // Export normalized node coordinates for renderer
    g_nodes_x.assign(g_n_nodes, 0.0f);
    g_nodes_y.assign(g_n_nodes, 0.0f);
    for(int i=0; i<g_n_nodes; i++) {
        // ピクセル中心 (+0.5) を考慮して正確に -1.0 〜 1.0 にマップ
        g_nodes_x[i] = ((float)nodes[i].x + 0.5f) / (float)w * 2.0f - 1.0f;
        g_nodes_y[i] = 1.0f - ((float)nodes[i].y + 0.5f) / (float)h * 2.0f;
    }
}

// ---- Native/JS Getter API ----

EMSCRIPTEN_KEEPALIVE
int poi_get_dim() {
    return g_dim;
}

EMSCRIPTEN_KEEPALIVE
int poi_get_n_nodes() {
    return g_n_nodes;
}

EMSCRIPTEN_KEEPALIVE
float* poi_get_A() {
    return g_A.empty() ? nullptr : g_A.data();
}

EMSCRIPTEN_KEEPALIVE
float* poi_get_K() {
    return K_prev.empty() ? nullptr : K_prev.data();
}

EMSCRIPTEN_KEEPALIVE
float* poi_get_Omega() {
    return g_Omega.empty() ? nullptr : g_Omega.data();
}

EMSCRIPTEN_KEEPALIVE
float* poi_get_K_sig() {
    return g_K_sig.empty() ? nullptr : g_K_sig.data();
}

EMSCRIPTEN_KEEPALIVE
float* poi_get_nodes_x() {
    return g_nodes_x.empty() ? nullptr : g_nodes_x.data();
}

EMSCRIPTEN_KEEPALIVE
float* poi_get_nodes_y() {
    return g_nodes_y.empty() ? nullptr : g_nodes_y.data();
}

EMSCRIPTEN_KEEPALIVE
float* poi_get_world_voxels() {
    return world_voxels.empty() ? nullptr : (float*)world_voxels.data();
}

EMSCRIPTEN_KEEPALIVE
float poi_get_world_voxels_max() {
    if (world_voxels.empty()) return 0.0f;
    float m = 0.0f;
    for (const auto& v : world_voxels) {
        if (v.value > m) m = v.value;
    }
    return m;
}

EMSCRIPTEN_KEEPALIVE
float poi_get_pose_x() {
    return current_pose.x;
}

} // extern "C"

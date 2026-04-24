import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from skimage.morphology import skeletonize
from collections import deque, defaultdict
import os

# ============================================
# Font
# ============================================
def load_font(size):
    paths = [
        "ipaexg.ttf",
        "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except:
                pass
    return ImageFont.load_default()

# ============================================
# Render character
# ============================================
def render_char(ch, size=64):
    img = Image.new("L", (size, size), 255)
    draw = ImageDraw.Draw(img)
    font = load_font(int(size * 0.7))

    bbox = draw.textbbox((0, 0), ch, font=font)
    x = (size - (bbox[2] - bbox[0])) // 2
    y = (size - (bbox[3] - bbox[1])) // 2
    draw.text((x, y), ch, fill=0, font=font)

    return np.array(img)

# ============================================
# Preprocess → Skeleton
# ============================================
def preprocess(img):
    _, b = cv2.threshold(img, 0, 1, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return b

def to_skeleton(b):
    return skeletonize(b > 0).astype(np.uint8)

# ============================================
# Node classification
# ============================================
def classify(skel, x, y):
    n = np.sum(skel[y-1:y+2, x-1:x+2]) - 1
    if n == 1:
        return "END"
    elif n == 2:
        return "LINE"
    elif n == 3:
        return "BRANCH"
    else:
        return "CROSS"

# ============================================
# Extract nodes
# ============================================
def extract_nodes(skel):
    h, w = skel.shape
    nodes = []
    index = {}

    for y in range(1, h-1):
        for x in range(1, w-1):
            if skel[y, x] == 0:
                continue
            t = classify(skel, x, y)
            idx = len(nodes)
            nodes.append({"type": t, "pos": (x, y)})
            index[(x, y)] = idx

    return nodes, index

# ============================================
# Build edges
# ============================================
def build_edges(skel, nodes, index):
    edges = set()
    h, w = skel.shape

    for i, n in enumerate(nodes):
        x0, y0 = n["pos"]
        visited = set()
        queue = deque([(x0, y0)])

        while queue:
            cx, cy = queue.popleft()

            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    nx, ny = cx + dx, cy + dy
                    if (nx, ny) == (cx, cy):
                        continue
                    if not (0 <= nx < w and 0 <= ny < h):
                        continue
                    if skel[ny, nx] == 0:
                        continue
                    if (nx, ny) in visited:
                        continue

                    visited.add((nx, ny))

                    if (nx, ny) in index and index[(nx, ny)] != i:
                        j = index[(nx, ny)]
                        edges.add(tuple(sorted((i, j))))
                    else:
                        queue.append((nx, ny))

    return list(edges)

# ============================================
# Graph distances
# ============================================
def graph_distances(nodes, edges):
    n = len(nodes)
    graph = {i: [] for i in range(n)}
    for a, b in edges:
        graph[a].append(b)
        graph[b].append(a)

    D = np.full((n, n), np.inf)
    for i in range(n):
        D[i, i] = 0
        queue = deque([(i, 0)])
        visited = {i}

        while queue:
            cur, d = queue.popleft()
            for nxt in graph[cur]:
                if nxt not in visited:
                    visited.add(nxt)
                    D[i, nxt] = d + 1
                    queue.append((nxt, d + 1))

    return D

# ============================================
# Canonical embedding (rotation invariant)
# ============================================
def canonicalize(nodes):
    pts = np.array([n["pos"] for n in nodes], dtype=float)

    # center
    pts -= pts.mean(axis=0)

    # PCA
    cov = np.cov(pts.T)
    vals, vecs = np.linalg.eigh(cov)
    main_axis = vecs[:, np.argmax(vals)]

    angle = np.arctan2(main_axis[1], main_axis[0])
    rot = np.array([[np.cos(-angle), -np.sin(-angle)],
                    [np.sin(-angle),  np.cos(-angle)]])

    pts = pts @ rot.T

    # sort nodes by (radius, angle)
    r = np.sqrt(pts[:,0]**2 + pts[:,1]**2)
    th = np.arctan2(pts[:,1], pts[:,0])
    order = np.lexsort((th, r))

    return order

# ============================================
# Layer signatures
# ============================================
def node_centrality(D):
    vals = []
    for i in range(len(D)):
        row = D[i]
        finite = row[np.isfinite(row)]
        vals.append(np.mean(finite) if len(finite) else 0)
    return np.array(vals)

def split_layers(types, D):
    c = node_centrality(D)
    if np.max(c) > 0:
        c = c / np.max(c)

    layers = {"core": [], "mid": [], "outer": []}
    for i, v in enumerate(c):
        if v < 0.4:
            layers["core"].append(i)
        elif v < 0.7:
            layers["mid"].append(i)
        else:
            layers["outer"].append(i)
    return layers

def typed_distance_signature(types, D, idxs):
    sig = []
    for i in idxs:
        for j in idxs:
            if i < j and np.isfinite(D[i,j]):
                key = tuple(sorted([types[i], types[j]]))
                sig.append((key, D[i,j]))

    if not sig:
        return []

    dvals = np.array([x[1] for x in sig])
    mean = np.mean(dvals)
    dvals = dvals / mean if mean > 0 else dvals

    return [(sig[i][0], dvals[i]) for i in range(len(sig))]

def layered_signature(types, D):
    layers = split_layers(types, D)
    return {name: typed_distance_signature(types, D, idxs)
            for name, idxs in layers.items()}

# ============================================
# A-field (local feature vectors)
# ============================================
def build_A_field(nodes, D):
    n = len(nodes)
    A = np.zeros((n, 8))

    # degree
    deg = np.sum(np.isfinite(D), axis=1) - 1
    A[:,0] = deg / (np.max(deg)+1e-9)

    # centrality
    cent = node_centrality(D)
    A[:,1] = cent / (np.max(cent)+1e-9)

    # type one-hot
    type_map = {"END":2, "LINE":3, "BRANCH":4, "CROSS":5}
    for i, nd in enumerate(nodes):
        A[i, type_map[nd["type"]]] = 1

    return A

# ============================================
# K-field (structure field)
# ============================================
def build_K_field(D, dim=64, sigma=2.0):
    n = len(D)
    if n == 0:
        return np.eye(dim)

    D_eff = np.array(D, float)
    finite = np.isfinite(D_eff)
    max_finite = np.max(D_eff[finite])
    D_eff[~finite] = max_finite + 1.0

    K_small = np.exp(-D_eff / sigma)
    K_small = 0.5 * (K_small + K_small.T)

    K = np.zeros((dim, dim))
    m = min(dim, n)
    K[:m,:m] = K_small[:m,:m]

    tr = np.trace(K)
    K = K / tr if tr > 1e-12 else np.eye(dim)

    return K

# ============================================
# Ω-field (input field)
# ============================================
def build_Omega(A, dim=64):
    n = len(A)
    Ω = np.zeros((dim, dim))
    m = min(dim, n)
    Ω[:m,:m] = A[:m,:m] if A.shape[1] >= m else A[:m,:].dot(A[:m,:].T)
    tr = np.trace(Ω)
    return Ω / tr if tr > 1e-12 else np.eye(dim)

# ============================================
# Effective dimension (log-spectrum)
# ============================================
def effective_dim(K):
    try:
        s = np.linalg.svd(K, compute_uv=False)
    except:
        return 1.0

    s = np.log1p(s)
    p = s**2 / (np.sum(s**2) + 1e-12)
    return np.exp(-np.sum(p * np.log(p + 1e-12)))

# ============================================
# PoI resonance
# ============================================
def comm(A, B):
    return A @ B - B @ A

# ============================================
# Build full PoI state
# ============================================
def build_state(ch, dim=64):
    img = render_char(ch)
    img = rotate_image(img, 45)

    skel = to_skeleton(preprocess(img))

    nodes, index = extract_nodes(skel)
    if len(nodes) == 0:
        K = np.eye(dim)
        Ω = np.eye(dim)
        return {"K":K, "Ω":Ω, "rank":1.0, "sig":{"core":[], "mid":[], "outer":[]} }

    edges = build_edges(skel, nodes, index)
    D = graph_distances(nodes, edges)
    types = [n["type"] for n in nodes]

    order = canonicalize(nodes)
    D = D[order][:,order]
    nodes = [nodes[i] for i in order]

    sig = layered_signature(types, D)

    A = build_A_field(nodes, D)
    Ω = build_Omega(A, dim)
    K = build_K_field(D, dim)
    K = canonical_K(K)

    rank = effective_dim(K)

    return {"K":K, "Ω":Ω, "rank":rank, "sig":sig}

# ============================================
# Identify
# ============================================
def identify(target, candidates, dim=64):
    s0 = build_state(target, dim)

    results = []
    for c in candidates:
        s = build_state(c, dim)
        topo = compare_layered(s0["sig"], s["sig"])
        poi = poi_resonance(s0, s)
        score = topo * poi
        results.append((c, score))

    return sorted(results, key=lambda x: x[1], reverse=True)

def compare_typed(sig1, sig2):
    def group(sig):
        d = defaultdict(list)
        for k, v in sig:
            d[k].append(v)
        return d

    g1 = group(sig1)
    g2 = group(sig2)

    keys = set(g1) | set(g2)

    score = 0
    count = 0

    for k in keys:
        v1 = np.sort(g1.get(k, []))
        v2 = np.sort(g2.get(k, []))

        m = min(len(v1), len(v2))
        if m == 0:
            continue

        score += np.mean(np.abs(v1[:m] - v2[:m]))
        count += 1

    if count == 0:
        return 0

    return 1 / (1 + score / count)

def compare_layered(s1, s2):
    total = 0
    count = 0

    for layer in ["core", "mid", "outer"]:
        if len(s1[layer]) == 0 or len(s2[layer]) == 0:
            continue

        total += compare_typed(s1[layer], s2[layer])
        count += 1

    if count == 0:
        return 0

    return total / count

def quantize_rank(r, step=0.25):
    # rank を step ごとの離散値に丸める
    return np.round(r / step) * step

def quantize_spectrum(s, step=0.1):
    # 固有値スペクトルを step ごとに量子化
    return np.round(s / step) * step

def poi_resonance(state1, state2,
                  alpha=4.0, beta=2.0,
                  gamma_rank=1.5, gamma_spec=1.0,
                  q_step_rank=0.25, q_step_spec=0.1,
                  lambda_tri=1.0):
    K1, Ω1, r1 = state1["K"], state1["Ω"], state1["rank"]
    K2, Ω2, r2 = state2["K"], state2["Ω"], state2["rank"]

    # --- PoI trace alignment（Ω vs K）---
    trace_align = np.abs(np.trace(Ω1.T @ K2))

    # --- commutator lock（位相ロック）---
    C = K1 @ K2 - K2 @ K1
    denom = np.linalg.norm(K1) + np.linalg.norm(K2) + 1e-9
    lock = np.exp(-alpha * np.linalg.norm(C) / denom)

    # --- Q‑PoI：rank の量子化 ---
    qr1 = quantize_rank(r1, step=q_step_rank)
    qr2 = quantize_rank(r2, step=q_step_rank)
    rank_penalty = np.exp(-beta * abs(qr1 - qr2))

    # --- Higgs（rank 側）---
    higgs_rank1 = np.exp(-gamma_rank * (r1 - qr1)**2)
    higgs_rank2 = np.exp(-gamma_rank * (r2 - qr2)**2)
    higgs_rank = higgs_rank1 * higgs_rank2

    # --- 固有値スペクトルの取得 ---
    try:
        s1 = np.linalg.svd(K1, compute_uv=False)
        s2 = np.linalg.svd(K2, compute_uv=False)
    except np.linalg.LinAlgError:
        s1 = np.ones(1)
        s2 = np.ones(1)

    s1 = s1 / (np.sum(s1) + 1e-12)
    s2 = s2 / (np.sum(s2) + 1e-12)

    # --- Q‑PoI：スペクトルの量子化 ---
    qs1 = quantize_spectrum(s1, step=q_step_spec)
    qs2 = quantize_spectrum(s2, step=q_step_spec)

    spec_diff = np.mean(np.abs(qs1 - qs2))
    spec_penalty = np.exp(-beta * spec_diff)

    # --- Higgs（スペクトル側）---
    higgs_spec1 = np.exp(-gamma_spec * np.mean((s1 - qs1)**2))
    higgs_spec2 = np.exp(-gamma_spec * np.mean((s2 - qs2)**2))
    higgs_spec = higgs_spec1 * higgs_spec2

    higgs_total = higgs_rank * higgs_spec

    # --- 三体相互作用 A×K×Ω（ここでは Ω を A の像として使う）---
    # I = tr(Ω1 K1 Ω2^T K2^T)
    tri_raw = np.trace(Ω1 @ K1 @ Ω2.T @ K2.T)
    # スケールを落として安定化
    tri_norm = np.abs(tri_raw) / (1.0 + np.abs(tri_raw))
    tri_factor = np.exp(lambda_tri * tri_norm)

    return trace_align * lock * rank_penalty * spec_penalty * higgs_total * tri_factor

def canonical_K(K):
    # 固有値分解
    vals, vecs = np.linalg.eigh(K)

    # 固有値を降順に並べ替え
    idx = np.argsort(vals)[::-1]
    vals = vals[idx]
    vecs = vecs[:, idx]

    # 固有ベクトルの符号を固定（最初の非ゼロ成分を正に）
    for i in range(vecs.shape[1]):
        col = vecs[:, i]
        for x in col:
            if abs(x) > 1e-12:
                if x < 0:
                    vecs[:, i] = -vecs[:, i]
                break

    # 正準化された K を返す
    return vecs @ np.diag(vals) @ vecs.T

def rotate_image(img, angle=45):
    h, w = img.shape
    center = (w//2, h//2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_NEAREST, borderValue=255)
    return rotated

# ============================================
# Run
# ============================================
if __name__ == "__main__":
    candidates = ["口","〇","Ⅹ","×","二","＝","工","エ","薔","薇","三","ミ","ハ","八","日","曰","王","玉","主","犬","太","大","鳥","烏","斉","齊","済","辺","邉","邊","返","迫","近","青","清","晴","情","精","祭","察","擦","斎","齋"]

    for target in candidates:
        print("\n==============================")
        print("Target:", target)
        print("==============================")

        # 元の identify と同じく、target も含めて比較
        res = identify(target, candidates)

        for c, s in res:
            print(c, s)

        print("Winner:", res[0])

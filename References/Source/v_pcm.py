import numpy as np
import matplotlib.pyplot as plt
from collections import deque
import os

# ============================================================
#  V‑PCM 研究用究極完全版（ルート出力・ファイル名統一版）
# ============================================================

def save_summary(text):
    with open("summary.txt", "a", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)

def save_raw_data(filename, data, header=""):
    np.savetxt(filename, data, header=header, delimiter=",", fmt="%.6f")

# -----------------------------
# ユーティリティ
# -----------------------------
def orthogonal_matrix(n):
    Q, _ = np.linalg.qr(np.random.randn(n, n))
    return Q

def rank_threshold(mat, eps=1e-3):
    s = np.linalg.svd(mat, compute_uv=False)
    return np.sum(s > eps)

def entropy(phi, eps=1e-8):
    phi = np.abs(phi); phi = np.clip(phi, eps, None); phi /= phi.sum()
    return -np.sum(phi * np.log(phi))

def connected_components_2d(mat, threshold=0.2):
    n = mat.shape[0]; visited = np.zeros_like(mat, dtype=bool); comps = 0
    for i in range(n):
        for j in range(n):
            if abs(mat[i, j]) > threshold and not visited[i, j]:
                comps += 1; q = deque([(i, j)]); visited[i, j] = True
                while q:
                    x, y = q.popleft()
                    for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                        nx, ny = x+dx, y+dy
                        if 0 <= nx < n and 0 <= ny < n:
                            if abs(mat[nx, ny]) > threshold and not visited[nx, ny]:
                                visited[nx, ny] = True; q.append((nx, ny))
    return comps

def cosine_sim(a, b, eps=1e-8):
    na = np.linalg.norm(a) + eps; nb = np.linalg.norm(b) + eps
    return float(np.dot(a, b) / (na * nb))

# -----------------------------
# 光学設計 (Phase 4)
# -----------------------------
def estimate_sigma_from_A(A):
    row = A[len(A)//2]; row = row / row.max(); x = np.arange(len(row)) - len(row)//2
    mask = row > 1e-4
    if not np.any(mask): return 1.0
    x_fit = x[mask]; y_fit = np.log(row[mask])
    A_mat = np.vstack([x_fit**2, np.ones_like(x_fit)]).T
    try:
        a, _ = np.linalg.lstsq(A_mat, y_fit, rcond=None)[0]
        return float(np.sqrt(-1.0 / (2 * a))) if a < 0 else 1.0
    except: return 1.0

# -----------------------------
# V‑PCM クラス
# -----------------------------
class VPCM:
    def __init__(self, n=16, lam=0.05, noise=0.02, t_sb=100):
        self.n = n; self.lam = lam; self.noise = noise
        x = np.arange(n); self.A = np.exp(-(x[:, None] - x[None, :])**2 / (2 * 1.2**2))
        self.A /= self.A.sum(axis=1, keepdims=True)
        self.K_core = np.random.randn(n, n) * 0.5; self.K_fluct = np.random.randn(n, n) * 0.1
        self.K_prev = self.K_core.copy(); self.t = 0; self.t_sb = t_sb
        self.gauge_broken = False; self.H = np.eye(n)

    @property
    def K(self): return self.K_core + 1j * self.K_fluct

    def curvature(self):
        omega = self.K_core.copy(); np.fill_diagonal(omega, 0.0)
        return omega @ omega.T - omega.T @ omega

    def temporal_covariant_derivative(self):
        dK = self.K_core - self.K_prev; omega_t = dK.copy(); np.fill_diagonal(omega_t, 0.0)
        return dK + (omega_t @ self.K_core - self.K_core @ omega_t)

    def apply_dynamic_gauge(self):
        if not self.gauge_broken:
            H = orthogonal_matrix(self.n); self.K_core = H @ self.K_core @ H.T; self.K_fluct = H @ self.K_fluct @ H.T

    def maybe_spontaneous_symmetry_breaking(self):
        if (not self.gauge_broken) and (self.t >= self.t_sb):
            self.gauge_broken = True; _, vecs = np.linalg.eigh(self.K_core); self.H = vecs
            self.K_core = self.H.T @ self.K_core @ self.H; self.K_fluct = self.H.T @ self.K_fluct @ self.H

    def update(self, phi_external=None):
        self.apply_dynamic_gauge(); self.maybe_spontaneous_symmetry_breaking()
        self.K_prev = self.K_core.copy(); K = self.K
        phi = np.tanh(K.real.diagonal()) if phi_external is None else phi_external
        Ω = np.zeros((self.n, self.n))
        for i in range(self.n):
            for j in range(self.n): Ω[i, j] = np.exp(-abs(i-j)/3.0) * np.tanh(phi[i])
        ξ = (self.noise * np.random.randn(self.n, self.n) + 1j * self.noise * np.random.randn(self.n, self.n))
        K_new = self.A @ (K + (Ω @ K - K @ Ω) - self.lam * K + ξ) @ self.A.T
        self.K_core, self.K_fluct = K_new.real, K_new.imag; self.t += 1
        return self.temporal_covariant_derivative()

# -----------------------------
# 統合実験
# -----------------------------
def run_all_experiments():
    save_summary("V‑PCM 究極完全版シミュレーション開始")
    
    # 1. 構造進化 & 幾何学解析
    vpcm = VPCM(t_sb=100)
    history_core, ranks, ents, comps, curv, nabla_t = [], [], [], [], [], []
    steps = 400
    for t in range(steps):
        phi = np.zeros(16); phi[:8] = 1.0 if t < 250 else 0.0
        nt = vpcm.update(phi_external=phi)
        history_core.append(vpcm.K_core.copy())
        ranks.append(rank_threshold(vpcm.K_core))
        ents.append(entropy(vpcm.K_core.diagonal()))
        comps.append(connected_components_2d(vpcm.K_core))
        curv.append(np.linalg.norm(vpcm.curvature()))
        nabla_t.append(np.linalg.norm(nt))

    evolution_data = np.column_stack([np.arange(steps), ranks, ents, comps, curv, nabla_t])
    save_raw_data("evolution_metrics.csv", evolution_data, header="step,rank,entropy,components,curvature,nabla_t")

    plt.figure(figsize=(15, 4))
    for i, idx in enumerate([0, 100, 250, 399]):
        plt.subplot(1, 4, i + 1); plt.imshow(history_core[idx], cmap="coolwarm", vmin=-1, vmax=1)
        plt.title(f"K_core @ t={idx}"); plt.axis("off")
    plt.tight_layout(); plt.savefig("exp1_matrix_evolution.png"); plt.close()

    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    axs[0,0].plot(ranks); axs[0,0].set_title("Rank (U6)")
    axs[0,1].plot(ents); axs[0,1].set_title("Entropy (D4)")
    axs[1,0].plot(comps); axs[1,0].set_title("Components (Topology)")
    axs[1,1].plot(curv); axs[1,1].set_title("Curvature ||F||")
    for ax in axs.flat: ax.axvline(100, color='r', ls='--'); ax.set_xlabel("t")
    plt.tight_layout(); plt.savefig("exp2_metrics.png"); plt.close()

    plt.figure(figsize=(6, 4)); plt.plot(nabla_t); plt.title("Temporal Connection ||∇_t K||"); plt.axvline(100, color='r', ls='--')
    plt.savefig("exp3_geometry_temporal.png"); plt.close()

    # 2. ONP Basin & Similarity
    n_inits = 20; phi_onp = np.zeros(16); phi_onp[:8] = 1.0; finals = []
    for k in range(n_inits):
        v = VPCM(lam=0.04, noise=0.01)
        for t in range(300): v.update(phi_external=phi_onp)
        finals.append(v.K_core.diagonal().copy())
    finals = np.array(finals); sim_mat = np.zeros((n_inits, n_inits))
    for i in range(n_inits):
        for j in range(n_inits): sim_mat[i,j] = cosine_sim(finals[i], finals[j])
    
    save_raw_data("onp_similarity_matrix.csv", sim_mat, header="pattern similarity matrix")
    plt.figure(figsize=(6, 5)); plt.imshow(sim_mat, cmap="viridis", vmin=-1, vmax=1); plt.colorbar(); plt.title("ONP Similarity Matrix")
    plt.savefig("exp4_onp_similarity.png"); plt.close()
    
    clusters = []
    for f in finals:
        assigned = False
        for c in clusters:
            if cosine_sim(f, c[0]) > 0.98: c.append(f); assigned = True; break
        if not assigned: clusters.append([f])
    save_summary(f"実験: ONP 解析結果\n - Attractors: {len(clusters)}\n - Basin Sizes: {[len(c)/n_inits for c in clusters]}")

    # 3. 相図
    lams = np.linspace(0.01, 0.12, 5); noises = np.linspace(0.0, 0.06, 5); res = np.zeros((5, 5))
    for i, l in enumerate(lams):
        for j, n in enumerate(noises):
            v = VPCM(lam=l, noise=n); [v.update() for _ in range(100)]
            res[i,j] = rank_threshold(v.K_core)
    
    save_raw_data("phase_diagram_data.csv", res, header="Phase Diagram: rows=lambda, cols=noise")
    plt.figure(figsize=(6, 5)); plt.imshow(res, origin='lower', extent=[0, 0.06, 0.01, 0.12], aspect='auto')
    plt.title("Phase Diagram (Rank)"); plt.xlabel("noise"); plt.ylabel("lambda"); plt.colorbar()
    plt.savefig("exp5_phase_diagram.png"); plt.close()

    # 4. 光学逆算
    sigma_pix = estimate_sigma_from_A(vpcm.A); f_num = (sigma_pix * 5.0) / (1.5 * 0.55)
    save_summary(f"\n最終光学設計パラメータ:\n - 推定 PSF sigma: {sigma_pix:.3f} px\n - 推奨レンズ F値: {f_num:.2f}\n - 散逸係数 lambda: {vpcm.lam}\n - ノイズレベル: {vpcm.noise}")

if __name__ == "__main__":
    if os.path.exists("summary.txt"): os.remove("summary.txt")
    run_all_experiments()
    save_summary("\n全工程完了。すべてのファイルがルートディレクトリに保存されました。")

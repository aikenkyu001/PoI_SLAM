#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import json
from datetime import datetime

from scipy.linalg import expm
from ripser import ripser
from sklearn.decomposition import PCA


# ============================================================
# 0. Global constants
# ============================================================

DIM = 32
SECTOR_SIZE = 8
N_SECTORS = 4
RNG = np.random.default_rng(1)


# ============================================================
# Logging utilities
# ============================================================

def init_log():
    return {
        "PKGF_LOG": {
            "experiment_id": "PKGF_EXPERIMENTS",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "language": "Python",
            "dim": DIM,
            "sector_size": SECTOR_SIZE,
            "num_sectors": N_SECTORS,
            "Constructive": {},
            "Destructive": {},
            "Unified": {},
            "GaugeBreaking": {},
            "MultiAgent": {},
            "Fields": {},
            "TDA": {},
            "Metadata": {
                "random_seed": 1,
                "machine": "Python",
                "compiler_or_interpreter": "CPython"
            }
        }
    }


def save_log(log, filename="pkgf_log_python.json"):
    with open(filename, "w") as f:
        json.dump(log, f, indent=2)


# ============================================================
# 1. Sector system & gauge group
# ============================================================

def sector_indices(alpha):
    s = alpha * SECTOR_SIZE
    e = s + SECTOR_SIZE
    return slice(s, e)


def projector(alpha):
    P = np.zeros((DIM, DIM))
    s = sector_indices(alpha)
    P[s, s] = np.eye(SECTOR_SIZE)
    return P


def gauge_generator(preserve_sectors=True):
    if preserve_sectors:
        blocks = []
        for _ in range(N_SECTORS):
            A = RNG.normal(size=(SECTOR_SIZE, SECTOR_SIZE))
            A = 0.5 * (A + A.T)  # symmetric
            blocks.append(A)

        # ← 修正：二重ループでブロック行列を構成
        return np.block([
            [
                blocks[i] if i == j else np.zeros_like(blocks[0])
                for j in range(N_SECTORS)
            ]
            for i in range(N_SECTORS)
        ])

    else:
        A = RNG.normal(size=(DIM, DIM))
        return A


def gauge_action(H, K):
    H_inv = np.linalg.inv(H)
    return H @ K @ H_inv


# ============================================================
# 2. Differential geometry core
# ============================================================

def init_connection():
    A = RNG.normal(size=(DIM, DIM))
    omega = 0.5 * (A - A.T)  # antisymmetric
    return omega


def curvature(omega):
    # 離散一点上の「曲率」として ω^2 を採用（dω=0 とみなす）
    return omega @ omega


def covariant_derivative(K, omega):
    return omega @ K - K @ omega


# ============================================================
# 3. PKGF operators & metric modulation
# ============================================================

def commutator(A, B):
    return A @ B - B @ A


def constructive_term(K, Omega):
    return commutator(Omega, K)


def destructive_operator(K):
    # 理論 P10: 対称部分に対するランク低下の勾配
    S = 0.5 * (K + K.T)
    return S


def unified_operator(K, Omega, lam):
    return constructive_term(K, Omega) - lam * destructive_operator(K)


def metric_modulation_eta_from_K(K):
    """
    公理 U5/Extension A: 文脈依存計量 η(x) を、K の対角成分から構成する。
    Context セクタ E_C の平均値を文脈状態とみなす。
    """
    d = K.shape[0]
    x = np.diag(K).copy()
    
    # 次元に応じて Context セクタの範囲を調整 (NaN 回避)
    if d >= 32:
        ctx_slice = sector_indices(3)
        x_ctx = x[ctx_slice]
    else:
        # 低次元の場合は最後の一要素を文脈とみなす
        x_ctx = x[-1:]
        
    bar_ctx = np.mean(x_ctx) if len(x_ctx) > 0 else 0.0
    
    # 文脈が強いほど eta が小さくなり、構造が固定化（保守적）される
    eta = 1.0 / (1.0 + 0.5 * np.abs(bar_ctx))
    return float(eta)


# ============================================================
# 4. Sixteen fields Ω^(1..16) (Axiom P7 / U2 Detailed)
# ============================================================

class PKGFields:
    @staticmethod
    def semantics(K): return np.diag(np.tanh(np.diag(K)))
    @staticmethod
    def context(K): 
        d = K.shape[0]
        if d >= 32:
            ctx = np.mean(np.diag(K)[sector_indices(3)])
        else:
            ctx = np.mean(np.diag(K)[-1:])
        return ctx * np.eye(d)
    @staticmethod
    def metric(K): return np.diag(np.abs(np.diag(K)))
    @staticmethod
    def transformation(K): 
        d = K.shape[0]
        T = np.zeros((d, d))
        if d >= 16:
            T[0:8, 8:16] = 1.0; T[8:16, 0:8] = -1.0
        else:
            mid = d // 2
            T[0:mid, mid:2*mid] = 1.0; T[mid:2*mid, 0:mid] = -1.0
        return T
    @staticmethod
    def desire(K): return np.diag(np.sin(np.diag(K)))
    @staticmethod
    def ethics(K): return -0.05 * (K + K.T)
    @staticmethod
    def emotion(K): 
        d = K.shape[0]
        E = np.zeros((d, d))
        if d >= 24:
            E[16:24, 16:24] = RNG.normal(size=(8, 8))
        else:
            E = RNG.normal(size=(d, d))
        return 0.5 * (E - E.T)
    @staticmethod
    def value(K): return np.diag(np.exp(-np.abs(np.diag(K))))
    @staticmethod
    def learning(K): return RNG.normal(size=K.shape) * 0.01
    @staticmethod
    def memory(K): return 0.05 * np.eye(K.shape[0])
    @staticmethod
    def metacognition(K): return np.trace(K) * 0.001 * np.eye(K.shape[0])
    @staticmethod
    def meta_update(K): return np.zeros(K.shape)
    @staticmethod
    def self_reference(K): return 0.02 * (K @ K.T)
    @staticmethod
    def awareness(K): 
        d = K.shape[0]
        A = np.zeros((d, d))
        if d >= 8:
            A[0:8, 0:8] = 1.0
        else:
            A[0, 0] = 1.0
        return A
    @staticmethod
    def strategy(K): return np.zeros(K.shape)
    @staticmethod
    def social(K): return np.zeros(K.shape)

FIELD_FUNCS = [
    PKGFields.semantics, PKGFields.context, PKGFields.metric, PKGFields.transformation,
    PKGFields.desire, PKGFields.ethics, PKGFields.emotion, PKGFields.value,
    PKGFields.learning, PKGFields.memory, PKGFields.metacognition, PKGFields.meta_update,
    PKGFields.self_reference, PKGFields.awareness, PKGFields.strategy, PKGFields.social
]

def build_Omega(K):
    d = K.shape[0]
    Omega = np.zeros((d, d))
    for f in FIELD_FUNCS:
        res = f(K)
        # 行列の次元が一致する場合のみ加算
        if res.shape == (d, d):
            Omega += res
    # 反対称化（ゲージ接続 generator）
    return 0.5 * (Omega - Omega.T)


# ============================================================
# 5. PKGF flows (Refined with Axioms)
# ============================================================

def constructive_step_unitary(K, Omega, dt, eta=1.0):
    """
    K(t+dt) = exp(dt η Ω) K(t) exp(-dt η Ω)
    Metric Modulation (eta) を導入。
    """
    U = expm(dt * eta * Omega)
    return U @ K @ np.linalg.inv(U)


def destructive_step_lowrank(K, lam, dt, eta=1.0, shrink_tol=1e-3):
    """
    公理 D3: 特異値切断によるランク低下の確実な誘導。
    """
    d = K.shape[0]
    U, s, Vh = np.linalg.svd(K)
    # 指数減衰。etaが小さい（文脈が強い）ほど減衰が抑えられる
    s_new = s * np.exp(-(lam / eta) * dt)
    # しきい値処理でランクを落とす
    s_new[s_new < shrink_tol] = 0.0
    
    # 形状を合わせるための対角行列再構成
    S_mat = np.zeros((d, d))
    np.fill_diagonal(S_mat, s_new)
    return U @ S_mat @ Vh


def unified_step_metabolic(K, Omega, lam, dt):
    """
    Axiom U3: 代謝フロー。動的計量 η を介した構築と解体の統合。
    """
    eta = metric_modulation_eta_from_K(K)
    K_c = constructive_step_unitary(K, Omega, dt, eta)
    K_m = destructive_step_lowrank(K_c, lam, dt, eta)
    return K_m



# ============================================================
# 6. Metrics & observables
# ============================================================

def gauge_invariants(K):
    vals = np.linalg.eigvals(K)
    return np.linalg.det(K), np.sort(vals)


def sector_mixing_norm(K):
    mix = 0.0
    for a in range(N_SECTORS):
        for b in range(N_SECTORS):
            if a == b:
                continue
            P_a = projector(a)
            P_b = projector(b)
            mix += np.linalg.norm(P_a @ K @ P_b)
    return float(mix)


def effective_rank(K, tol=1e-4):
    vals = np.linalg.eigvals(K)
    return int(np.sum(np.abs(vals) > tol))


def entropy_from_samples(samples, bins=50):
    hist, _ = np.histogram(samples, bins=bins, density=True)
    hist = hist[hist > 0]
    return float(-np.sum(hist * np.log(hist + 1e-12)))


def symmetric_part(K):
    return 0.5 * (K + K.T)


def antisymmetric_part(K):
    return 0.5 * (K - K.T)


# ============================================================
# 7. TDA utilities (Persistent Homology via ripser)
# ============================================================

def betti_numbers_from_point_cloud(points, maxdim=2, eps=1e-3):
    """
    ripser を用いて 0,1,2 次のベッチ数を推定。
    PCA で 3 次元に落としてから解析する。
    """
    # --- PCA で 3 次元に次元削減 ---
    pca = PCA(n_components=3)
    pts = pca.fit_transform(points)

    # --- ripser に「点群」であることを明示 ---
    result = ripser(pts, maxdim=maxdim, distance_matrix=False)

    dgms = result["dgms"]
    bettis = []
    for k in range(maxdim + 1):
        diag = dgms[k]
        count = 0
        for birth, death in diag:
            if np.isinf(death):
                count += 1
            elif death - birth > eps:
                count += 1
        bettis.append(int(count))
    return bettis


# ============================================================
# 8. K initialization
# ============================================================

def init_K_block_diagonal():
    K = np.zeros((DIM, DIM))
    for b in range(N_SECTORS):
        A = RNG.normal(size=(SECTOR_SIZE, SECTOR_SIZE))
        A = 0.5 * (A + A.T) + 2.0 * np.eye(SECTOR_SIZE)
        s = b * SECTOR_SIZE
        K[s:s+SECTOR_SIZE, s:s+SECTOR_SIZE] = A
    return K


def get_so_generators(n):
    """SO(n)のリー代数生成子（反対称行列）の基底を生成"""
    gens = []
    for i in range(n):
        for j in range(i + 1, n):
            G = np.zeros((n, n))
            G[i, j] = 1.0
            G[j, i] = -1.0
            gens.append(G)
    return gens


def calculate_stabilizer_dimension(K, tol=1e-2):
    """
    リー代数的手法による安定化群の次元計算。
    [X, K] = 0 を満たすリー環基底 X の空間の次元を求める。
    """
    gens = get_so_generators(DIM)
    n_gens = len(gens)
    matrix_op = np.zeros((DIM * DIM, n_gens))
    
    for k, G in enumerate(gens):
        comm = G @ K - K @ G
        matrix_op[:, k] = comm.flatten()
        
    s = np.linalg.svd(matrix_op, compute_uv=False)
    dim_stab = np.sum(s < tol)
    return int(dim_stab)


# ============================================================
# 9. Experiments
# ============================================================

def experiment_constructive_invariants(log, T=50, dt=0.05):
    K = init_K_block_diagonal()
    Omega = build_Omega(K)

    det0, _ = gauge_invariants(K)
    mix0 = sector_mixing_norm(K)

    det_list = []
    mix_list = []
    comm_norm_list = []

    for _ in range(T):
        K = constructive_step_unitary(K, Omega, dt)
        det_t, _ = gauge_invariants(K)
        det_list.append(float(det_t))
        mix_list.append(sector_mixing_norm(K))
        comm_norm_list.append(float(np.linalg.norm(constructive_term(K, Omega))))

    log["PKGF_LOG"]["Constructive"] = {
        "det_initial": float(det0),
        "det_final": float(det_list[-1]),
        "sector_mixing_initial": float(mix0),
        "sector_mixing_final": float(mix_list[-1]),
        "max_comm_norm": float(np.max(comm_norm_list)),
        "steps": T
    }


def experiment_destructive_rank_entropy(log, T=80, dt=0.05, lam=0.8):
    K = init_K_block_diagonal()

    ranks = []
    entropies = []
    dets = []

    for _ in range(T):
        x = RNG.normal(size=(DIM, 800))
        y = K @ x
        S = entropy_from_samples(y.flatten())
        entropies.append(S)
        ranks.append(effective_rank(K))
        dets.append(float(np.linalg.det(K)))

        K = destructive_step_lowrank(K, lam=lam, dt=dt)

    log["PKGF_LOG"]["Destructive"] = {
        "det_sequence": dets,
        "entropy_sequence": entropies,
        "effective_rank_sequence": ranks,
        "steps": T
    }


def experiment_unified_metabolic(log, T=200, dt=0.02,
                                 lam0=0.2, lam_amp=0.15, omega=0.1):
    K = init_K_block_diagonal()

    det_list = []
    core_det_list = []
    fluct_norm_list = []
    lam_list = []
    phi_list = []
    metric_scaling_list = []

    for step in range(T):
        t = step * dt
        lam_t = lam0 + lam_amp * np.sin(omega * t)
        lam_list.append(float(lam_t))

        eta = metric_modulation_eta_from_K(K)
        metric_scaling_list.append(eta)

        Omega = build_Omega(K)
        K = unified_step_metabolic(K, Omega, lam_t, dt)

        det_list.append(float(np.linalg.det(K)))
        K_core = symmetric_part(K)
        K_fluct = antisymmetric_part(K)
        core_det_list.append(float(np.linalg.det(K_core)))
        fluct_norm_list.append(float(np.linalg.norm(K_fluct)))
        phi_list.append(float(np.linalg.norm(destructive_operator(K))))

    log["PKGF_LOG"]["Unified"] = {
        "det_sequence": det_list,
        "core_det_sequence": core_det_list,
        "fluct_norm_sequence": fluct_norm_list,
        "lambda_sequence": lam_list,
        "order_parameter_sequence": phi_list,
        "metric_scaling_sequence": metric_scaling_list,
        "steps": T
    }


def experiment_gauge_breaking(log, T=100, dt=0.02, lam=0.5):
    """公理 U4: ゲージ対称性の自発的破れの追跡"""
    K = np.eye(DIM) + RNG.normal(scale=0.1, size=(DIM, DIM))
    
    phi_list = []
    stabilizer_dim_seq = []
    rank_seq = []

    for _ in range(T):
        Omega = build_Omega(K)
        K = unified_step_metabolic(K, Omega, lam, dt)
        
        phi = float(np.linalg.norm(destructive_operator(K)))
        phi_list.append(phi)
        
        # 安定化群の次元計算（厳密）
        dim_stab = calculate_stabilizer_dimension(K)
        stabilizer_dim_seq.append(dim_stab)
        rank_seq.append(effective_rank(K))

    log["PKGF_LOG"]["GaugeBreaking"] = {
        "order_parameter_sequence": phi_list,
        "stabilizer_dim_sequence": stabilizer_dim_seq,
        "rank_sequence": rank_seq,
        "steps": T
    }


def experiment_multi_agent(log, n_agents=4, T=120, dt=0.05, lam=0.2):
    """
    Extension D: 臨界次元探索 (Critical Dimension Search)
    定理 6: D >= n ならば安定。D < n ならば競合。
    次元 D を 2 から n_agents + 4 までスイープし、臨界点 D* を探索する。
    """
    resonance_energies_all_D = []
    critical_D = None
    threshold = 0.5  # エネルギーがこの値を下回れば「解消」とみなす
    
    # 次元のスイープ (D=2 から n_agents+4 程度まで)
    d_range = range(2, n_agents + 5)
    
    for D in d_range:
        agents_K = [np.eye(D) + RNG.normal(scale=0.1, size=(D, D)) for _ in range(n_agents)]
        F_social = 0.5 * (RNG.normal(size=(D, D)) - RNG.normal(size=(D, D)).T)
        
        energies_seq = []
        for _ in range(T):
            step_energy = 0
            for i in range(n_agents):
                # 社会的曲率 F と 内部 Omega の結合
                # build_Omega は本来 DIM 次元用なので、D 次元にスライスして利用
                Omega = 0.5 * F_social + 0.5 * build_Omega(agents_K[i])[:D, :D]
                agents_K[i] = unified_step_metabolic(agents_K[i], Omega, lam, dt)
                # 社会場との非共鳴エネルギー: ||[K, F]||
                step_energy += np.linalg.norm(agents_K[i] @ F_social - F_social @ agents_K[i])
            
            energies_seq.append(float(step_energy / n_agents))
        
        resonance_energies_all_D.append(energies_seq)
        
        # 最終的なエネルギーが閾値を下回った最初の次元を D* とみなす
        if energies_seq[-1] < threshold and critical_D is None:
            critical_D = D

    log["PKGF_LOG"]["MultiAgent"] = {
        "num_agents": n_agents,
        "d_range": list(d_range),
        "social_resonance_energy_sequence": resonance_energies_all_D,
        "critical_dimension_detected": critical_D is not None,
        "critical_dimension_value": critical_D,
        "steps": T
    }


def experiment_phase_diagram(log, n_points=10, T=100, dt=0.05):
    """
    統一PKGF 相図 (Phase Diagram) の作成
    lambda (解体強度) と A (内部矛盾/Omega強度) を軸に知能の状態を分類。
    """
    lam_range = np.linspace(0.01, 1.0, n_points)
    omega_range = np.linspace(0.1, 2.0, n_points)
    
    phase_matrix = [] # 0: Constructive, 1: Metabolic (Stable Cycle), 2: Destructive/Collapsed
    
    for lam in lam_range:
        row = []
        for omega_scale in omega_range:
            K = init_K_block_diagonal()
            # 安定性評価用の指標
            det_history = []
            
            for _ in range(T):
                Omega = build_Omega(K) * omega_scale
                K = unified_step_metabolic(K, Omega, lam, dt)
                det_history.append(float(np.linalg.det(K)))
            
            # 状態分類ロジック
            # 1. 崩壊 (det -> 0)
            if det_history[-1] < 1e-4:
                row.append(2)
            # 2. 代謝平衡/呼吸 (det が一定幅で振動)
            elif np.std(det_history[-20:]) > 1e-1:
                row.append(1)
            # 3. 構築/固定 (det が安定、または単調増加)
            else:
                row.append(0)
        phase_matrix.append(row)

    log["PKGF_LOG"]["PhaseDiagram"] = {
        "lambda_range": lam_range.tolist(),
        "omega_scale_range": omega_range.tolist(),
        "phase_matrix": phase_matrix,
        "legend": {
            "0": "Constructive (Stable/Crystalline)",
            "1": "Metabolic (Breathing/Oscillatory)",
            "2": "Destructive (Collapsed/Dissipated)"
        }
    }


def experiment_fields_ablation(log):
    """16フィールドのアブレーション解析: 各フィールドの「構造維持力」を分析"""
    contributions = {}
    K_ref = np.eye(DIM)

    for f in FIELD_FUNCS:
        K = K_ref.copy()
        # 特定のフィールドのみをONにして、代謝サイクルを回す
        for _ in range(10):
            # Omega はこのフィールドのみから構築
            Omega = 0.5 * (f(K) - f(K).T)
            K = unified_step_metabolic(K, Omega, lam=0.1, dt=0.05)
        
        name = f.__name__.replace("field_", "")
        contributions[name] = {
            "final_rank": effective_rank(K),
            "trace": float(np.trace(K))
        }

    log["PKGF_LOG"]["Fields"] = contributions



def experiment_tda(log, T=40, dt=0.05, lam=0.25, maxdim=2):
    """
    Unified PKGF の流れの中で、K(t) の作用を受けた基底ベクトル群を点群とみなし、
    ripser でベッチ数を計算する。
    """
    K = init_K_block_diagonal()

    betti_0_seq = []
    betti_1_seq = []
    betti_2_seq = []

    tda_critical_step = None
    prev_betti = None

    for step in range(T):
        Omega = build_Omega(K)
        K = unified_step_metabolic(K, Omega, lam, dt)

        # 基底ベクトル e_i に K を作用させた点群（DIM 個の点）
        E = np.eye(DIM)
        Y = (K @ E).T  # shape (DIM, DIM)

        b0, b1, b2 = betti_numbers_from_point_cloud(Y, maxdim=maxdim)
        betti_0_seq.append(b0)
        betti_1_seq.append(b1)
        betti_2_seq.append(b2)

        if prev_betti is not None and tda_critical_step is None:
            if (b0 != prev_betti[0]) or (b1 != prev_betti[1]) or (b2 != prev_betti[2]):
                tda_critical_step = step
        prev_betti = (b0, b1, b2)

    log["PKGF_LOG"]["TDA"] = {
        "betti_0_sequence": betti_0_seq,
        "betti_1_sequence": betti_1_seq,
        "betti_2_sequence": betti_2_seq,
        "tda_critical_step": int(tda_critical_step) if tda_critical_step is not None else None,
        "barcode_snapshots": None  # 必要なら別途保存
    }


# ============================================================
# 10. main()
# ============================================================

def main():
    log = init_log()

    print("Running Experiment: Constructive Invariants...")
    experiment_constructive_invariants(log)
    
    print("Running Experiment: Destructive Rank & Entropy...")
    experiment_destructive_rank_entropy(log)
    
    print("Running Experiment: Unified Metabolic Flow...")
    experiment_unified_metabolic(log)
    
    print("Running Experiment: Gauge Symmetry Breaking...")
    experiment_gauge_breaking(log)
    
    print("Running Experiment: Multi-Agent Critical Dimension Search...")
    experiment_multi_agent(log)
    
    print("Running Experiment: Phase Diagram Mapping...")
    experiment_phase_diagram(log)
    
    print("Running Experiment: 16 Fields Ablation...")
    experiment_fields_ablation(log)
    
    print("Running Experiment: TDA (Persistent Homology)...")
    experiment_tda(log)

    save_log(log, "pkgf_log_python.json")
    print("PKGF Python experiments completed. Log saved to pkgf_log_python.json")


if __name__ == "__main__":
    main()

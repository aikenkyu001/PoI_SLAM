# filename: step5_pkgf_phase_diagram_multi_device.py
# Purpose:
#   - Regime A: 崩壊相（高ランク初期 → rank-1 へ潰れる, RankJump < 0）
#   - Regime B: 強い構造生成相（大きな RankJump > 0）
#   - Regime C: 弱結合・線形相（小さな RankJump > 0）
#   → PoI の 3 相図を 1 ファイルで実験・可視化
#   - 付録: CPU vs GPU vs ANE の簡易デュエル（Step4 Task J 風）

from typing import Optional, Dict, Any
import numpy as np
import matplotlib.pyplot as plt
import time
import json

# GPU / ANE 用（インポートできない環境でも動くように try/except）
try:
    import mlx.core as mx
except ImportError:
    mx = None

try:
    import torch
    import torch.nn as nn
    import coremltools as ct
except ImportError:
    torch = None
    nn = None
    ct = None


# ------------------------------------------------------------
# 1. Dynamic structured potential Ω(t)
# ------------------------------------------------------------
def make_dynamic_potential(n: int, t: int, T: int) -> np.ndarray:
    y, x = np.indices((n, n))

    cx = (n / 2) + 6 * np.sin(2 * np.pi * t / T)
    cy = (n / 2) + 6 * np.cos(2 * np.pi * t / T)

    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    radius = n * 0.20

    omega = np.exp(-0.5 * (r / radius) ** 2)
    omega = omega / omega.max()

    anti = omega - omega.T
    sym = (omega + omega.T) / 2.0
    return 0.5 * sym + 0.5 * anti


# ------------------------------------------------------------
# 2. Dissipation operator
# ------------------------------------------------------------
def dissipate(K: np.ndarray, sigma: float) -> np.ndarray:
    kernel = np.array([
        [1, 2, 1],
        [2, 4, 2],
        [1, 2, 1]
    ], dtype=float)
    kernel /= kernel.sum()

    padded = np.pad(K, 1, mode="reflect")
    out = np.zeros_like(K)

    for i in range(K.shape[0]):
        for j in range(K.shape[1]):
            region = padded[i:i+3, j:j+3]
            out[i, j] = (1 - sigma) * K[i, j] + sigma * np.sum(region * kernel)

    return out


# ------------------------------------------------------------
# 3. Commutator
# ------------------------------------------------------------
def commutator(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    return A @ B - B @ A


# ------------------------------------------------------------
# 4. Effective rank
# ------------------------------------------------------------
def effective_rank(K: np.ndarray, eps: float = 1e-12) -> float:
    s = np.linalg.svd(K, compute_uv=False)
    s = s[s > eps]
    if len(s) == 0:
        return 0.0
    return (s.sum() ** 2) / (s ** 2).sum()


# ------------------------------------------------------------
# 5. PKGF flow (single run, CPU/NumPy)
#    regime_type:
#      "A" → 崩壊相用（高ランク初期）
#      "B","C" → 生成・線形相用（rank-1 初期）
# ------------------------------------------------------------
def run_pkgf_cpu(
    n: int,
    sigma: float,
    xi: float,
    eta: float,
    steps: int,
    regime_type: str,
    seed: Optional[int] = None,
    nonlin_interval: int = 0
):
    rng = np.random.default_rng(seed)

    if regime_type == "A":
        # 高ランク初期化：崩壊相を確実に出す
        Q, _ = np.linalg.qr(rng.standard_normal((n, n)))
        S = np.linspace(1.0, 0.1, n)
        K = Q @ np.diag(S) @ Q.T
    else:
        # rank-1 + 微小ノイズ：生成・線形相の標準設定
        u = rng.standard_normal(n)
        v = rng.standard_normal(n)
        K = np.outer(u, v)
        K = K / np.max(np.abs(K))
        K = K + 1e-3 * rng.standard_normal((n, n))

    d0 = effective_rank(K)

    for t in range(steps):
        omega_t = make_dynamic_potential(n, t, steps)

        noise = rng.standard_normal((n, n))
        omega_t = omega_t + xi * noise

        K = dissipate(K, sigma=sigma)
        K = K + eta * commutator(omega_t, K)

        if nonlin_interval > 0 and (t + 1) % nonlin_interval == 0:
            K = np.tanh(K * 1.5)

        max_abs = np.max(np.abs(K))
        if max_abs > 0:
            K = K / max_abs

    K = np.clip(K, -4.0, 4.0)
    K = np.exp(K * 2.0)
    K = K / np.max(np.abs(K))

    dT = effective_rank(K)
    return d0, dT, dT - d0


# ------------------------------------------------------------
# 6. Sweep ξ for one regime (CPU)
# ------------------------------------------------------------
def sweep_noise_regime_cpu(
    n: int,
    sigma: float,
    eta: float,
    steps: int,
    nonlin_interval: int,
    xi_values: np.ndarray,
    regime_name: str,
    regime_type: str,
    base_seed: int = 1000
) -> Dict[str, Any]:
    print(f"\n=== Regime {regime_name} (CPU) ===")
    print(f"  n={n}, sigma={sigma}, eta={eta}, steps={steps}, nonlin_interval={nonlin_interval}")

    results = {
        "xi": [],
        "rank_jump": [],
        "d0": [],
        "dT": []
    }

    for i, xi in enumerate(xi_values):
        d0, dT, rj = run_pkgf_cpu(
            n=n,
            sigma=sigma,
            xi=xi,
            eta=eta,
            steps=steps,
            regime_type=regime_type,
            seed=base_seed + i,
            nonlin_interval=nonlin_interval
        )
        results["xi"].append(xi)
        results["rank_jump"].append(rj)
        results["d0"].append(d0)
        results["dT"].append(dT)

        print(f"[{regime_name}] [N={n}] xi={xi:.3f} -> RankJump={rj:.4f} (d0={d0:.2f}, dT={dT:.2f})")

    return results


# ------------------------------------------------------------
# 7. Plot all regimes (CPU)
# ------------------------------------------------------------
def plot_all_regimes(regime_results: Dict[str, Dict[str, Any]], n: int):
    plt.figure(figsize=(9, 6))

    for name, res in regime_results.items():
        xi = np.array(res["xi"])
        rj = np.array(res["rank_jump"])
        plt.plot(xi, rj, marker="o", ms=3, label=name)

    plt.axhline(0, color="k", linestyle="--", linewidth=0.8)
    plt.xlabel("Noise strength ξ")
    plt.ylabel("Rank Jump Δd_eff")
    plt.title(f"PKGF Noise Phase Diagram (N={n}) [CPU]")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig("step5_phase_diagram_cpu.png", dpi=220)


# ------------------------------------------------------------
# 8. (Optional) Step4 風: CPU vs GPU vs ANE デュエル
#    ※ フェーズ図とは独立の簡易ベンチマーク
# ------------------------------------------------------------
def create_ane_flow_model(N: int):
    """
    Step4 Task J と同じ形の「1ステップ更新」モデル。
    PKGF 本体とは少し簡略化した流れだが、ANE が動くかどうかの確認用。
    """
    if torch is None or nn is None or ct is None:
        raise RuntimeError("torch / coremltools がインポートできません。ANE モデルを作れません。")

    class PKGFFlow(nn.Module):
        def forward(self, omega, k):
            comm = torch.matmul(omega, k) - torch.matmul(k, omega)
            k_next = k + 0.05 * (comm - 0.1 * k)
            return torch.sigmoid(k_next * 2.5)

    model = PKGFFlow().eval()
    ex_omega = torch.rand(1, N, N)
    ex_k = torch.rand(1, N, N)

    mlmodel = ct.convert(
        torch.jit.trace(model, (ex_omega, ex_k)),
        inputs=[
            ct.TensorType(shape=ex_omega.shape, name="omega"),
            ct.TensorType(shape=ex_k.shape, name="k")
        ],
        compute_units=ct.ComputeUnit.ALL
    )
    return mlmodel


def benchmark_cpu_simple(omega, k, steps: int = 100) -> float:
    start = time.time()
    for _ in range(steps):
        comm = np.dot(omega, k) - np.dot(k, omega)
        k = k + 0.05 * (comm - 0.1 * k)
        k = 1 / (1 + np.exp(-k * 2.5))
    return (time.time() - start) * 1000.0


def benchmark_gpu_simple(omega, k, steps: int = 100) -> float:
    if mx is None:
        raise RuntimeError("mlx.core がインポートできません。GPU ベンチマークは実行できません。")

    start = time.time()
    for _ in range(steps):
        comm = mx.matmul(omega, k) - mx.matmul(k, omega)
        k = k + 0.05 * (comm - 0.1 * k)
        k = mx.sigmoid(k * 2.5)
        mx.eval(k)
    return (time.time() - start) * 1000.0


def benchmark_ane_simple(ane_model, omega, k, steps: int = 100) -> float:
    start = time.time()
    for _ in range(steps):
        out = ane_model.predict({"omega": omega, "k": k})
        k = list(out.values())[0]
    return (time.time() - start) * 1000.0


def run_all_device_duel(N: int = 256):
    print(f"--- Step5: All-Device PKGF Flow Duel (N={N}) ---")

    omega_np = np.random.rand(N, N).astype(np.float32)
    k_np = np.random.rand(N, N).astype(np.float32)

    # GPU 用
    if mx is not None:
        omega_mx = mx.array(omega_np)
        k_mx = mx.array(k_np)
    else:
        omega_mx = None
        k_mx = None

    # ANE 用
    if ct is not None and torch is not None:
        omega_ane = omega_np.reshape(1, N, N)
        k_ane = k_np.reshape(1, N, N)
        ane_model = create_ane_flow_model(N)
    else:
        omega_ane = None
        k_ane = None
        ane_model = None

    print("Benchmarking CPU...")
    t_cpu = benchmark_cpu_simple(omega_np, k_np)

    if omega_mx is not None and k_mx is not None:
        print("Benchmarking GPU (MLX)...")
        t_gpu = benchmark_gpu_simple(omega_mx, k_mx)
    else:
        t_gpu = None
        print("GPU (MLX) not available.")

    if ane_model is not None:
        print("Benchmarking ANE (CoreML)...")
        t_ane = benchmark_ane_simple(ane_model, omega_ane, k_ane)
    else:
        t_ane = None
        print("ANE (CoreML) not available.")

    print("-" * 55)
    print(f"{'Device':<20} | {'100-Step Time (ms)':<20}")
    print("-" * 55)
    print(f"{'CPU (NumPy)':<20} | {t_cpu:20.4f}")
    if t_gpu is not None:
        print(f"{'GPU (MLX)':<20} | {t_gpu:20.4f}")
    if t_ane is not None:
        print(f"{'ANE (CoreML)':<20} | {t_ane:20.4f}")
    print("-" * 55)

    results = {
        "N": N,
        "cpu_ms": t_cpu,
        "gpu_ms": t_gpu,
        "ane_ms": t_ane
    }
    with open("step5_multi_device_duel_results.json", "w") as f:
        json.dump(results, f, indent=4)


# ------------------------------------------------------------
# 9. Main: 3 相図の最終実験（CPU）＋（任意）デバイスデュエル
# ------------------------------------------------------------
def main():
    n = 100
    xi_values = np.linspace(0.0, 1.0, 51)

    regime_results: Dict[str, Dict[str, Any]] = {}

    # Regime A: 崩壊相（高ランク初期 → rank-1 へ潰れる, RankJump < 0 を期待）
    regime_results["A: collapse (high-rank → low-rank)"] = sweep_noise_regime_cpu(
        n=n,
        sigma=0.45,          # 強い散逸
        eta=0.15,            # 弱い構築
        steps=220,           # 長め
        nonlin_interval=0,   # 中間非線形なし
        xi_values=xi_values,
        regime_name="A",
        regime_type="A",
        base_seed=1000
    )

    # Regime B: 強い生成相（大きな RankJump > 0）
    regime_results["B: strong C/U (large RankJump)"] = sweep_noise_regime_cpu(
        n=n,
        sigma=0.02,          # 弱い散逸
        eta=1.4,             # 強い構築
        steps=160,
        nonlin_interval=40,
        xi_values=xi_values,
        regime_name="B",
        regime_type="B",
        base_seed=2000
    )

    # Regime C: 弱結合・線形相（小さな RankJump > 0）
    regime_results["C: weak/linear (small RankJump)"] = sweep_noise_regime_cpu(
        n=n,
        sigma=0.12,          # 中程度の散逸
        eta=0.8,             # 弱い構築
        steps=80,
        nonlin_interval=30,
        xi_values=xi_values,
        regime_name="C",
        regime_type="C",
        base_seed=3000
    )

    plot_all_regimes(regime_results, n=n)

    # 必要ならコメントアウトを外して、デバイスデュエルも実行
    run_all_device_duel(N=256)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""U10 实验 C 的补充计算（2026-11-06，第 11 章改写用）。复用 u10_power.py 的精确计算，不改原输出。

1. 真实差 6 个百分点（第 11 章的示意：成功率 72% → 66%）：需要多少对、50 对的功效、A/A 碰巧差 ≥ 6 个百分点的概率。
2. 两个具体的符号检验：不一致对里 A、B 各赢几次时的双侧 p 值。
3. A/A 量 d 能量多准：观察到 d = 0.30 时，n 个任务的 95% 精确置信区间（Clopper-Pearson）。
4. 剔掉两边总是同成同败的任务：全部任务 d = 0.10、δ = 5 个百分点，和只留下三分之一任务（d = 0.30、δ = 15 个百分点）比较。

用法：python3 -I u10_power_extra.py --out <绝对路径>
"""
import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import u10_power as P  # noqa: E402


def sign_p(x, y):
    """不一致对里 A 赢 x 次、B 赢 y 次时，精确符号检验的双侧 p 值。"""
    D = x + y
    half = P.pmf(D, 0.5)
    k = min(x, y)
    return min(1.0, 2 * sum(half[: k + 1]))


def beta_ppf(q, a, b):
    """Beta(a, b) 的分位数：二分法求累积分布（用正则化不完全 beta 的级数，够用）。"""
    def cdf(x):
        # 二项和形式：I_x(a, b) = P(Binomial(a+b-1, x) >= a)，a、b 为正整数
        n = a + b - 1
        return sum(math.comb(n, j) * x ** j * (1 - x) ** (n - j) for j in range(a, n + 1))
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if cdf(mid) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def clopper_pearson(k, n, alpha=0.05):
    lo = 0.0 if k == 0 else beta_ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta_ppf(1 - alpha / 2, k + 1, n - k)
    return lo, hi


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    L = []

    L.append("== 1. 真实差 6 个百分点")
    for d in P.DS:
        L.append(f"d = {d:.2f}：80% 功效需要 {P.need_n(d, 0.06)} 对；50 对的功效 {P.power(50, d, 0.06) * 100:.1f}%；"
                 f"A/A 50 对碰巧差 ≥ 6 个百分点 {P.gap_prob(50, d, 0.06) * 100:.1f}%")

    L.append("\n== 2. 符号检验的例子（双侧 p 值）")
    for x, y, note in [(9, 6, "50 个任务、d = 0.30 时约 15 个不一致对，差 3 个 = 6 个百分点"),
                       (10, 5, "15 个不一致对，差 5 个 = 50 个任务上 10 个百分点"),
                       (6, 3, "30 个任务、d = 0.30 时约 9 个不一致对，差 3 个 = 10 个百分点")]:
        L.append(f"A 赢 {x}、B 赢 {y}：p = {sign_p(x, y):.3f}（{note}）")
    # 15 个不一致对时，要差多少才显著
    for D in (9, 15, 30, 75):
        c = P.crit(D)
        L.append(f"不一致对 {D} 个：一方至少赢 {D - c} 个（另一方 ≤ {c}）才算显著")

    L.append("\n== 3. A/A 量 d：观察到 d = 0.30 时的 95% 精确置信区间")
    for n in (30, 50, 100, 200):
        k = round(0.3 * n)
        lo, hi = clopper_pearson(k, n)
        L.append(f"n = {n}（{k} 个任务一成一败）：{lo:.3f} – {hi:.3f}")

    L.append("\n== 4. 剔掉总是同成同败的任务")
    a, b = P.need_n(0.10, 0.05), P.need_n(0.30, 0.15)
    L.append(f"全部任务 d = 0.10、δ = 5 个百分点：{a} 对，预期不一致对 {a * 0.10:.1f} 个")
    L.append(f"只留三分之一 d = 0.30、δ = 15 个百分点：{b} 对，预期不一致对 {b * 0.30:.1f} 个；"
             f"折回全部任务相当于 {b * 3} 个")

    text = "\n".join(L)
    (out / "extra.txt").write_text(text)
    print(text)

    # 给第 11 章第二节的交互：在 power-embed.json（4 位小数）的 deltas 里插入 0.06，其余格子原样保留
    import json
    base = json.loads((out / "power-embed.json").read_text())
    idx = next(i for i, x in enumerate(base["deltas"]) if x > 0.06)
    base["deltas"].insert(idx, 0.06)
    for d in P.DS:
        base["need"][str(d)].insert(idx, P.need_n(d, 0.06))
        for n in P.NS:
            base["power"][str(d)][str(n)].insert(idx, round(P.power(n, d, 0.06), 4))
    (out / "power-embed-6pp.json").write_text(json.dumps(base, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()

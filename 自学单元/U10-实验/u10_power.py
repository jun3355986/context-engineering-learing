#!/usr/bin/env python3
"""U10 实验 C：配对对照要跑多少个任务？两个完全一样的配置会碰巧差多少？

模型：n 个任务，每个任务在两个配置（A、B）下各跑一次，结果是成功/失败。
  d  = 不一致率：一个任务在 A、B 下结果不同（一个成功一个失败）的概率
  δ  = A 比 B 多成功的比例（p10 − p01），d = p10 + p01
  A/A：两个配置完全一样，δ = 0。此时 d 就是"同一个配置跑两遍，同一个任务一次成功一次失败"的比例。
  若所有任务难度相同、两次运行独立、成功率都是 p，则 d = 2p(1−p)（p=0.7 时 0.42）；
  任务有难有易时 d 更小。真实的 d 要靠 A/A 实验量，这里不假设。
检验：精确的符号检验（McNemar 精确版），双侧，α = 0.05。
输出：out/power.txt（给人看）和 out/power.json（给网页用）。全部精确计算，随后随机模拟核对几格。

用法：python3 -I u10_power.py --out <绝对路径>
"""
import argparse
import json
import math
import random
from pathlib import Path

ALPHA = 0.05
NS = [20, 30, 50, 100, 200, 400]
DS = [0.10, 0.20, 0.30, 0.42]
DELTAS = [0.02, 0.03, 0.05, 0.075, 0.10, 0.15, 0.20]
GAPS = [0.05, 0.10, 0.15]


def pmf(n, p):
    """Binomial(n,p) 的概率质量，返回长度 n+1 的列表。"""
    if p <= 0:
        return [1.0] + [0.0] * n
    if p >= 1:
        return [0.0] * n + [1.0]
    lp, lq, lf = math.log(p), math.log(1 - p), math.lgamma(n + 1)
    return [math.exp(lf - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * lp + (n - k) * lq)
            for k in range(n + 1)]


_cache = {}


def crit(D):
    """不一致对数为 D 时，符号检验拒绝的区域：x ≤ c 或 x ≥ D − c。返回 c（−1 表示永不拒绝）。"""
    if D in _cache:
        return _cache[D]
    half = pmf(D, 0.5)
    c, cum = -1, 0.0
    for k in range(D + 1):
        cum += half[k]
        if 2 * cum <= ALPHA + 1e-12:
            c = k
        else:
            break
    _cache[D] = c
    return c


def d_window(n, d):
    pd = pmf(n, d)
    return [(D, p) for D, p in enumerate(pd) if p > 1e-12]


def power(n, d, delta):
    q = (d + delta) / (2 * d)  # 不一致对里 A 成功 B 失败的比例
    total = 0.0
    for D, pD in d_window(n, d):
        c = crit(D)
        if c < 0:
            continue
        px = pmf(D, q)
        total += pD * (sum(px[: c + 1]) + sum(px[D - c:]))
    return total


def need_n(d, delta, target=0.8):
    """能让功效 ≥ target 的最小 n（先二分找，再往下扫几个，因为精确检验的功效会锯齿起伏）。"""
    if delta > d + 1e-12:
        return None
    lo, hi = 5, 8
    while power(hi, d, delta) < target:
        lo, hi = hi, hi * 2
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if power(mid, d, delta) >= target:
            hi = mid
        else:
            lo = mid
    n = hi
    for m in range(max(5, n - 12), n):
        if power(m, d, delta) >= target:
            n = m
            break
    return n


def normal_n(d, delta, za=1.96, zb=0.8416):
    return math.ceil((za * math.sqrt(d) + zb * math.sqrt(d - delta ** 2)) ** 2 / delta ** 2)


def gap_prob(n, d, t):
    """A/A（δ=0）时，两个配置成功率之差的绝对值 ≥ t 的概率：|X−Y| ≥ t·n。"""
    thr = t * n - 1e-9
    total = 0.0
    for D, pD in d_window(n, d):
        px = pmf(D, 0.5)
        total += pD * sum(p for x, p in enumerate(px) if abs(2 * x - D) >= thr)
    return total


def simulate_gap(n, d, t, trials, rng):
    thr = t * n - 1e-9
    hit = 0
    for _ in range(trials):
        diff = 0
        for _ in range(n):
            if rng.random() < d:
                diff += 1 if rng.random() < 0.5 else -1
        hit += abs(diff) >= thr
    return hit / trials


def simulate_power(n, d, delta, trials, rng):
    p10, p01 = (d + delta) / 2, (d - delta) / 2
    hit = 0
    for _ in range(trials):
        x = y = 0
        for _ in range(n):
            r = rng.random()
            if r < p10:
                x += 1
            elif r < p10 + p01:
                y += 1
        D = x + y
        c = crit(D)
        hit += c >= 0 and (min(x, y) <= c)
    return hit / trials


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--trials", type=int, default=20000)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lines, data = [], {"ns": NS, "ds": DS, "deltas": DELTAS, "gaps": GAPS}

    lines.append("== 1. 需要多少对任务（功效 ≥ 80%，α = 0.05 双侧，精确符号检验）")
    lines.append(f"{'d＼δ':>8}" + "".join(f"{x * 100:>8.1f}pp" for x in DELTAS) + "    （括号内：正态近似公式的结果）")
    data["need"] = {}
    for d in DS:
        row, cells = f"{d:>8.2f}", []
        for dl in DELTAS:
            n = need_n(d, dl)
            cells.append(n)
            row += f"{'—':>10}" if n is None else f"{n:>10}"
        data["need"][str(d)] = cells
        lines.append(row)
        lines.append(f"{'':>8}" + "".join(
            f"{'':>10}" if c is None else f"{'(' + str(normal_n(d, dl)) + ')':>10}" for c, dl in zip(cells, DELTAS)))

    lines.append("\n== 2. 手上有 n 对任务，真实差 δ 时，测得出来的概率（功效）")
    data["power"] = {}
    for d in DS:
        lines.append(f"-- d = {d}")
        lines.append(f"{'n＼δ':>8}" + "".join(f"{x * 100:>8.1f}pp" for x in DELTAS))
        data["power"][str(d)] = {}
        for n in NS:
            ps = [None if dl > d + 1e-12 else power(n, d, dl) for dl in DELTAS]
            data["power"][str(d)][str(n)] = ps
            lines.append(f"{n:>8}" + "".join(f"{'—':>10}" if p is None else f"{p * 100:>9.0f}%" for p in ps))

    lines.append("\n== 3. A/A：两个完全一样的配置，碰巧差 ≥ t 个百分点的概率")
    data["gap"] = {}
    for d in DS:
        lines.append(f"-- d = {d}")
        lines.append(f"{'n＼t':>8}" + "".join(f"{t * 100:>8.0f}pp" for t in GAPS))
        data["gap"][str(d)] = {}
        for n in NS:
            ps = [gap_prob(n, d, t) for t in GAPS]
            data["gap"][str(d)][str(n)] = ps
            lines.append(f"{n:>8}" + "".join(f"{p * 100:>9.1f}%" for p in ps))

    lines.append(f"\n== 4. 随机模拟核对（{args.trials} 次，种子 20261102）：精确值 / 模拟值")
    rng = random.Random(20261102)
    for n, d, t in [(30, 0.30, 0.10), (50, 0.42, 0.10), (100, 0.20, 0.05), (200, 0.30, 0.05)]:
        lines.append(f"A/A gap n={n} d={d} t={t * 100:.0f}pp：{gap_prob(n, d, t) * 100:.1f}% / "
                     f"{simulate_gap(n, d, t, args.trials, rng) * 100:.1f}%")
    for n, d, dl in [(100, 0.30, 0.10), (200, 0.30, 0.10), (50, 0.30, 0.20)]:
        lines.append(f"功效 n={n} d={d} δ={dl * 100:.0f}pp：{power(n, d, dl) * 100:.1f}% / "
                     f"{simulate_power(n, d, dl, args.trials, rng) * 100:.1f}%")

    (out / "power.txt").write_text("\n".join(lines))
    (out / "power.json").write_text(json.dumps(data, ensure_ascii=False))
    print("\n".join(lines))


if __name__ == "__main__":
    main()

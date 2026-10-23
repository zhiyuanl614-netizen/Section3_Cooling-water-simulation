"""
vcls.py — 电压崩溃最小减载（VCLS）：二分法可支撑负荷水平
=========================================================
思路
----
孤岛潮流不收敛时，求该孤岛**可支撑的最大负荷水平** λ* ∈ [0,1]：
        λ* = max{ λ | AC 潮流在负荷 λ·P_load 下收敛 }
以 PF 收敛性作为可行性判据做二分，等价于连续潮流法（CPF）的崩溃点搜索。

未供负荷 = (1 − λ*) · ΣP_load，按母线负荷比例分配；
再用 λ* 下的潮流解取得各母线电压，用于 F1/F2 判定。

为什么不用 AC-OPF 最小减载
--------------------------
AC-OPF 形式更"最优"，但（i）高压应力下 MIPS 求解器频繁返回 success=False，
（ii）"最小加权减载"依赖 VOLL 等主观权重，（iii）每岛一次 OPF 的计算代价高。
二分法（i）只用 PF 收敛性判据，稳健；（ii）物理含义清晰（崩溃前可支撑的负荷）；
（iii）单次仅 ~10 次 PF，代价可控。若需要"最优减载分布"，可在本模块外层再做 OPF 精修。
"""

from __future__ import annotations

import copy
import numpy as np
from pypower.api import runpf, ppoption


def _pf(case):
    res, ok = runpf(case, ppoption(VERBOSE=0, OUT_ALL=0))
    return (res, True) if ok else (None, False)


def _scale_load(case, lam):
    """负荷与（非平衡机）出力同比例缩放，保持孤岛功率自洽。"""
    c = copy.deepcopy(case)
    c["bus"][:, 2] *= lam
    c["bus"][:, 3] *= lam
    c["gen"][:, 1] *= lam
    c["gen"][:, 2] *= lam
    return c


def collapse_loadability(case, tol=0.005, lam_lo=0.0, lam_hi=1.0, max_iter=14):
    """
    返回 (lam_star, res_at_lam, converged_flag)
    lam_star = 可支撑的最大负荷比例；converged_flag 表示 λ 上限本身是否可行。
    """
    res1, ok1 = _pf(_scale_load(case, lam_hi))
    if ok1:
        return lam_hi, res1, True              # 全负荷可行，无需减载

    # 下界扫描：确保 λ=lam_lo 可行（通常为 0，即空载）
    while lam_lo < lam_hi:
        res0, ok0 = _pf(_scale_load(case, lam_lo))
        if ok0:
            break
        lam_lo = lam_lo / 2 if lam_lo > 1e-3 else 0.0
        if lam_lo <= 1e-6:
            return 0.0, None, False            # 空载都不可行 → 真实崩溃

    best_res = res0
    for _ in range(max_iter):
        if lam_hi - lam_lo < tol:
            break
        lam_mid = 0.5 * (lam_lo + lam_hi)
        res_m, ok_m = _pf(_scale_load(case, lam_mid))
        if ok_m:
            lam_lo, best_res = lam_mid, res_m
        else:
            lam_hi = lam_mid
    return lam_lo, best_res, False


def vcls(case, bus_ids=None):
    """
    返回 dict:
      ok        : 是否无需崩溃减载（原负荷直接可行）
      lam       : 可支撑负荷比例
      shed_total: 未供负荷 (MW)
      shed_frac : 未供负荷占该岛负荷比例
      shed_per_bus: {bus_id: MW}
      res       : λ* 下的潮流结果（用于取母线电压）
    """
    pd = case["bus"][:, 2].copy()
    load = float(pd.sum())
    res1, ok1 = _pf(case)
    if ok1:
        return dict(ok=True, lam=1.0, shed_total=0.0, shed_frac=0.0,
                    shed_per_bus={}, res=res1)

    lam, res, _ = collapse_loadability(case)
    shed_total = (1.0 - lam) * load
    per = {}
    for i, row in enumerate(case["bus"]):
        b = int(row[0])
        per[b] = float(pd[i] * (1.0 - lam))
    return dict(ok=False, lam=lam, shed_total=shed_total,
                shed_frac=(1.0 - lam) if load > 0 else 0.0,
                shed_per_bus=per, res=res)


if __name__ == "__main__":
    import copy
    from pypower.api import case30
    c = case30()
    c["gen"][:, 5] = np.clip(c["gen"][:, 5], 0.98, 1.03)
    c["gen"][:, 8] = np.maximum(c["gen"][:, 8], c["gen"][:, 1] * 1.15)

    print("=== 原始算例 ===")
    r = vcls(c)
    print(f"ok={r['ok']} lam={r['lam']:.3f} shed={r['shed_total']:.0f} MW")

    print("=== 跳开 G@39 (1100MW) 且不做再调度 ===")
    c2 = copy.deepcopy(c)
    c2["gen"][9, 7] = 0
    c2["gen"][9, 1] = c2["gen"][9, 2] = 0.0
    r = vcls(c2)
    print(f"ok={r['ok']} lam={r['lam']:.3f} shed={r['shed_total']:.0f} MW "
          f"({100*r['shed_frac']:.1f}%)")

    print("=== 跳开 G@39 + G@38 (1965MW) ===")
    c3 = copy.deepcopy(c)
    for k in (8, 9):
        c3["gen"][k, 7] = 0
        c3["gen"][k, 1] = c3["gen"][k, 2] = 0.0
    r = vcls(c3)
    print(f"ok={r['ok']} lam={r['lam']:.3f} shed={r['shed_total']:.0f} MW "
          f"({100*r['shed_frac']:.1f}%)")

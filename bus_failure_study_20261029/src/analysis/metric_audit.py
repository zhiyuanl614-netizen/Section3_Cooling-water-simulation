#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metric_audit.py — 母线服务/失效指标一致性审计
==========================================================
对已生成的 results/*/tables/*_summary.csv 逐案校验指标自洽性，并输出
前后口径对照。重点检查：

  1. H_count 是否等于 |F3|（F3 是唯一硬失供判据，二者应恒等）
  2. N3 是否与 H>0 严格一一对应
  3. bfi_hard 是否等于 H_count/30，且与 bfi_legacy_composite 区分
  4. 负荷加权严重度 h_load_ratio 与计数法 h_load 的差异
  5. 切负荷三量语义：shed_action_total / shed_peak / ufls
  6. t_first_H 与 observation_window 是否随 H 状态合理变化
  7. 求解器收敛性标记（solver_converged / 奇异告警计数）
  8. 指标退化：不同情景是否产生完全相同的电网后果

用法:
  python3 src/analysis/metric_audit.py [--results results] [--csv out.csv]
退出码 2 表示存在不自洽项（可用于 CI）。
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from coupling.metrics import TOTAL_LOAD_MW, bus_load_mw  # noqa: E402

LOAD_MW = bus_load_mw()

#: 注：第七轮重构曾需在输出口剔除 F1/F2 等已废止状态列；2026-10-28 全量重跑后
#: 源汇总表 K*/tables/*.csv 已不再写出这些字段，故该过滤已移除。

def num(row: dict, key: str, default=None):
    v = row.get(key, "")
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def collect(results_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(results_dir.glob("*/tables/*_summary.csv")):
        layer = path.parent.parent.name          # K1 … K6
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if not r.get("scenario_id") and not r.get("initial_unit"):
                    continue
                # K1 层汇总表无 scenario_id 列，按层目录 + 初始故障机组合成，
                # 否则审计表与 scenario_master 无法按 scenario_id 连接
                # （曾导致 6 个 K1 案在下游表中静默丢失）。
                if not (r.get("scenario_id") or "").strip() and r.get("initial_unit"):
                    r["scenario_id"] = f"{layer}-{str(r['initial_unit']).strip()}"
                r["_src"] = str(path.relative_to(ROOT))
                rows.append(r)
    # 注：此处曾有一段"兼容旧版 K1 目录结构"的回退，读取
    # K1/scenarios/*/cascade_summary.csv。重跑后该目录存在，导致 K1 的 6 行被
    # 重复计入（审计表 69 行而非 63）。K1 汇总表恒提供这些行，故回退已删除。
    return rows


def audit_row(r: dict) -> list[str]:
    issues: list[str] = []
    sid = r.get("scenario_id") or r.get("initial_unit") or "?"
    H = num(r, "n_bus_hard_failure")
    F3 = num(r, "n_f3_deenergized")
    if H is None:
        return [f"{sid}: 缺少 n_bus_hard_failure（新指标未生成）"]

    # 1. H = |F3|（F3 为唯一硬失供判据，二者应恒等）
    if F3 is not None and H != F3:
        issues.append(f"{sid}: H={H:.0f} != F3={F3:.0f}")

    # 2. N3 ⟺ H>0
    cls = (r.get("impact_class") or "")
    if H > 0 and not cls.startswith("N3"):
        issues.append(f"{sid}: H={H:.0f}>0 但类别为 {cls!r}（应为 N3）")
    if H == 0 and cls.startswith("N3"):
        issues.append(f"{sid}: H=0 却标为 N3（N3 应与 H>0 一一对应）")

    # 3. bfi_hard 与 H 一致
    bfi_hard = num(r, "bfi_hard")
    n_bus = num(r, "n_bus_total") or 30.0
    if bfi_hard is not None and abs(bfi_hard - H / n_bus) > 1e-6:
        issues.append(f"{sid}: bfi_hard={bfi_hard:.4f} != H/{n_bus:.0f}={H/n_bus:.4f}")

    # 4. 负荷加权严重度应在 [0,1] 且与计数法不矛盾
    hl = num(r, "h_load_ratio")
    if hl is not None:
        if not (0.0 <= hl <= 1.0 + 1e-9):
            issues.append(f"{sid}: h_load_ratio={hl:.4f} 越界")
        if hl > 0 and H == 0:
            issues.append(f"{sid}: H=0 但 h_load_ratio={hl:.4f}>0")
        if H > 0 and hl == 0.0:
            issues.append(f"{sid}: H={H:.0f}>0 但 h_load_ratio=0（负荷权重缺失？）")

    # 5. 切负荷三量语义
    peak = num(r, "shed_peak_mw")
    action = num(r, "total_shed_mw")
    if peak is not None and action is not None:
        if peak > action + 1e-3:
            issues.append(f"{sid}: shed_peak({peak:.1f}) > total_shed({action:.1f})")
        if action is not None and action > TOTAL_LOAD_MW * 1.05 and H == 0:
            issues.append(
                f"{sid}: H=0 但累计切负荷 {action:.1f} MW 超过全网负荷 "
                f"{TOTAL_LOAD_MW:.1f} MW（跨阶段重复计入）")

    # 8. 静态减载的成因分解应可加总回 static_grid_shed_mw
    #    static_grid_shed_mw 是 deenergized/collapse/vcls/uvls/ufls 的混合和；
    #    分离前无法回答"VCLS 究竟减了多少"，故此处强制分项可加。
    _COMPONENTS = ("deenergized_shed_mw", "collapse_shed_mw", "vcls_shed_mw",
                   "uvls_shed_mw", "grid_ufls_shed_mw")
    if "static_grid_shed_mw" in r and all(c in r for c in _COMPONENTS):
        stat = num(r, "static_grid_shed_mw") or 0.0
        parts = {c: (num(r, c) or 0.0) for c in _COMPONENTS}
        ssum = sum(parts.values())
        if abs(ssum - stat) > 1e-3:
            issues.append(
                f"{sid}: 静态减载分项合计 {ssum:.3f} != "
                f"static_grid_shed_mw {stat:.3f}（分解不可加）")
        if H == 0 and parts["deenergized_shed_mw"] + parts["collapse_shed_mw"] > 1e-6:
            issues.append(
                f"{sid}: H=0 却记录失电/崩溃减载 "
                f"{parts['deenergized_shed_mw'] + parts['collapse_shed_mw']:.3f} MW")

    # 6. t_first_H 时序合理性
    t_first = num(r, "t_first_hard_s")
    win = num(r, "observation_window_h")
    if H > 0 and t_first is None:
        issues.append(f"{sid}: H={H:.0f}>0 但缺少 t_first_hard_s")
    if H == 0 and t_first is not None:
        issues.append(f"{sid}: H=0 却记录了 t_first_hard_s={t_first}")
    if t_first is not None and win is not None:
        # observation_window_h 以 4 位小数（小时）存储，量化精度约 0.36 s；
        # 末位舍入可能使 t_first_H 略大于窗口，容差取 1 s。
        tol_s = 1.0
        if t_first > win * 3600.0 + tol_s:
            issues.append(f"{sid}: t_first_H={t_first/3600.0:.4f}h 超出观察窗口 {win:.4f}h")

    # 7. 收敛性
    conv = r.get("solver_converged", "")
    nsing = num(r, "n_singular_warnings", 0) or 0
    if conv == "":
        issues.append(f"{sid}: 缺少 solver_converged 字段")
    elif conv in ("False", "false", "0") and H > 0:
        issues.append(
            f"{sid}: solver_converged=False 且 H={H:.0f}>0 —— "
            f"收敛性是潮流求解前提，该 H 值为条件性结果")
    if nsing and conv not in ("False", "false", "0"):
        issues.append(f"{sid}: 有 {nsing:.0f} 条奇异告警但 solver_converged={conv!r}")
    return issues


def degeneracy_groups(rows: list[dict]) -> dict[tuple, list[str]]:
    groups: dict[tuple, list[str]] = defaultdict(list)
    for r in rows:
        H = num(r, "n_bus_hard_failure")
        if H is None:
            continue
        key = (H,
               num(r, "n_f3_deenergized", 0),
               num(r, "shed_peak_mw", num(r, "total_shed_mw", 0.0)),
               num(r, "f_nadir_hz", 0.0))
        groups[key].append(r.get("scenario_id") or r.get("initial_unit") or "?")
    return {k: v for k, v in groups.items() if len(v) > 1}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--csv", default="")
    args = ap.parse_args(argv)
    results_dir = Path(args.results)

    if not results_dir.exists():
        print(f"[skip] {results_dir} 不存在；先运行 ./run.sh 生成结果", file=sys.stderr)
        return 0

    rows = collect(results_dir)
    if not rows:
        print(f"[skip] {results_dir} 下未找到汇总表", file=sys.stderr)
        return 0

    # 只审计已应用新口径的案例（含 bfi_hard 字段）
    audited = [r for r in rows if "bfi_hard" in r]
    legacy = [r for r in rows if "bfi_hard" not in r]
    print(f"共发现 {len(rows)} 条汇总记录；新口径 {len(audited)} 条，"
          f"旧口径 {len(legacy)} 条")

    if legacy:
        print(f"\n[旧口径] 以下 {len(legacy)} 条尚未重跑，缺少 bfi_hard/"
              f"t_first_hard_s/solver_converged：")
        for r in legacy[:10]:
            print("   ", r.get("scenario_id") or r.get("initial_unit"))

    if not audited:
        print("\n尚无新口径案例；请先重跑 ./run.sh K1-all / K2 / K3 / K4 / K5 / K6")
        return 0

    issues: list[str] = []
    for r in audited:
        issues.extend(audit_row(r))

    print(f"\n{'='*72}\n逐案指标自洽性审计（{len(audited)} 案）\n{'='*72}")
    print(f"{'scenario':28s} {'H':>3s} {'H_load':>7s} {'bfi_hard':>9s} "
          f"{'bfi_legacy':>10s} {'class':>6s} {'t_first_H':>10s} {'conv':>5s}")
    for r in audited:
        print(f"{(r.get('scenario_id') or r.get('initial_unit'))[:28]:28s} "
              f"{num(r,'n_bus_hard_failure',0):3.0f} "
              f"{num(r,'h_load_ratio',0):7.3f} "
              f"{num(r,'bfi_hard',0):9.3f} "
              f"{num(r,'bfi_legacy_composite',0):10.3f} "
              f"{(r.get('impact_class') or '')[:6]:>6s} "
              f"{(('%.3fh'%(num(r,'t_first_hard_s')/3600.0)) if num(r,'t_first_hard_s') is not None else '—'):>10s} "
              f"{(r.get('solver_converged') or '?'):>5s}")

    print(f"\n{'='*72}\n指标退化组（同 H/F3/切负荷/最低频率，网格后果不可区分）\n{'='*72}")
    groups = degeneracy_groups(audited)
    if not groups:
        print("无退化组。")
    for key, sids in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print(f"  H={key[0]:.0f} F3={key[1]:.0f} shed_peak={key[2]:.1f} "
              f"f_nadir={key[3]:.3f}  → {len(sids)} 案: {', '.join(sids)}")
    if groups:
        print("  提示：同组案例不是相互独立的验证，统计时应按组计权或明确标注。")

    print(f"\n{'='*72}\n问题清单\n{'='*72}")
    if not issues:
        print("未发现不自洽项。")
    else:
        for i in issues:
            print(" ✗", i)
        print(f"\n共 {len(issues)} 项。")

    if args.csv:
        out = Path(args.csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        if audited:
            # 不同 K 层字段集不同，取并集作为表头
            fields: list[str] = []
            seen = set()
            for r in audited:
                for k in r:
                    if k not in seen:
                        seen.add(k)
                        fields.append(k)
            with out.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fields, restval="",
                                   extrasaction="ignore")
                w.writeheader()
                for r in audited:
                    w.writerow(r)
            print(f"\n已写出：{out}")

    return 2 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
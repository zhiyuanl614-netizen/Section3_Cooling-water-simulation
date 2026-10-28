#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metric_audit.py — H=F3 唯一端点下的指标一致性审计
==========================================================
对已生成的 results/*/tables/*_summary.csv 逐案校验指标自洽性，并输出
F3-only 口径下的审计 CSV（即 metric_audit.csv 的唯一事实来源）。

重点检查：
  1. H_count 是否严格等于 n_f3_deenergized（H = 1[F3]，无 F2b/F2a/F1 贡献）
  2. impact_class 是否与 H>0 严格一一对应（N3 ⟺ H>0，N0 ⟺ H=0）
  3. bfi_hard 是否等于 H/30；负荷加权 h_load_ratio 是否越界或与 H 矛盾
  4. 切负荷三量语义：total_shed / shed_peak / ufls 的量级关系
  5. t_first_H 与 observation_window 的时序合理性
  6. 案数完整性：K1=6、K2=15、K3=20、K4=15、K5=6、K6=1，合计 63 案
  7. 求解器数值健康度（仅影响切负荷/频率等次级量；H=F3 为拓扑判定，
     不受收敛性影响）——作为披露项列出，不计入不自洽问题
  8. 指标退化：不同情景是否产生完全相同的电网后果（计权提示）

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

# 案数完整性基线：每层应有案数（scenario_id 前缀）
EXPECTED_COUNTS = {"K1": 6, "K2": 15, "K3": 20, "K4": 15, "K5": 6, "K6": 1}
TOTAL_EXPECTED = sum(EXPECTED_COUNTS.values())


def num(row: dict, key: str, default=None):
    v = row.get(key, "")
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def row_key(r: dict) -> str:
    """去重键：优先 scenario_id；K1 等无 id 行退回 K1-{initial_unit}。"""
    return r.get("scenario_id") or f"K1-{r.get('initial_unit', '?')}"


def collect(results_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(results_dir.glob("*/tables/*_summary.csv")):
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if not r.get("scenario_id") and not r.get("initial_unit"):
                    continue
                r["_src"] = str(path.relative_to(ROOT))
                rows.append(r)
    # 兼容旧版 K1 目录结构（scenarios/*/cascade_summary.csv）
    for path in sorted(results_dir.glob("K1/scenarios/*/cascade_summary.csv")):
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                r["scenario_id"] = r.get("scenario_id") or f"K1-{path.parent.name}"
                r["_src"] = str(path.relative_to(ROOT))
                rows.append(r)
    # 去重：同一情景在多个 *_summary.csv（如 scenario_summary 与 comparison）中
    # 出现时只保留第一个（glob 排序保证 scenario_summary 优先于 comparison）。
    seen: set[str] = set()
    uniq: list[dict] = []
    for r in rows:
        k = row_key(r)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return uniq


def audit_row(r: dict) -> list[str]:
    issues: list[str] = []
    sid = row_key(r)
    H = num(r, "n_bus_hard_failure")
    F3 = num(r, "n_f3_deenergized")
    if H is None:
        return [f"{sid}: 缺少 n_bus_hard_failure（新指标未生成）"]

    # 1. H = 1[F3] 严格相等
    if F3 is not None and abs(H - F3) > 1e-9:
        issues.append(f"{sid}: H={H:.0f} != n_f3_deenergized={F3:.0f}（H 应只等于 F3）")

    # 2. impact_class ⟺ H：N3 ⟺ H>0；N0 ⟺ H=0
    cls = (r.get("impact_class") or "")
    if H > 0 and not cls.startswith("N3"):
        issues.append(f"{sid}: H={H:.0f}>0 但类别为 {cls!r}（应为 N3）")
    if H == 0 and cls.startswith("N3"):
        issues.append(f"{sid}: H=0 却标为 N3（口径错位）")

    # 3. bfi_hard = H/30
    bfi_hard = num(r, "bfi_hard")
    n_bus = num(r, "n_bus_total") or 30.0
    if bfi_hard is not None and abs(bfi_hard - H / n_bus) > 1e-6:
        issues.append(f"{sid}: bfi_hard={bfi_hard:.4f} != H/{n_bus:.0f}={H/n_bus:.4f}")

    # 4. 负荷加权严重度
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

    # 6. t_first_H 时序合理性
    t_first = num(r, "t_first_hard_s")
    win = num(r, "observation_window_h")
    if H > 0 and t_first is None:
        issues.append(f"{sid}: H={H:.0f}>0 但缺少 t_first_hard_s")
    if H == 0 and t_first is not None:
        issues.append(f"{sid}: H=0 却记录了 t_first_hard_s={t_first}")
    if t_first is not None and win is not None:
        tol_s = 1.0  # observation_window_h 4 位小数（小时），量化约 0.36 s
        if t_first > win * 3600.0 + tol_s:
            issues.append(f"{sid}: t_first_H={t_first/3600.0:.4f}h 超出观察窗口 {win:.4f}h")
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
        groups[key].append(row_key(r))
    return {k: v for k, v in groups.items() if len(v) > 1}


def check_completeness(rows: list[dict]) -> list[str]:
    """案数完整性：K1=6、K2=15、K3=20、K4=15、K5=6、K6=1。"""
    issues: list[str] = []
    by_layer: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        sid = row_key(r)
        prefix = sid.split("-")[0]
        by_layer[prefix].add(sid)
    for layer, expected in EXPECTED_COUNTS.items():
        got = len(by_layer.get(layer, set()))
        if got != expected:
            issues.append(
                f"案数完整性: 层 {layer} 应有 {expected} 案，实际 {got} 案"
                f"（多/缺 → 审计覆盖率不完整）")
    got_total = len({row_key(r) for r in rows})
    if got_total != TOTAL_EXPECTED:
        issues.append(f"案数完整性: 去重后总案数 {got_total} != {TOTAL_EXPECTED}")
    return issues


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--csv", default="")
    args = ap.parse_args(argv)
    # 修复相对路径 bug：--results 相对路径一律按项目根解析
    results_dir = Path(args.results)
    if not results_dir.is_absolute():
        results_dir = ROOT / results_dir
    results_dir = results_dir.resolve()

    if not results_dir.exists():
        print(f"[skip] {results_dir} 不存在；先运行 ./run.sh 生成结果", file=sys.stderr)
        return 0

    rows = collect(results_dir)
    if not rows:
        print(f"[skip] {results_dir} 下未找到汇总表", file=sys.stderr)
        return 0

    audited = [r for r in rows if "bfi_hard" in r]
    print(f"共发现 {len(rows)} 条唯一汇总记录；F3-only 口径 {len(audited)} 条")

    issues: list[str] = []
    for r in audited:
        issues.extend(audit_row(r))
    issues.extend(check_completeness(audited))

    print(f"\n{'='*72}\n逐案指标自洽性审计（{len(audited)} 案，H=F3 唯一端点）\n{'='*72}")
    print(f"{'scenario':28s} {'H':>3s} {'F3':>3s} {'H_load':>7s} {'bfi_hard':>9s} "
          f"{'class':>6s} {'t_first_H':>10s} {'conv':>5s}")
    for r in audited:
        print(f"{row_key(r)[:28]:28s} "
              f"{num(r,'n_bus_hard_failure',0):3.0f} "
              f"{num(r,'n_f3_deenergized',0):3.0f} "
              f"{num(r,'h_load_ratio',0):7.3f} "
              f"{num(r,'bfi_hard',0):9.3f} "
              f"{(r.get('impact_class') or '')[:6]:>6s} "
              f"{(('%.3fh'%(num(r,'t_first_hard_s')/3600.0)) if num(r,'t_first_hard_s') is not None else '—'):>10s} "
              f"{(r.get('solver_converged') or '?'):>5s}")

    # 披露项（非不自洽）：求解器数值健康度——H=F3 为拓扑判定不受影响，
    # 但切负荷/频率等次级量以收敛为前提。
    nonconv = [r for r in audited
               if (r.get("solver_converged") or "").lower() in ("false", "0")]
    print(f"\n{'='*72}\n披露项（非不自洽）\n{'='*72}")
    if nonconv:
        print(f"{len(nonconv)} 案未完全收敛：H 为拓扑判定不受影响，但其切负荷/"
              f"频率等次级量为条件性结果：")
        for r in nonconv:
            sid = row_key(r)
            print(f"  {sid}: H={num(r,'n_bus_hard_failure',0):.0f} "
                  f"conv={r.get('solver_converged')} "
                  f"warnings={num(r,'n_singular_warnings',0):.0f}+"
                  f"{num(r,'n_divergence_warnings',0):.0f} "
                  f"stop={r.get('simulation_stop_reason')}")
    else:
        print("全部案例收敛，无披露项。")
    censored = [row_key(r) for r in audited
                if num(r, "n_bus_hard_failure", 0) == 0
                and (num(r, "observation_window_h", 24.0) or 24.0) < 24.0 - 1e-6]
    if censored:
        print(f"删失案（H=0 且观察窗口不足 24 h，未观测到演化终点）：{len(censored)} 案")
        print("  " + ", ".join(censored))

    print(f"\n{'='*72}\n指标退化组（同 H/F3/切负荷/最低频率，电网后果不可区分）\n{'='*72}")
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
        if not out.is_absolute():
            out = ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        if audited:
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

"""生成情景主表 scenario_master.csv（63 案，K1–K6）与分层汇总 group_summary.csv。

本脚本替代已损坏的 build_results_report.py 的**数据段**。后者依赖已被删除的
results/reference/coldend_p5/ 与 results/K6/continuation/，在绘图段崩溃，
无法完整运行；其数据段（load_master / write_master / build_summary）被抽出并
重写于此，使主表重新可复现。

机组归属一律经 src.analysis.unitparse（禁止子串匹配）。

用法：PYTHONPATH=src python3 src/analysis/build_scenario_master.py
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from analysis.unitparse import unit_set  # noqa: E402

OUT = ROOT / "results" / "analysis"

SOURCES = {
    "K1": "results/K1/tables/six_unit_comparison.csv",
    "K2": "results/K2/tables/pairwise_summary.csv",
    "K3": "results/K3/tables/triple_summary.csv",
    "K4": "results/K4/tables/quadruple_summary.csv",
    "K5": "results/K5/tables/quintuple_summary.csv",
    "K6": "results/K6/tables/six_unit_summary.csv",
}


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fnum(row, key, default=0.0):
    try:
        v = row.get(key, "")
        return float(v) if v not in ("", None) else default
    except (TypeError, ValueError):
        return default


def nclass(s):
    m = re.match(r"(N[0-3])", str(s or ""))
    return m.group(1) if m else "NA"


def split_list(text):
    """把 ';' / '+' / ',' 分隔的字段拆成列表（母线号或机组名）。"""
    return [x for x in re.split(r"[;,+\s]+", str(text or "")) if x]


def trip_events(row, k):
    """按时间顺序还原该情景的跳闸事件 [(机组, 时刻h)]。"""
    if k == "K1":
        return [(row["initial_unit"], fnum(row, "initial_trip_h"))]
    out = []
    for e in filter(None, (row.get("initial_trip_events") or "").split(";")):
        m = re.fullmatch(r"([^@]+)@([0-9.]+)h", e)
        if m:
            out.append((m.group(1), float(m.group(2))))
    for e in filter(None, (row.get("other_coldend_trip_events") or "").split(";")):
        m = re.fullmatch(r"([^@]+)@([0-9.]+)s", e)
        if m:
            out.append((m.group(1), float(m.group(2)) / 3600.0))
    return out


def load_master():
    rows = []
    for k, rel in SOURCES.items():
        for raw in read_csv(ROOT / rel):
            if k == "K1":
                # K1 是单机情景，源表按 initial_unit 逐行给出，无 scenario_id。
                units = split_list(raw["initial_unit"])
                sid = f"K1-{'+'.join(units)}"
                count = 1
                censored = ""
            else:
                # 保留源字段顺序（下游按字符串比对），仅用 unit_set 做集合运算
                units = split_list(raw.get("initial_makeup_failure_units", ""))
                sid = raw.get("scenario_id", "")
                count = int(fnum(raw,
                                 "faulted_units_tripped_count_before_stop",
                                 len(units) if k in ("K2", "K3") else 0))
                # K2 / K3 归档批次中，被选机组全部跳完。
                if k in ("K2", "K3"):
                    count = len(units)
                censored = raw.get("faulted_units_not_tripped_before_stop", "")

            status = raw.get("simulation_stop_reason", "")
            events = trip_events(raw, k)
            event_units = list(dict.fromkeys(u for u, _ in events))
            actual_selected = sorted(set(event_units) & unit_set(units))
            first = fnum(raw, "initial_trip_h")
            h = int(fnum(raw, "n_bus_hard_failure"))
            fmin = fnum(raw, "f_nadir_hz", float("nan"))
            uf = fnum(raw, "ufls_shed_mw")
            total = fnum(raw, "total_shed_mw")
            # K1 归档早于 static_grid_shed_mw，从其归档的总减载反推非 UFLS 分量。
            static = (fnum(raw, "static_grid_shed_mw")
                      if raw.get("static_grid_shed_mw") not in ("", None)
                      else max(0.0, total - uf))
            raw_class = raw.get("impact_class", "")

            rows.append({
                "K": k, "scenario_id": sid, "units": "+".join(units),
                "unit_count": len(units), "initial_trip_h": first,
                "trip_order": " → ".join(f"{u}@{t:.4f}h" for u, t in events),
                "trip_count_before_stop": count,
                "actual_trip_units": ";".join(actual_selected),
                "censored_units": censored,
                "hard_stop": int("hard_service_loss" in status),
                "stop_reason": status, "f_nadir_hz": fmin,
                "ufls_shed_mw": uf, "static_grid_shed_mw": static,
                "total_shed_mw": total, "H_hard_buses": h,
                "hard_failure_buses": ";".join(split_list(raw.get("hard_failure_buses", ""))),
                "F3_buses_seen": int(fnum(raw, "n_f3_deenergized")),
                "N_class": nclass(raw_class), "raw_impact_class": raw_class,
                "cooling_tracking_elapsed_h": fnum(raw, "cooling_tracking_elapsed_h"),
                "total_load_mw": fnum(raw, "total_load_mw", 189.2),
                "ufls_triggered": int(uf > 1e-9),
                "source_file": rel,
                "scenario_status": raw.get("scenario_status", "completed"),
            })
    order = {f"K{i}": i for i in range(1, 7)}
    rows.sort(key=lambda r: (order[r["K"]], r["scenario_id"]))
    return rows


def write_csv(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def build_summary(rows):
    out = []
    for k in [f"K{i}" for i in range(1, 7)]:
        rr = [r for r in rows if r["K"] == k]
        if not rr:
            continue
        cls = Counter(r["N_class"] for r in rr)
        h = [r["H_hard_buses"] for r in rr]
        out.append({
            "K": k, "cases": len(rr),
            "H_positive": sum(x > 0 for x in h),
            "tested_share": sum(x > 0 for x in h) / len(rr),
            "H_max": max(h), "H_median": float(np.median(h)),
            "UFLS_cases": sum(r["ufls_triggered"] for r in rr),
            "censored_cases": sum(bool(r["censored_units"]) for r in rr),
            "N0": cls["N0"], "N1": cls["N1"], "N2": cls["N2"], "N3": cls["N3"],
            "freq_min": min(r["f_nadir_hz"] for r in rr),
            "freq_max": max(r["f_nadir_hz"] for r in rr),
            "total_shed_min": min(r["total_shed_mw"] for r in rr),
            "total_shed_max": max(r["total_shed_mw"] for r in rr),
        })
    return out


def main() -> int:
    rows = load_master()
    if len(rows) != 63:
        print(f"警告：预期 63 案，实际 {len(rows)} 案", file=sys.stderr)
    write_csv(OUT / "scenario_master.csv", rows)
    groups = build_summary(rows)
    write_csv(OUT / "group_summary.csv", groups)
    print(f"✓ scenario_master.csv  {len(rows)} 行 × {len(rows[0])} 列")
    print(f"✓ group_summary.csv    {len(groups)} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

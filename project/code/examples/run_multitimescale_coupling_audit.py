"""
Audit the event-aware multi-timescale cold-end/grid exchange.

The cold-end trajectory is kept on its own dynamic time base.  The grid layer
receives a regular macro-step (30/15/5 min in the audit) augmented with the
derating and trip events.  Outputs:

* ``examples/multitimescale_coupling_audit.csv``

With pandapower available, the audit also recomputes the G33 incremental
unserved energy at load x1.15 for each macro-step so the snapshot error can be
reported rather than assumed.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cooling.benchmarks import mechanistic_trajectory  # noqa: E402
from cooling.prototype_500mw import WetRecircPrototype500  # noqa: E402
from grid.coupling import event_aware_time_nodes, integrate_time_series  # noqa: E402
from scenarios import COAL_WR_IDS, load_unit_config, load_unit_params  # noqa: E402
from scenarios.fault_makeup_basin import build_unit_model  # noqa: E402

HORIZON_H = 8.0
# Primary mapped wet unit (bus 33, 652 MW).
PRIMARY_UNIT = "G33"


def _has_time(nodes: list[float], target: float | None) -> bool:
    return target is not None and any(abs(t - target) < 1e-9 for t in nodes)


def _trajectory_rows(scope: str, traj, macro_minutes: list[int]) -> list[dict]:
    reference = traj.delivered_energy_mwh(HORIZON_H)
    rows: list[dict] = []
    for minutes in macro_minutes:
        nodes = event_aware_time_nodes(
            traj, t_end_h=HORIZON_H, macro_step_h=minutes / 60.0
        )
        energy = integrate_time_series(nodes, [traj.p_avail_at(t) for t in nodes])
        rows.append(
            {
                "scope": scope,
                "trajectory": traj.name,
                "macro_step_min": minutes,
                "n_snapshot_nodes": len(nodes),
                "derate_event_included": _has_time(nodes, traj.t_derate_start_h),
                "trip_event_included": _has_time(nodes, traj.t_trip_h),
                "node_integrated_energy_mwh": round(energy, 3),
                "reference_energy_mwh": round(reference, 3),
                "energy_rel_error_pct_vs_reference": round(
                    100.0 * (energy - reference) / reference, 4
                )
                if reference
                else "",
            }
        )
    return rows


def _grid_rows(traj, macro_minutes: list[int]) -> list[dict]:
    try:
        from grid import evaluate_grid_impact  # noqa: PLC0415
    except Exception as exc:  # pandapower is optional
        print(f"grid audit skipped: {exc}")
        return []

    units = load_unit_config()
    healthy = {uid: u.pmax_mw for uid, u in units.items() if uid in COAL_WR_IDS}
    with contextlib.redirect_stderr(io.StringIO()):
        baseline_shed = evaluate_grid_impact({}, load_scale=1.15).shed_load_mw

    rows: list[dict] = []
    for minutes in macro_minutes:
        nodes = event_aware_time_nodes(
            traj, t_end_h=HORIZON_H, macro_step_h=minutes / 60.0
        )
        sheds: list[float] = []
        for t in nodes:
            pavail = dict(healthy)
            pavail[PRIMARY_UNIT] = traj.p_avail_at(t)
            with contextlib.redirect_stderr(io.StringIO()):
                sheds.append(evaluate_grid_impact(pavail, load_scale=1.15).shed_load_mw)
        total = integrate_time_series(nodes, sheds)
        incremental = integrate_time_series(
            nodes, [max(0.0, s - baseline_shed) for s in sheds]
        )
        rows.append(
            {
                "scope": f"IEEE39_{PRIMARY_UNIT}_grid_load_x1.15",
                "trajectory": traj.name,
                "macro_step_min": minutes,
                "n_snapshot_nodes": len(nodes),
                "derate_event_included": _has_time(nodes, traj.t_derate_start_h),
                "trip_event_included": _has_time(nodes, traj.t_trip_h),
                "unserved_energy_0_8h_mwh": round(total, 3),
                "incremental_unserved_energy_0_8h_mwh": round(incremental, 3),
            }
        )
    if rows:
        finest = rows[-1]["incremental_unserved_energy_0_8h_mwh"]
        for row in rows:
            row["incremental_energy_diff_pct_vs_5min"] = round(
                100.0 * (row["incremental_unserved_energy_0_8h_mwh"] - finest) / finest,
                4,
            )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-grid", action="store_true", help="skip the optional DC-OPF audit")
    args = ap.parse_args()

    proto_traj = mechanistic_trajectory(WetRecircPrototype500(), strategy="ride_down")
    units = load_unit_config()
    params = load_unit_params("baseline")
    mapped_traj = mechanistic_trajectory(
        build_unit_model(units[PRIMARY_UNIT], params=params), strategy="ride_down"
    )

    rows: list[dict] = []
    rows.extend(_trajectory_rows("500MW_prototype", proto_traj, [30, 15, 5, 1]))
    rows.extend(
        _trajectory_rows(f"IEEE39_{PRIMARY_UNIT}_cold_end", mapped_traj, [30, 15, 5, 1])
    )
    if not args.no_grid:
        rows.extend(_grid_rows(mapped_traj, [30, 15, 5]))

    out_csv = ROOT / "examples" / "multitimescale_coupling_audit.csv"
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print("=== multi-timescale exchange audit (synthetic case) ===")
    for row in rows:
        if row["scope"].endswith("grid_load_x1.15"):
            print(
                f"{row['scope']:28s} macro={row['macro_step_min']:>2.0f} min "
                f"nodes={row['n_snapshot_nodes']:>3d} "
                f"incremental={row['incremental_unserved_energy_0_8h_mwh']:9.1f} MWh "
                f"diff_vs_5min={row['incremental_energy_diff_pct_vs_5min']:+.3f}%"
            )
        elif row["macro_step_min"] in (30, 5, 1):
            print(
                f"{row['scope']:28s} macro={row['macro_step_min']:>2.0f} min "
                f"nodes={row['n_snapshot_nodes']:>3d} "
                f"energy_error={row['energy_rel_error_pct_vs_reference']:+.3f}%"
            )
    print(f"\nwrote {out_csv} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

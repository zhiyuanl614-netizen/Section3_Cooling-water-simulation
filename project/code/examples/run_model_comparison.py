"""
Compare simplified outage assumptions with mechanism-resolved trajectories.

Outputs:
* ``examples/model_comparison.csv`` -- 500 MW cold-end metrics and, when
  pandapower is available, G33/IEEE-39 grid metrics at load x1.15.  Grid
  snapshots use a 15 min macro-step augmented with trajectory events; a
  separate audit shows this is within 0.1% of the 5 min exchange for the
  reference ride-down trajectory.

The simplified trajectories are comparators, not plant models.  The grid
calculation is a sequence of DC-OPF snapshots; unserved energy is obtained by
trapezoidal integration over 0-8 h and reported both as total shed energy and
as the increment over the same-load no-fault case.
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

from cooling.benchmarks import build_benchmark_trajectories  # noqa: E402
from grid.coupling import event_aware_time_nodes  # noqa: E402
from cooling.prototype_500mw import WetRecircPrototype500  # noqa: E402
from scenarios.fault_makeup_basin import build_unit_model  # noqa: E402
from scenarios import COAL_WR_IDS, load_unit_config, load_unit_params  # noqa: E402

# Primary mapped wet unit (bus 33, 652 MW): the larger of the two mapped units.
PRIMARY_UNIT = "G33"


def _trapz(times: list[float], values: list[float]) -> float:
    return sum(
        0.5 * (values[i - 1] + values[i]) * (times[i] - times[i - 1])
        for i in range(1, len(times))
    )


def _grid_metrics(trajectories, model) -> dict[str, dict[str, float]]:
    try:
        from grid import evaluate_grid_impact  # noqa: PLC0415
    except Exception as exc:  # pandapower is optional
        print(f"grid comparison skipped: {exc}")
        return {}

    units = load_unit_config()
    healthy = {uid: u.pmax_mw for uid, u in units.items() if uid in COAL_WR_IDS}
    with contextlib.redirect_stderr(io.StringIO()):
        baseline = evaluate_grid_impact({}, load_scale=1.15)
    baseline_shed = baseline.shed_load_mw
    out: dict[str, dict[str, float]] = {}
    for traj in trajectories:
        times = event_aware_time_nodes(traj, t_end_h=8.0, macro_step_h=0.25)
        sheds: list[float] = []
        loadings: list[float] = []
        for t in times:
            pavail = dict(healthy)
            pavail[PRIMARY_UNIT] = traj.p_avail_at(t)
            with contextlib.redirect_stderr(io.StringIO()):
                res = evaluate_grid_impact(pavail, load_scale=1.15)
            sheds.append(res.shed_load_mw)
            loadings.append(res.max_line_loading_percent)
        total_energy = _trapz(times, sheds)
        incremental_rate = [max(0.0, s - baseline_shed) for s in sheds]
        out[traj.name] = {
            "grid_scope": f"{PRIMARY_UNIT}_load_x1.15",
            "baseline_shed_mw": round(baseline_shed, 3),
            "shed_at_3h_mw": round(sheds[times.index(3.0)], 3),
            "shed_at_5h_mw": round(sheds[times.index(5.0)], 3),
            "shed_at_8h_mw": round(sheds[-1], 3),
            "unserved_energy_0_8h_mwh": round(total_energy, 2),
            "incremental_unserved_energy_0_8h_mwh": round(_trapz(times, incremental_rate), 2),
            "max_line_loading_percent_max": round(max(loadings), 2),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-grid", action="store_true", help="skip the optional DC-OPF comparison")
    args = ap.parse_args()

    rows: list[dict] = []
    proto = WetRecircPrototype500()
    proto_trajectories = build_benchmark_trajectories(proto)
    reference_energy = next(
        t.delivered_energy_mwh() for t in proto_trajectories if t.name == "mechanistic_ride_down"
    )
    for traj in proto_trajectories:
        row = {"scope": "500MW_prototype", **traj.metrics()}
        row["delivered_energy_vs_mechanistic"] = round(
            traj.delivered_energy_mwh() / reference_energy, 4
        ) if reference_energy else None
        rows.append(row)

    if not args.no_grid:
        units = load_unit_config()
        params = load_unit_params("baseline")
        mapped_model = build_unit_model(units[PRIMARY_UNIT], params=params)
        mapped_trajectories = build_benchmark_trajectories(mapped_model)
        grid = _grid_metrics(mapped_trajectories, mapped_model)
        metrics_by_name = {t.name: t.metrics() for t in mapped_trajectories}
        for name, values in grid.items():
            rows.append({
                "scope": f"IEEE39_{PRIMARY_UNIT}_grid",
                **metrics_by_name[name],
                **values,
            })

    out_csv = ROOT / "examples" / "model_comparison.csv"
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print("=== cold-end benchmark comparison (500 MW prototype) ===")
    for row in rows:
        if row["scope"] != "500MW_prototype":
            continue
        trip = "--" if row["t_trip_h"] is None else f"{row['t_trip_h']:.3f}"
        print(
            f"{row['benchmark']:28s} trip={trip:>7s} h  "
            f"E0-8={row['delivered_energy_0_8h_mwh']:8.1f} MWh  "
            f"P@3h={row['p_at_3h_mw']:6.1f} MW"
        )
    grid_rows = [r for r in rows if r["scope"] == f"IEEE39_{PRIMARY_UNIT}_grid"]
    if grid_rows:
        print(
            f"\n=== IEEE-39 {PRIMARY_UNIT} grid comparison (load x1.15, synthetic case) ==="
        )
        for row in grid_rows:
            print(
                f"{row['benchmark']:28s} shed@3h={row['shed_at_3h_mw']:7.1f} MW  "
                f"incremental E={row['incremental_unserved_energy_0_8h_mwh']:8.1f} MWh"
            )
    print(f"\nwrote {out_csv} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

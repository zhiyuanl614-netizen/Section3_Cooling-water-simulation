"""
Probabilistic uncertainty and global sensitivity for the synthetic case.

The sampled ranges are transparent reference-template scenario ranges, not
plant posteriors.  Outputs are written to:

* ``examples/probabilistic_uncertainty_samples.csv``
* ``examples/probabilistic_uncertainty_summary.json``
* ``examples/global_sensitivity_morris.csv``
* ``examples/global_sensitivity_sobol.csv``

The dynamic model is evaluated with a 10 s step for these ensembles.  At the
reference point this reproduces the 1 s trip time to within one minute.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cooling.prototype_500mw import WetRecircPrototype500  # noqa: E402
from cooling.uncertainty import (  # noqa: E402
    Morris_sensitivity,
    default_uncertainty_parameters,
    run_monte_carlo,
    sobol_sensitivity,
    summarise_monte_carlo,
)


def _write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _top(rows: list[dict], output: str, key: str, n: int = 5) -> list[dict]:
    selected = [r for r in rows if r["output"] == output]
    return sorted(selected, key=lambda r: abs(float(r[key])), reverse=True)[:n]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-mc", type=int, default=384)
    ap.add_argument("--sobol-n", type=int, default=256)
    ap.add_argument("--Morris-trajectories", type=int, default=12)
    ap.add_argument("--seed", type=int, default=20261013)
    args = ap.parse_args()
    if args.sobol_n <= 0 or (args.sobol_n & (args.sobol_n - 1)) != 0:
        # The scrambled-Sobol design requires a power of two for exact
        # ``random_base2`` balance; retain the convention for auditability.
        print("warning: --sobol-n is conventionally a power of two", file=sys.stderr)

    base = WetRecircPrototype500()
    specs = default_uncertainty_parameters(base)

    print(f"Monte Carlo / LHS: {args.n_mc} samples")
    mc_rows = run_monte_carlo(base, specs, n_samples=args.n_mc, seed=args.seed)
    summary = summarise_monte_carlo(mc_rows)
    summary["case_status"] = "synthetic_reference_template_not_site_calibrated"
    summary["parameter_distributions"] = [asdict(s) for s in specs]
    summary["dynamic_step_s"] = 10.0

    print(f"Morris screening: {args.Morris_trajectories} trajectories")
    Morris_rows = Morris_sensitivity(
        base, specs, n_trajectories=args.Morris_trajectories, seed=args.seed
    )
    print(f"Sobol/Saltelli: base_n={args.sobol_n}, parameters={len(specs)}")
    sobol_rows = sobol_sensitivity(base, specs, base_n=args.sobol_n, seed=17, bootstrap_replicates=200)

    samples_csv = ROOT / "examples" / "probabilistic_uncertainty_samples.csv"
    summary_json = ROOT / "examples" / "probabilistic_uncertainty_summary.json"
    Morris_csv = ROOT / "examples" / "global_sensitivity_morris.csv"
    sobol_csv = ROOT / "examples" / "global_sensitivity_sobol.csv"
    _write_csv(samples_csv, mc_rows)
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_csv(Morris_csv, Morris_rows)
    _write_csv(sobol_csv, sobol_rows)

    trip = summary["outputs"]["t_trip_h"]
    energy = summary["outputs"]["delivered_energy_0_8h_mwh"]
    print("\n=== probabilistic summary (synthetic scenario ranges) ===")
    print(
        f"trip time h: mean={trip['mean']:.3f}, sd={trip['sd']:.3f}, "
        f"p05={trip['p05']:.3f}, p50={trip['p50']:.3f}, p95={trip['p95']:.3f}"
    )
    print(
        f"delivered energy 0-8h MWh: mean={energy['mean']:.1f}, "
        f"p05={energy['p05']:.1f}, p50={energy['p50']:.1f}, p95={energy['p95']:.1f}"
    )
    print(f"trip mechanisms: {summary['mechanisms']}")

    print("\nTop Sobol total-order parameters for trip time:")
    for row in _top(sobol_rows, "t_trip_h", "sobol_total_order"):
        print(f"  {row['parameter']:32s} ST={row['sobol_total_order']:.3f} S1={row['sobol_first_order']:.3f}")
    print("\nTop Sobol total-order parameters for delivered energy:")
    for row in _top(sobol_rows, "delivered_energy_0_8h_mwh", "sobol_total_order"):
        print(f"  {row['parameter']:32s} ST={row['sobol_total_order']:.3f} S1={row['sobol_first_order']:.3f}")

    print(f"\nwrote {samples_csv}")
    print(f"wrote {summary_json}")
    print(f"wrote {Morris_csv}")
    print(f"wrote {sobol_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

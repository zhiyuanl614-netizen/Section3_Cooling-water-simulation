"""Run framework v0.3 cold-end → IEEE39 cascade matrix and write a summary CSV."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scenarios.framework_coupling import (  # noqa: E402
    run_framework_matrix,
    write_summary_csv,
)

OUT = ROOT / "examples" / "framework_cascade_coupling_summary.csv"

# Minimal publishable matrix (S + G + key controls). Full registry remains loadable.
DEFAULT_IDS = [
    "S0",
    "S1a",
    "S1b",
    "S2",
    "S2qs",
    "S3a",
    "S3b",
    "S3a_hold",
    "S4",
    "C1_hold",
    "G1",
    "G2",
    "G3",
    "G4",
]


def main() -> None:
    results = run_framework_matrix(DEFAULT_IDS)
    path = write_summary_csv(results, OUT)
    print(f"wrote {path}")
    print(
        f"{'ID':<10} {'mech':<24} {'t_min':>8} {'P_end':>8} "
        f"{'casc':>5} {'n_line':>6}"
    )
    for r in results:
        row = r.summary_row()
        tmin = row["t_trip_min"]
        tmin_s = "" if tmin is None else f"{tmin:.2f}"
        casc = row["cascade_triggered"]
        casc_s = "" if casc is None else str(casc)
        nline = row["n_lines_removed"]
        nline_s = "" if nline is None else str(nline)
        print(
            f"{row['scenario_id']:<10} {row['trip_mechanism']:<24} "
            f"{tmin_s:>8} {row['p_final_mw']:>8.1f} {casc_s:>5} {nline_s:>6}"
        )


if __name__ == "__main__":
    main()

"""Smoke-check U1 sensitivity outputs exist and encode A4 claims."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "examples" / "u1_sensitivity_summary.csv"


def test_u1_csv_exists_with_a4_rows():
    assert CSV.is_file()
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    assert len(rows) >= 20
    params = {r["param"] for r in rows}
    assert "tower_characteristic_mult" in params
    assert "condenser_cleanliness" in params
    cases = {r["case_id"] for r in rows}
    assert {"S1a", "S2", "S3a", "G2_both_trip", "G1_only_33_trip"} <= cases


def test_dual_trip_cascades_but_derate_does_not():
    rows = {r["case_id"]: r for r in csv.DictReader(CSV.open(encoding="utf-8"))}
    assert rows["G2_both_trip"]["cascade_triggered"] == "True"
    assert int(rows["G2_both_trip"]["n_lines_removed"]) == 13
    assert rows["G2_both_S3a_derate"]["cascade_triggered"] == "False"
    assert rows["G1_only_33_trip"]["cascade_triggered"] == "False"

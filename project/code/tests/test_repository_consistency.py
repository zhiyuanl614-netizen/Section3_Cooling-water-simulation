"""Repository-level guards: docs must describe what the code does.

These tests exist because the original defect class was *documentation drift*:
a hand-maintained calibrated table and an undocumented parameter that the code
silently depended on.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_plant_calibration_contract_is_documented():
    """Ghost parameters are out; the calibration contract must be explicit."""
    doc = (ROOT / "docs" / "RESEARCH_FRAMEWORK.md").read_text(encoding="utf-8")
    assert "reference_template_not_site_measured" in doc
    assert "tower_characteristic_mult" in doc
    assert "me_design" not in doc
    registry = list(csv.DictReader(open(ROOT / "data" / "parameter_registry.csv", encoding="utf-8")))
    assert registry and all(r["calibration_status"] == "reference_template_not_site_measured" for r in registry)


def test_generic_parameterization_is_the_current_route():
    """No-history route: literature/standard anchors, not plant fitting."""
    doc = (ROOT / "docs" / "GENERIC_PARAMETERIZATION.md").read_text(encoding="utf-8")
    assert "文献与标准锚定的通用参数标定" in doc
    assert "不是当前研究成立的前提" in doc
    registry = list(csv.DictReader(open(ROOT / "data" / "parameter_registry.csv", encoding="utf-8")))
    assert registry and all(
        r["generic_anchor_type"] and r["generic_anchor_note"] and r["sensitivity_treatment"]
        for r in registry
    )
    framework = (ROOT / "docs" / "RESEARCH_FRAMEWORK.md").read_text(encoding="utf-8")
    assert "cooling_grid_causal_chain.svg" in framework


def test_coc_convention_is_documented():
    """P6: the cycles-of-concentration convention must be written down."""
    doc = (ROOT / "docs" / "RESEARCH_FRAMEWORK.md").read_text(encoding="utf-8")
    assert "CoC" in doc and "M/(B+D)" in doc.replace(" ", "")


def test_calibrated_table_is_in_sync_with_the_code():
    """The exported table must be reproducible from the model (no drift)."""
    out = ROOT / "tests" / "_tmp_calibrated.csv"
    try:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "export_calibrated_parameters.py"),
                "--out",
                str(out),
            ],
            check=True,
            capture_output=True,
        )
        shipped = list(csv.DictReader(open(ROOT / "data" / "calibrated_unit_parameters.csv", encoding="utf-8")))
        fresh = list(csv.DictReader(open(out, encoding="utf-8")))
        assert [r["gen_id"] for r in shipped] == [r["gen_id"] for r in fresh]
        for a, b in zip(shipped, fresh):
            assert a == b, f"calibrated table drifted for {a['gen_id']}"
    finally:
        out.unlink(missing_ok=True)


def test_cold_end_scope_is_the_two_mapped_units():
    """Buses 33 and 34 are the mapped wet-recirculating units (manuscript Sec. 3.2)."""
    rows = list(csv.DictReader(open(ROOT / "data" / "ieee39_unit_config.csv", encoding="utf-8")))
    modelled = [r["gen_id"] for r in rows if r["include_cold_end"] == "1"]
    assert sorted(modelled) == ["G33", "G34"]
    assert all(r["cooling_type"] == "wet_recirc" for r in rows if r["include_cold_end"] == "1")
    buses = {r["gen_id"]: int(r["bus"]) for r in rows}
    assert (buses["G33"], buses["G34"]) == (33, 34)


def test_mapped_unit_capacities_follow_matpower_case39():
    """Generator ratings are the MATPOWER case39 Pmax values, not round numbers."""
    rows = list(csv.DictReader(open(ROOT / "data" / "ieee39_unit_config.csv", encoding="utf-8")))
    ratings = {r["gen_id"]: float(r["pmax_mw"]) for r in rows}
    assert ratings["G33"] == pytest.approx(652.0)
    assert ratings["G34"] == pytest.approx(508.0)
    assert sum(ratings.values()) == pytest.approx(7367.0)
    assert sum(float(r["pmax_mw"]) for r in rows if r["include_cold_end"] == "0") == pytest.approx(6207.0)


def test_revision_log_records_this_work():
    doc = (ROOT / "docs" / "RESEARCH_FRAMEWORK.md").read_text(encoding="utf-8")
    assert "2026-10-13" in doc


def test_readme_documents_the_new_entry_points():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for entry in (
        "examples/run_prototype_demo.py",
        "examples/run_timeseries_demo.py",
        "examples/run_sensitivity_demo.py",
        "examples/run_grid_impact_demo.py",
    ):
        assert entry in readme, f"{entry} missing from README"

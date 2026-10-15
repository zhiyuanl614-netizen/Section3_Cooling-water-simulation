"""
Fit selected cold-end parameters against plant historian data supplied by
the user.  No example plant measurements are bundled with this repository.

Example (after replacing the template values with a real unit model):

    python tools/calibrate_from_historian.py \
        --data path/to/historian.csv \
        --gen-id G34 --package baseline \
        --params tower_characteristic_mult,condenser_cleanliness,evap_heat_fraction \
        --out calibration_result.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cooling.calibration import calibrate_model, load_historian_csv  # noqa: E402
from cooling.prototype_500mw import WetRecircPrototype500  # noqa: E402
from scenarios.fault_makeup_basin import build_unit_model, load_unit_config  # noqa: E402
from scenarios.unit_params import load_unit_params  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", required=True, help="historian CSV supplied by the plant/researcher")
    ap.add_argument("--params", required=True, help="comma-separated registered parameter names")
    ap.add_argument("--gen-id", default=None, help="optional IEEE39 unit id (G33/G34)")
    ap.add_argument("--package", default="baseline")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = load_historian_csv(args.data)
    if args.gen_id:
        units = load_unit_config()
        model = build_unit_model(units[args.gen_id], params=load_unit_params(args.package))
    else:
        model = WetRecircPrototype500()

    params = [p.strip() for p in args.params.split(",") if p.strip()]
    result = calibrate_model(model, rows, params)
    fitted = {p: float(getattr(result.model, p)) for p in params}
    payload = {
        "gen_id": args.gen_id or model.gen_id,
        "parameters": params,
        "fitted_values": fitted,
        "initial_metrics": result.initial_metrics,
        "final_metrics": result.final_metrics,
        "history": result.history,
        "warning": "Validate on a separate historian period before accepting fitted values.",
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

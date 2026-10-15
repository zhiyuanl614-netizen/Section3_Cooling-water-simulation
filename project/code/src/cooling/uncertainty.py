"""Probabilistic uncertainty and global sensitivity for the synthetic case.

The distributions in this module are transparent *scenario distributions*
for a synthetic IEEE-39 demonstration.  They are not posterior distributions
and must not be described as plant-measurement uncertainty.  Their purpose is
to propagate plausible reference-template ranges through the mechanistic
model and identify which inputs control the outputs.

Monte Carlo and Morris use only the standard library.  Sobol sampling
prefers SciPy's scrambled Sobol sequence when the optional ``analysis``
extra is installed and otherwise falls back to independent LHS matrices.
Dynamic evaluations use a 10 s integration step by default; for the
reference model this changes the trip time by less than one minute relative
to the 1 s calculation while making Saltelli/Sobol sampling practical.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from typing import Any, Iterable, Sequence

from .dynamics import TimeseriesResult, simulate_makeup_interrupt
from .prototype_500mw import WetRecircPrototype500

OUTPUTS = (
    "initial_p_mw",
    "initial_pb_kpa",
    "t_derate_start_h",
    "t_trip_h",
    "p_at_3h_mw",
    "delivered_energy_0_8h_mwh",
)


@dataclass(frozen=True)
class UncertaintyParameter:
    """One uncertain input in normalised [0, 1] sampling space."""

    name: str
    lower: float
    upper: float
    destination: str = "model"  # "model" or "dynamics"
    unit: str = "-"
    rationale: str = "synthetic scenario range"

    def map_value(self, unit_value: float) -> float:
        if not 0.0 <= unit_value <= 1.0:
            raise ValueError("unit_value must lie in [0, 1]")
        return self.lower + unit_value * (self.upper - self.lower)


def default_uncertainty_parameters(
    base: WetRecircPrototype500,
) -> list[UncertaintyParameter]:
    """Reference-template scenario ranges around one base model.

    Ranges intentionally span the previously used equipment band and the
    one-at-a-time sensitivity ranges.  Protection settings are included as
    epistemic scenario variables to expose non-identifiability; in a plant
    study they should be entered from the setting sheet, not sampled.
    """
    return [
        UncertaintyParameter("tower_characteristic_mult", 0.85, 1.15, rationale="tower condition / NTU uncertainty"),
        UncertaintyParameter("condenser_cleanliness", 0.88, 1.06, rationale="condenser fouling/cleanliness range"),
        UncertaintyParameter(
            "basin_area_m2", 0.85 * base.basin_area_m2, 1.15 * base.basin_area_m2,
            unit="m2", rationale="±15% synthetic inventory-geometry range",
        ),
        UncertaintyParameter("evap_heat_fraction", 0.74, 0.90, rationale="evaporative heat-share range"),
        UncertaintyParameter("cycles_of_concentration", 3.0, 5.0, rationale="water-chemistry operating range"),
        UncertaintyParameter("pump_npshr_design_m", 6.0, 10.0, unit="m", rationale="pump-curve uncertainty range"),
        UncertaintyParameter(
            "operator_shed_start_level_m", 1.5, 2.5,
            unit="m", rationale="SOP action-level scenario range",
        ),
        UncertaintyParameter("p_min_tech_frac", 0.35, 0.45, rationale="technical-minimum scenario range"),
        UncertaintyParameter(
            "basin_level_trip_m", 0.9, 1.1,
            unit="m", rationale="level-switch setting tolerance scenario",
        ),
        UncertaintyParameter("pb_trip_kpa", 12.0, 20.0, unit="kPa", rationale="low-vacuum setting scenario range"),
        UncertaintyParameter(
            "twb_op_c", 18.0, 30.0, destination="dynamics",
            unit="degC", rationale="operating wet-bulb scenario range",
        ),
        UncertaintyParameter(
            "airflow_ratio", 0.90, 1.10, destination="dynamics",
            rationale="tower airflow/fan-state scenario range",
        ),
    ]


def apply_unit_sample(
    base: WetRecircPrototype500,
    parameters: Sequence[UncertaintyParameter],
    unit_values: Sequence[float],
) -> tuple[WetRecircPrototype500, dict[str, Any]]:
    """Map one normalised sample to a model and dynamic kwargs."""
    if len(parameters) != len(unit_values):
        raise ValueError("parameter/value length mismatch")
    model_updates: dict[str, float] = {}
    dyn_kwargs: dict[str, Any] = {}
    for spec, u in zip(parameters, unit_values):
        value = spec.map_value(float(u))
        if spec.destination == "model":
            model_updates[spec.name] = value
        elif spec.destination == "dynamics":
            dyn_kwargs[spec.name] = value
        else:  # pragma: no cover - defensive
            raise ValueError(f"unknown destination {spec.destination!r}")
    return replace(base, **model_updates), dyn_kwargs


def _integrate_energy(ts: TimeseriesResult, horizon_h: float = 8.0) -> float:
    energy = 0.0
    for i in range(1, len(ts.t_h)):
        t0, t1 = ts.t_h[i - 1], ts.t_h[i]
        if t0 >= horizon_h:
            break
        end = min(t1, horizon_h)
        p0 = ts.p_avail_mw[i - 1]
        if end < t1:
            p1 = ts.p_avail_at(end)
        else:
            p1 = ts.p_avail_mw[i]
        energy += 0.5 * (p0 + p1) * (end - t0)
        if end >= horizon_h:
            break
    return energy


def evaluate_unit_sample(
    base: WetRecircPrototype500,
    parameters: Sequence[UncertaintyParameter],
    unit_values: Sequence[float],
    *,
    dt_s: float = 10.0,
    t_max_h: float = 12.0,
    strategy: str = "ride_down",
) -> dict[str, Any]:
    """Evaluate all uncertainty outputs for one normalised sample."""
    model, dyn_kwargs = apply_unit_sample(base, parameters, unit_values)
    initial = model.evaluate(
        twb_c=dyn_kwargs.get("twb_op_c", model.twb_ref_c),
        airflow_ratio=dyn_kwargs.get("airflow_ratio", 1.0),
    )
    ts = simulate_makeup_interrupt(
        model,
        strategy=strategy,  # type: ignore[arg-type]
        dt_s=dt_s,
        sample_every_s=60.0,
        t_max_h=t_max_h,
        **dyn_kwargs,
    )
    censored = ts.trip is None
    return {
        "initial_p_mw": float(initial.p_avail_mw),
        "initial_pb_kpa": float(initial.backpressure_kpa),
        "t_derate_start_h": float(ts.t_derate_start_h if ts.t_derate_start_h is not None else t_max_h),
        "derate_censored": bool(ts.t_derate_start_h is None),
        "t_trip_h": float(ts.t_trip_h if ts.t_trip_h is not None else t_max_h),
        "trip_censored": bool(censored),
        "trip_mechanism": ts.trip_mechanism,
        "p_at_3h_mw": float(ts.p_avail_at(3.0)),
        "delivered_energy_0_8h_mwh": float(_integrate_energy(ts, 8.0)),
    }


# --------------------------------------------------------------------------
# Sampling helpers
# --------------------------------------------------------------------------

def _latin_hypercube(n: int, k: int, seed: int) -> list[list[float]]:
    rng = random.Random(seed)
    columns: list[list[float]] = []
    for _ in range(k):
        values = [(i + rng.random()) / n for i in range(n)]
        rng.shuffle(values)
        columns.append(values)
    return [[columns[j][i] for j in range(k)] for i in range(n)]


def _radical_inverse(index: int, prime: int) -> float:
    inv = 1.0 / prime
    factor = inv
    result = 0.0
    while index:
        result += factor * (index % prime)
        index //= prime
        factor *= inv
    return result


_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89)


def _halton(n: int, k: int, *, start: int = 17) -> list[list[float]]:
    if k > len(_PRIMES):
        raise ValueError("too many dimensions for the built-in Halton sequence")
    return [
        [_radical_inverse(start + i, _PRIMES[j]) for j in range(k)]
        for i in range(n)
    ]


def run_monte_carlo(
    base: WetRecircPrototype500,
    parameters: Sequence[UncertaintyParameter] | None = None,
    *,
    n_samples: int = 384,
    seed: int = 20261013,
    dt_s: float = 10.0,
) -> list[dict[str, Any]]:
    """Latin-hypercube propagation of the synthetic scenario distributions."""
    specs = list(parameters or default_uncertainty_parameters(base))
    samples = _latin_hypercube(n_samples, len(specs), seed)
    rows: list[dict[str, Any]] = []
    for i, unit_values in enumerate(samples):
        result = evaluate_unit_sample(base, specs, unit_values, dt_s=dt_s)
        row: dict[str, Any] = {"sample_id": i}
        for spec, u in zip(specs, unit_values):
            row[spec.name] = spec.map_value(float(u))
        row.update(result)
        rows.append(row)
    return rows


def quantile(values: Sequence[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return ordered[0]
    pos = q * (len(ordered) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[int(pos)]
    return ordered[lo] * (hi - pos) + ordered[hi] * (pos - lo)


def summarise_monte_carlo(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Means, standard deviations and 5/50/95% quantiles for each output."""
    rows = list(rows)
    summary: dict[str, Any] = {"n_samples": len(rows), "outputs": {}, "mechanisms": {}}
    for output in OUTPUTS:
        values = [float(r[output]) for r in rows]
        mean = sum(values) / len(values)
        var = sum((v - mean) ** 2 for v in values) / max(len(values) - 1, 1)
        summary["outputs"][output] = {
            "mean": mean,
            "sd": math.sqrt(var),
            "p05": quantile(values, 0.05),
            "p50": quantile(values, 0.50),
            "p95": quantile(values, 0.95),
            "min": min(values),
            "max": max(values),
        }
    for row in rows:
        mech = str(row["trip_mechanism"])
        summary["mechanisms"][mech] = summary["mechanisms"].get(mech, 0) + 1
    total = max(len(rows), 1)
    summary["mechanisms"] = {
        k: {"n": v, "probability": v / total}
        for k, v in sorted(summary["mechanisms"].items())
    }
    summary["trip_censored_probability"] = sum(bool(r["trip_censored"]) for r in rows) / total
    summary["derate_censored_probability"] = sum(bool(r["derate_censored"]) for r in rows) / total
    return summary


# --------------------------------------------------------------------------
# Global sensitivity
# --------------------------------------------------------------------------

def Morris_sensitivity(
    base: WetRecircPrototype500,
    parameters: Sequence[UncertaintyParameter] | None = None,
    *,
    n_trajectories: int = 12,
    seed: int = 20261013,
    delta: float = 0.25,
    dt_s: float = 10.0,
) -> list[dict[str, Any]]:
    """Morris elementary-effects screening in normalised parameter space."""
    specs = list(parameters or default_uncertainty_parameters(base))
    rng = random.Random(seed)
    effects: dict[str, dict[str, list[float]]] = {
        output: {spec.name: [] for spec in specs} for output in OUTPUTS
    }
    for _ in range(n_trajectories):
        x = [0.15 + 0.70 * rng.random() for _ in specs]
        order = list(range(len(specs)))
        rng.shuffle(order)
        current = evaluate_unit_sample(base, specs, x, dt_s=dt_s)
        for j in order:
            y = list(x)
            step = delta if y[j] + delta <= 1.0 else -delta
            y[j] += step
            nxt = evaluate_unit_sample(base, specs, y, dt_s=dt_s)
            for output in OUTPUTS:
                effects[output][specs[j].name].append(
                    (float(nxt[output]) - float(current[output])) / step
                )
            x, current = y, nxt

    rows: list[dict[str, Any]] = []
    for output in OUTPUTS:
        for spec in specs:
            vals = effects[output][spec.name]
            mu = sum(vals) / len(vals)
            mu_star = sum(abs(v) for v in vals) / len(vals)
            sd = math.sqrt(sum((v - mu) ** 2 for v in vals) / max(len(vals) - 1, 1))
            rows.append({
                "output": output,
                "parameter": spec.name,
                "mu_per_full_range": mu,
                "mu_star_per_full_range": mu_star,
                "sigma_per_full_range": sd,
                "n_effects": len(vals),
            })
    return rows


def sobol_sensitivity(
    base: WetRecircPrototype500,
    parameters: Sequence[UncertaintyParameter] | None = None,
    *,
    base_n: int = 128,
    seed: int = 17,
    dt_s: float = 10.0,
    bootstrap_replicates: int = 0,
) -> list[dict[str, Any]]:
    """Saltelli first/total-order indices from a scrambled Sobol design.

    If SciPy is available, A/B are split from a ``2k``-dimensional scrambled
    Sobol sequence (``n`` should be a power of two).  Otherwise the function
    falls back to independent Latin-hypercube A/B matrices; first-order
    estimates from the fallback should be interpreted more cautiously.

    Estimators follow the common Saltelli/Jansen forms.  Small negative
    first-order estimates can occur at finite sample size and are retained
    in the CSV so convergence can be audited rather than hidden.
    """
    specs = list(parameters or default_uncertainty_parameters(base))
    k = len(specs)
    a: list[list[float]]
    b: list[list[float]]
    if base_n > 0 and (base_n & (base_n - 1)) == 0:
        try:
            from scipy.stats.qmc import Sobol  # noqa: PLC0415

            engine = Sobol(d=2 * k, scramble=True, seed=seed)
            design = engine.random_base2(int(math.log2(base_n)))
            a = design[:, :k].tolist()
            b = design[:, k:].tolist()
        except ImportError:  # pragma: no cover - SciPy is an optional extra
            a = _latin_hypercube(base_n, k, seed)
            b = _latin_hypercube(base_n, k, seed + 99991)
    else:
        a = _latin_hypercube(base_n, k, seed)
        b = _latin_hypercube(base_n, k, seed + 99991)

    def evaluate(samples: Sequence[Sequence[float]]) -> dict[str, list[float]]:
        out: dict[str, list[float]] = {output: [] for output in OUTPUTS}
        for sample in samples:
            result = evaluate_unit_sample(base, specs, list(sample), dt_s=dt_s)
            for output in OUTPUTS:
                out[output].append(float(result[output]))
        return out

    ya = evaluate(a)
    yb = evaluate(b)
    yab: list[dict[str, list[float]]] = []
    for j in range(k):
        ab = []
        for i in range(base_n):
            sample = list(b[i])
            sample[j] = a[i][j]
            ab.append(sample)
        yab.append(evaluate(ab))
    rows: list[dict[str, Any]] = []
    for output in OUTPUTS:
        a_vals = ya[output]
        b_vals = yb[output]
        pooled = a_vals + b_vals
        mean = sum(pooled) / len(pooled)
        var = sum((v - mean) ** 2 for v in pooled) / max(len(pooled) - 1, 1)
        for j, spec in enumerate(specs):
            ab_vals = yab[j][output]
            if var <= 0:
                s1 = st = float("nan")
            else:
                # AB shares parameter j with A and all other inputs with B.
                # Hence A-vs-AB isolates the complement of j (first order),
                # while B-vs-AB isolates j itself (total order).
                s1 = 1.0 - sum(
                    (a_vals[i] - ab_vals[i]) ** 2 for i in range(base_n)
                ) / (2.0 * base_n * var)
                st = sum(
                    (b_vals[i] - ab_vals[i]) ** 2 for i in range(base_n)
                ) / (2.0 * base_n * var)
            row: dict[str, Any] = {
                "output": output,
                "parameter": spec.name,
                "sobol_first_order": s1,
                "sobol_total_order": st,
                "base_n": base_n,
                "model_evaluations_for_output": base_n * (k + 2),
            }
            if bootstrap_replicates:
                rng = random.Random(seed + 7919 + j)
                boot_s1: list[float] = []
                boot_st: list[float] = []
                for _ in range(bootstrap_replicates):
                    idx = [rng.randrange(base_n) for _ in range(base_n)]
                    aa = [a_vals[i] for i in idx]
                    bb = [b_vals[i] for i in idx]
                    cc = [ab_vals[i] for i in idx]
                    pooled_b = aa + bb
                    mean_b = sum(pooled_b) / len(pooled_b)
                    var_b = sum((v - mean_b) ** 2 for v in pooled_b) / max(len(pooled_b) - 1, 1)
                    if var_b <= 0:
                        continue
                    boot_s1.append(
                        1.0 - sum((aa[i] - cc[i]) ** 2 for i in range(base_n))
                        / (2.0 * base_n * var_b)
                    )
                    boot_st.append(
                        sum((bb[i] - cc[i]) ** 2 for i in range(base_n))
                        / (2.0 * base_n * var_b)
                    )
                row["sobol_first_ci05"] = quantile(boot_s1, 0.05)
                row["sobol_first_ci95"] = quantile(boot_s1, 0.95)
                row["sobol_total_ci05"] = quantile(boot_st, 0.05)
                row["sobol_total_ci95"] = quantile(boot_st, 0.95)
            rows.append(row)
    return rows

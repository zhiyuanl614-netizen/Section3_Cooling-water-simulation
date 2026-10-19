"""
Grid-side impact assessment (assessment tier B): DC-OPF + load shedding.

Interface contract (see docs/RESEARCH_FRAMEWORK.md section 6.4):
    input : pavail_mw[gen_id]
    rule  : for generators in the cold-end set, Pmax_used = pavail_mw[gen_id];
            every other generator keeps the case Pmax.
    output: served / unserved load, line loading, dispatch.

The IEEE 39-bus case is taken from ``pandapower.networks.case39`` (MATPOWER
derivative) so no network data is hand-copied into this repository.  Load
shedding is modelled in the standard way -- a curtailment generator is placed
at every load bus with a very high marginal cost (value of lost load), so the
OPF only sheds when it has no cheaper alternative.

pandapower is an *optional* dependency: importing this module without it raises
an informative error, while everything else in the package keeps working.
"""

from __future__ import annotations

import warnings
import math
from dataclasses import dataclass, field
from typing import Any, Sequence

from .coupling import DEFAULT_MACRO_STEP_H, event_aware_time_nodes

# Marginal cost of ordinary generation (EUR/MWh); only the *ordering* matters
# when the question is unserved load, not the absolute dispatch cost.
DEFAULT_MARGINAL_COST = 25.0
# Value of lost load (EUR/MWh).  Large enough that shedding is a last resort.
DEFAULT_VOLL = 10_000.0

COLD_END_BUSES = {33: "G33", 34: "G34"}


def _require_pandapower():
    try:
        import pandapower as pp  # noqa: PLC0415
        from pandapower.networks import case39  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "pandapower is required for the grid-side OPF assessment "
            "(assessment tier B).  Install it with `pip install pandapower`, "
            "or use the default tier-A outputs (pavail_mw / capacity_lost_mw) "
            "which need only the standard library."
        ) from exc
    return pp, case39


@dataclass
class GridImpactResult:
    """Outcome of one OPF with a cold-end-constrained dispatch."""

    total_load_mw: float
    served_load_mw: float
    shed_load_mw: float
    shed_fraction: float
    max_line_loading_percent: float
    n_overloaded_lines: int
    generation_mw: dict[str, float] = field(default_factory=dict)
    applied_pmax_mw: dict[str, float] = field(default_factory=dict)
    converged: bool = True
    notes: str = ""
    shed_by_bus_mw: dict[int, float] = field(default_factory=dict)
    physical_pmax_mw: dict[str, float] = field(default_factory=dict)
    max_branch_loading_percent: float = 0.0
    max_nodal_residual_mw: float = 0.0
    n_overloaded_branches: int = 0
    n_branches_checked: int = 0
    solver_cost_scale: float = 1.0

    def as_row(self, **extra: Any) -> dict[str, Any]:
        row = {
            "total_load_mw": round(self.total_load_mw, 3),
            "served_load_mw": round(self.served_load_mw, 3),
            "shed_load_mw": round(self.shed_load_mw, 3),
            "shed_fraction": round(self.shed_fraction, 5),
            "max_line_loading_percent": round(self.max_line_loading_percent, 2),
            "n_overloaded_lines": self.n_overloaded_lines,
            "converged": self.converged,
            "max_branch_loading_percent": round(self.max_branch_loading_percent, 6),
            "n_overloaded_branches": self.n_overloaded_branches,
            "max_nodal_residual_mw": self.max_nodal_residual_mw,
        }
        row.update(extra)
        return row


def build_case39_opf(
    pavail_mw: dict[str, float] | None = None,
    *,
    voll_eur_per_mwh: float = DEFAULT_VOLL,
    marginal_cost: float = DEFAULT_MARGINAL_COST,
    load_scale: float = 1.0,
    cost_scale: float = 1.0,
):
    """
    Build (without solving) a DC-OPF-ready IEEE 39-bus network with load curtailment.

    Parameters
    ----------
    pavail_mw
        Optional mapping ``{"G33": mw, "G34": mw}``.  Generators not listed --
        and all non-cold-end generators -- keep the case Pmax.
    """
    pp, case39 = _require_pandapower()
    net = case39()
    if load_scale != 1.0:
        net.load["p_mw"] = net.load["p_mw"] * float(load_scale)
        net.load["q_mvar"] = net.load["q_mvar"] * float(load_scale)

    if not math.isfinite(load_scale) or load_scale <= 0:
        raise ValueError("load_scale must be finite and positive")
    if not (0 < marginal_cost < voll_eur_per_mwh) or not math.isfinite(voll_eur_per_mwh):
        raise ValueError("require finite VOLL > marginal cost > 0")
    # Capture physical identities BEFORE virtual load-curtailment rows exist.
    physical = {int(idx): f"G{int(row.bus)+1}" for idx, row in net.gen.iterrows()}
    external = {int(idx): f"G{int(row.bus)+1}" for idx, row in net.ext_grid.iterrows()}
    if len(set(physical.values()) | set(external.values())) != 10:
        raise ValueError("unexpected case39 equivalent-generator mapping")
    net["_physical_gid_by_row"] = physical
    net["_external_gid_by_row"] = external
    bus_to_gen = {int(net.gen.at[idx, "bus"])+1: idx for idx in physical}
    for gid, value in (pavail_mw or {}).items():
        if not math.isfinite(float(value)) or value < 0:
            raise ValueError(f"invalid capability: {gid}={value}")
        if gid not in COLD_END_BUSES.values():
            originals = {name: float(net.gen.at[i, "max_p_mw"]) for i,name in physical.items()}
            originals.update({name: float(net.ext_grid.at[i, "max_p_mw"]) for i,name in external.items()})
            if gid not in originals or abs(value-originals[gid]) > 1e-7:
                raise ValueError(f"non-cooling machine must retain case Pmax: {gid}")
            continue  # compatibility with a complete healthy-capability dictionary
        bus = next(bus for bus, name in COLD_END_BUSES.items() if name == gid)
        idx = bus_to_gen[bus]
        original = float(net.gen.at[idx, "max_p_mw"])
        if value > original + 1e-7:
            raise ValueError(f"capability exceeds case nameplate: {gid}")
        net.gen.at[idx, "max_p_mw"] = float(value)
        net.gen.at[idx, "min_p_mw"] = min(float(net.gen.at[idx, "min_p_mw"]), float(value))

    # 2) marginal costs for real generation (uniform: ordering is what matters)
    #    the case may ship with its own cost tables -- replace them so that the
    #    dispatch ordering is explicit and the VOLL is unambiguous
    for table in ("poly_cost", "pwl_cost"):
        if table in net and len(net[table]):
            net[table].drop(net[table].index, inplace=True)
    #    costs are normalised by the marginal generation cost: only the *ratio*
    #    VOLL/MC drives the shed/no-shed decision, and keeping the absolute
    #    magnitudes near unity is what makes the interior-point LP well
    #    conditioned (a raw 10000-vs-25 spread fails to converge).
    norm = cost_scale / max(marginal_cost, 1e-9)
    for idx in net.gen.index:
        pp.create_poly_cost(net, idx, "gen", cp1_eur_per_mw=marginal_cost * norm)
    pp.create_poly_cost(net, 0, "ext_grid", cp1_eur_per_mw=marginal_cost * norm)

    # 3) load-shedding generators: one per load bus, cost = VOLL
    net["_curtailment_gen"] = []  # type: ignore[index]
    for bus, load_mw in zip(net.load["bus"], net.load["p_mw"]):
        if load_mw <= 0:
            continue
        idx = pp.create_gen(
            net,
            bus=int(bus),
            p_mw=0.0,
            min_p_mw=0.0,
            max_p_mw=float(load_mw),
            vm_pu=1.0,
            name=f"shed_bus_{int(bus) + 1}",
        )
        pp.create_poly_cost(net, idx, "gen", cp1_eur_per_mw=voll_eur_per_mwh * norm)
        net["_curtailment_gen"].append(idx)
    return net


def evaluate_grid_impact(
    pavail_mw: dict[str, float] | None = None,
    *,
    voll_eur_per_mwh: float = DEFAULT_VOLL,
    marginal_cost: float = DEFAULT_MARGINAL_COST,
    load_scale: float = 1.0,
) -> GridImpactResult:
    """
    Run one DC-OPF and report served/unserved load and line loading.

    ``load_scale`` multiplies every bus load: IEEE 39 has roughly 15% capacity
    margin at the case peak, but network congestion can cause shedding even at base load;
    demand sweeps assess the additional adequacy gap.

    Note: in a converged DC-OPF, line limits are *constraints*, so overload
    counts stay near zero by construction; binding lines show up as shed load.
    Overload counting belongs to the power-flow / cascade tier (C).
    """
    pp, _ = _require_pandapower()
    last_error: Exception | None = None
    net = None
    for cost_scale in (1.0, 1e-2, 1e-4):
        candidate = build_case39_opf(
            pavail_mw,
            voll_eur_per_mwh=voll_eur_per_mwh,
            marginal_cost=marginal_cost,
            load_scale=load_scale,
            cost_scale=cost_scale,
        )
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pp.rundcopp(candidate)
            net = candidate
            break
        except Exception as exc:  # noqa: BLE001 - retry with better conditioning
            last_error = exc
    if net is None:
        raise RuntimeError(
            f"DC-OPF did not converge even after cost re-scaling: {last_error}"
        )
    converged = bool(getattr(net, "OPF_converged", False))

    total_load = float(net.load["p_mw"].sum())
    shed = float(net.res_gen.loc[net["_curtailment_gen"], "p_mw"].sum())
    shed = max(0.0, shed)
    served = max(0.0, total_load - shed)

    if not converged or net["_options"].get("ac") is not False:
        raise RuntimeError("no converged DC-only OPF state")
    gen_out = {gid: float(net.res_gen.at[idx, "p_mw"]) for idx, gid in net["_physical_gid_by_row"].items()}
    limits = {gid: float(net.gen.at[idx, "max_p_mw"]) for idx, gid in net["_physical_gid_by_row"].items()}
    for idx, gid in net["_external_gid_by_row"].items():
        gen_out[gid] = float(net.res_ext_grid.at[idx, "p_mw"])
        limits[gid] = float(net.ext_grid.at[idx, "max_p_mw"])
    shed_by_bus = {}
    for idx in net["_curtailment_gen"]:
        bus = int(net.gen.at[idx, "bus"])+1
        shed_by_bus[bus] = shed_by_bus.get(bus, 0.0) + float(net.res_gen.at[idx, "p_mw"])
    # Check the actual DC solver model, including ALL line/transformer rows.
    from pandapower.pypower.idx_brch import F_BUS, T_BUS, RATE_A, PF, PT
    from pandapower.pypower.idx_bus import PD, GS
    from pandapower.pypower.idx_gen import GEN_BUS, PG
    import numpy as np
    ppc = net["_ppc_opf"]
    branches = ppc["branch"]
    residual = -ppc["bus"][:, PD].copy() - ppc["bus"][:, GS]
    for g in ppc["gen"]:
        residual[int(g[GEN_BUS])] += g[PG]
    for e in branches:
        residual[int(e[F_BUS])] -= e[PF]
        residual[int(e[T_BUS])] -= e[PT]
    ratios = np.maximum(np.abs(branches[:, PF]), np.abs(branches[:, PT])) / branches[:, RATE_A] * 100
    max_residual = float(np.max(np.abs(residual)))
    tol = 1e-5  # MW; stricter than the persisted three-decimal display precision
    if not all(math.isfinite(v) and -tol <= v <= limits[k]+tol for k,v in gen_out.items()):
        raise RuntimeError("physical generation outside capability bounds")
    if abs(sum(gen_out.values()) - served) > tol or max_residual > tol:
        raise RuntimeError(f"DC nodal/global imbalance: {max_residual} MW")
    if not np.all(np.isfinite(ratios)) or float(np.max(ratios)) > 100.0 + 1e-5:
        raise RuntimeError("DC branch constraints violated")
    for bus, value in shed_by_bus.items():
        demand = float(net.load.loc[net.load.bus == bus-1, "p_mw"].sum())
        if not -tol <= value <= demand+tol:
            raise RuntimeError("invalid bus load curtailment")
    max_loading = float(net.res_line["loading_percent"].max())
    return GridImpactResult(
        total_load_mw=total_load, served_load_mw=served, shed_load_mw=shed,
        shed_fraction=shed / total_load if total_load else 0.0,
        max_line_loading_percent=max_loading,
        n_overloaded_lines=int((net.res_line["loading_percent"] > 100.0+1e-5).sum()),
        generation_mw=gen_out, applied_pmax_mw={gid: limits[gid] for gid in COLD_END_BUSES.values()},
        converged=True, notes="DC-only rundcopp; physical/virtual identities separated; all 46 branch limits/KCL checked",
        shed_by_bus_mw=shed_by_bus, physical_pmax_mw=limits,
        max_branch_loading_percent=float(np.max(ratios)), max_nodal_residual_mw=max_residual,
        n_overloaded_branches=int((ratios > 100.0+1e-5).sum()), n_branches_checked=len(branches),
        solver_cost_scale=cost_scale,
    )


def evaluate_timeseries(
    timeseries_by_unit: dict[str, Any],
    *,
    faulted_unit: str,
    t_end_h: float | None = None,
    sample_step_h: float | None = None,
    macro_step_h: float = DEFAULT_MACRO_STEP_H,
    event_aware: bool = True,
    time_nodes: Sequence[float] | None = None,
    healthy_pmax_mw: dict[str, float] | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """
    Sweep the OPF along a cold-end trajectory.

    ``timeseries_by_unit`` maps gen_id -> :class:`cooling.dynamics.TimeseriesResult`.
    Only the faulted unit's trajectory is swept; all other units keep their
    healthy Pmax from ``healthy_pmax_mw``.

    By default this is a multi-timescale exchange: the OPF is solved on a
    regular macro-step (five minutes unless overridden) augmented with the
    trajectory's derating and trip events.  ``sample_step_h`` is retained as
    a backwards-compatible alias for the macro-step.  Set
    ``event_aware=False`` only to reproduce a legacy uniform sweep.
    """
    ts = timeseries_by_unit[faulted_unit]
    end = t_end_h if t_end_h is not None else (ts.t_trip_h or ts.t_h[-1])
    step = macro_step_h if sample_step_h is None else sample_step_h
    if time_nodes is not None:
        nodes = sorted({round(min(max(float(t), 0.0), float(end)), 10) for t in time_nodes})
        if not nodes or nodes[0] > 0.0:
            nodes.insert(0, 0.0)
        if nodes[-1] < float(end):
            nodes.append(float(end))
        coupling_mode = "prescribed_time_nodes"
    elif event_aware:
        nodes = event_aware_time_nodes(ts, t_end_h=float(end), macro_step_h=float(step))
        coupling_mode = "event_aware_multirate"
    else:
        nodes = []
        t = 0.0
        while t <= end + 1e-9:
            nodes.append(float(t))
            t += float(step)
        if not nodes or nodes[-1] < end - 1e-9:
            nodes.append(float(end))
        coupling_mode = "legacy_uniform"

    event_times = set()
    if event_aware:
        from .coupling import trajectory_event_times  # local to keep mode explicit
        event_times = {round(float(t), 3) for t in trajectory_event_times(ts)}

    trip = ts.t_trip_h
    if event_aware and trip is not None and 0 < trip <= float(end):
        nodes = sorted(set([*nodes, float(trip)]))
    samples = []
    for t in nodes:
        if event_aware and trip is not None and t == trip and t > 0:
            samples.append((t, "left"))
        samples.append((t, "right"))
    rows: list[dict[str, Any]] = []
    for t, side in samples:
        pavail = dict(healthy_pmax_mw or {})
        pavail[faulted_unit] = ts.p_avail_at(t, side=side)
        res = evaluate_grid_impact(pavail, **kwargs)
        rows.append(
            res.as_row(
                faulted_unit=faulted_unit,
                t_h=float(t),
                event_side=side,
                pavail_faulted_mw=round(pavail[faulted_unit], 3),
                trip_mechanism=ts.trip_mechanism,
                coupling_mode=coupling_mode,
                macro_step_h=round(float(step), 6),
                snapshot_is_event=round(float(t), 3) in event_times,
            )
        )
    return rows


def baseline_no_fault(**kwargs: Any) -> GridImpactResult:
    """Reference OPF with the unmodified case (no cold-end constraint)."""
    return evaluate_grid_impact(None, **kwargs)

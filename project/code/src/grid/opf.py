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

    def as_row(self, **extra: Any) -> dict[str, Any]:
        row = {
            "total_load_mw": round(self.total_load_mw, 3),
            "served_load_mw": round(self.served_load_mw, 3),
            "shed_load_mw": round(self.shed_load_mw, 3),
            "shed_fraction": round(self.shed_fraction, 5),
            "max_line_loading_percent": round(self.max_line_loading_percent, 2),
            "n_overloaded_lines": self.n_overloaded_lines,
            "converged": self.converged,
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
    Build (and run) a DC-OPF-ready IEEE 39-bus network with load curtailment.

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

    # 1) map our gen ids to pandapower gen rows (0-indexed bus numbers)
    bus_to_gen = {int(b) + 1: idx for idx, b in enumerate(net.gen["bus"])}
    for bus, gid in COLD_END_BUSES.items():
        if gid in (pavail_mw or {}):
            idx = bus_to_gen.get(bus)
            if idx is None:  # pragma: no cover - defensive
                raise KeyError(f"bus {bus} not found among case39 generators")
            net.gen.at[idx, "max_p_mw"] = float(max(0.0, pavail_mw[gid]))
            # keep feasibility of the box constraints
            net.gen.at[idx, "min_p_mw"] = float(
                min(net.gen.at[idx, "min_p_mw"], net.gen.at[idx, "max_p_mw"])
            )

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
    margin at the case peak, so single-unit losses only produce unserved load
    at elevated demand levels -- sweep it to build the adequacy picture.

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
    converged = bool(getattr(net, "OPF_converged", True))

    total_load = float(net.load["p_mw"].sum())
    shed = float(net.res_gen.loc[net["_curtailment_gen"], "p_mw"].sum())
    shed = max(0.0, shed)
    served = max(0.0, total_load - shed)

    max_loading = float(net.res_line["loading_percent"].max())
    n_over = int((net.res_line["loading_percent"] > 100.0).sum())

    bus_to_gen = {int(b) + 1: idx for idx, b in enumerate(net.gen["bus"])}
    gen_out: dict[str, float] = {}
    for bus, gid in COLD_END_BUSES.items():
        idx = bus_to_gen.get(bus)
        if idx is not None:
            gen_out[gid] = round(float(net.res_gen.at[idx, "p_mw"]), 3)
    # non-modelled machines, by bus number
    for bus, idx in bus_to_gen.items():
        gid = f"G{bus}"
        if gid not in gen_out:
            gen_out[gid] = round(float(net.res_gen.at[idx, "p_mw"]), 3)
    if len(net.res_ext_grid):
        gen_out["G39"] = round(float(net.res_ext_grid.at[0, "p_mw"]), 3)

    applied = {
        gid: float(net.gen.at[bus_to_gen[bus], "max_p_mw"])
        for bus, gid in COLD_END_BUSES.items()
    }

    return GridImpactResult(
        total_load_mw=total_load,
        served_load_mw=served,
        shed_load_mw=shed,
        shed_fraction=shed / total_load if total_load else 0.0,
        max_line_loading_percent=max_loading,
        n_overloaded_lines=n_over,
        generation_mw=gen_out,
        applied_pmax_mw=applied,
        converged=converged,
        notes="DC-OPF (rundcopp) with curtailment generators at every load bus",
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

    rows: list[dict[str, Any]] = []
    for t in nodes:
        pavail = dict(healthy_pmax_mw or {})
        pavail[faulted_unit] = ts.p_avail_at(t)
        res = evaluate_grid_impact(pavail, **kwargs)
        rows.append(
            res.as_row(
                faulted_unit=faulted_unit,
                t_h=round(float(t), 3),
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

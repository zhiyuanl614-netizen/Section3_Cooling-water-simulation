"""DC-only, island-balanced overload propagation (v0.7).

S: proportional shedding/curtailment without upward reserve.
H: bounded headroom participation, followed by proportional shedding if needed.
Capabilities are upper bounds, not mandatory injections. Both policies carry
actual dispatch and served demand between removal rounds; there is no automatic
load restoration. These are static response assumptions, NOT governor, AGC,
frequency or relay-time simulation. Core implementation is standard-library only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, MutableSequence, Sequence, Tuple

TOL_MW = 1e-7


class PowerFlowError(RuntimeError):
    """An unbalanced or unsolved DC state must never be called converged."""


def _solve_linear(a: List[List[float]], b: List[float]) -> List[float]:
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-14:
            raise PowerFlowError('singular reduced island matrix')
        m[col], m[piv] = m[piv], m[col]
        diag = m[col][col]
        for j in range(col, n + 1):
            m[col][j] /= diag
        for row in range(n):
            if row != col:
                factor = m[row][col]
                for j in range(col, n + 1):
                    m[row][j] -= factor * m[col][j]
    x = [m[i][n] for i in range(n)]
    if not all(math.isfinite(v) for v in x):
        raise PowerFlowError('non-finite island angles')
    return x


@dataclass
class CascadeResult:
    removed_lines: List[int]
    stages: List[List[int]]
    line_flows_mw: List[float]
    cascade_triggered: bool
    status: str = 'converged'
    policy: str = 'S'
    rule: str = 'simultaneous'
    generation_mw: Dict[int, float] = field(default_factory=dict)
    served_load_mw: Dict[int, float] = field(default_factory=dict)
    shed_load_mw: float | None = None
    islands: List[Dict] = field(default_factory=list)
    deenergized_intact_lines: List[int] = field(default_factory=list)
    trace: List[Dict] = field(default_factory=list)
    notes: str = ''

    @property
    def n_removed(self) -> int:
        return len(self.removed_lines)

    @property
    def converged(self) -> bool:
        return self.status == 'converged'


@dataclass
class IEEE39CascadeGrid:
    base_mva: float = 100.0
    buses: List[Dict] | None = None
    generators: List[Dict] | None = None
    lines: List[Dict] | None = None
    failed_lines: MutableSequence[int] = field(default_factory=list)
    reference_bus: int = 31

    def __post_init__(self) -> None:
        if self.buses is None:
            self.buses = _default_buses()
        if self.generators is None:
            self.generators = _default_generators()
        if self.lines is None:
            self.lines = _default_lines()
        if not math.isfinite(self.base_mva) or self.base_mva <= 0:
            raise ValueError('invalid base MVA')
        ids = [int(b['id']) for b in self.buses]
        if len(set(ids)) != len(ids):
            raise ValueError('duplicate bus IDs')
        if len({g['bus'] for g in self.generators}) != len(self.generators):
            raise ValueError('equivalent model requires one generator per generator bus')
        for b in self.buses:
            if not math.isfinite(float(b['Pd'])) or b['Pd'] < 0:
                raise ValueError('invalid demand')
        for e in self.lines:
            if e['from'] not in ids or e['to'] not in ids or e['from'] == e['to']:
                raise ValueError('invalid branch endpoints')
            if not all(math.isfinite(float(e[k])) and e[k] > 0 for k in ('x', 'rate')):
                raise ValueError('branch reactance/rating must be positive and finite')
        for g in self.generators:
            if g['bus'] not in ids or not math.isfinite(float(g['Pmax'])) or g['Pmax'] < 0:
                raise ValueError('invalid equivalent generator')

    def reset(self) -> None:
        self.failed_lines = []

    def components(self) -> List[List[int]]:
        adj = {int(b['id']): [] for b in self.buses}
        for i, e in enumerate(self.lines):
            if i not in self.failed_lines:
                adj[e['from']].append(e['to'])
                adj[e['to']].append(e['from'])
        seen = set()
        out = []
        for n in adj:
            if n in seen:
                continue
            stack = [n]
            seen.add(n)
            comp = []
            while stack:
                v = stack.pop()
                comp.append(v)
                for w in adj[v]:
                    if w not in seen:
                        seen.add(w)
                        stack.append(w)
            out.append(sorted(comp))
        return out

    def base_dispatch(self) -> Dict[int, float]:
        """Explicit lossless base, not implicit post-fault slack compensation."""
        pg = {int(g['bus']): float(g['Pg']) for g in self.generators}
        if not pg:
            return pg
        ref = self.reference_bus if self.reference_bus in pg else next(iter(pg))
        pg[ref] = sum(float(b['Pd']) for b in self.buses) - sum(v for n, v in pg.items() if n != ref)
        cap = {g['bus']: float(g['Pmax']) for g in self.generators}
        if any(not math.isfinite(v) or v < -TOL_MW or v > cap[n] + TOL_MW for n, v in pg.items()):
            raise ValueError('lossless base dispatch violates capacity; supply an appropriate base case')
        return pg

    def build_b_matrix(self) -> List[List[float]]:
        pos = {b['id']: i for i, b in enumerate(self.buses)}
        b = [[0.0] * len(pos) for _ in pos]
        for k, e in enumerate(self.lines):
            if k not in self.failed_lines:
                i, j = pos[e['from']], pos[e['to']]
                w = 1.0 / e['x']
                b[i][i] += w
                b[j][j] += w
                b[i][j] -= w
                b[j][i] -= w
        return b

    def injections_mw(self, gen_pg: Mapping[int, float] | None = None,
                      served_load_mw: Mapping[int, float] | None = None) -> List[float]:
        pg = self.base_dispatch() if gen_pg is None else gen_pg
        load = {b['id']: float(b['Pd']) for b in self.buses} if served_load_mw is None else served_load_mw
        return [float(pg.get(b['id'], 0.0)) - float(load[b['id']]) for b in self.buses]

    def dc_power_flow(self, gen_pg: Mapping[int, float] | None = None, *,
                      served_load_mw: Mapping[int, float] | None = None,
                      reference_buses: Sequence[int] | None = None) -> Tuple[List[float], List[float]]:
        """Solve already-balanced injections; never invent balancing generation.

        Explicit gen_pg is a complete actual-dispatch mapping. Missing buses
        inject no generation. Use solve_cascade for capability-constrained states.
        """
        ids = [b['id'] for b in self.buses]
        pos = {n: i for i, n in enumerate(ids)}
        p = self.injections_mw(gen_pg, served_load_mw)
        bmat = self.build_b_matrix()
        theta = [0.0] * len(ids)
        for comp in self.components():
            if abs(sum(p[pos[n]] for n in comp)) > TOL_MW:
                raise PowerFlowError(f'unbalanced island {comp}')
            candidates = [n for n in (reference_buses or []) if n in comp]
            ref = candidates[0] if candidates else (self.reference_bus if self.reference_bus in comp else comp[0])
            ix = [pos[n] for n in comp if n != ref]
            x = _solve_linear([[bmat[i][j] for j in ix] for i in ix], [p[i] / self.base_mva for i in ix])
            for i, v in zip(ix, x):
                theta[i] = v
        residual = max((abs(self.base_mva * sum(bmat[i][j] * theta[j] for j in range(len(ids))) - p[i])
                        for i in range(len(ids))), default=0.0)
        if not math.isfinite(residual) or residual > TOL_MW:
            raise PowerFlowError(f'nodal residual {residual} MW')
        flows = [0.0 if k in self.failed_lines else self.base_mva * (theta[pos[e['from']]] - theta[pos[e['to']]]) / e['x']
                 for k, e in enumerate(self.lines)]
        return flows, theta

    def overloaded(self, flows: Sequence[float]) -> List[int]:
        return [i for i, e in enumerate(self.lines) if i not in self.failed_lines and abs(flows[i]) > e['rate'] + TOL_MW]

    def _balance(self, pg: Dict[int, float], load: Dict[int, float], caps: Dict[int, float], policy: str) -> List[Dict]:
        islands = []
        for comp in self.components():
            gs = [n for n in comp if n in pg]
            demand = sum(load[n] for n in comp)
            capacity = sum(caps[n] for n in gs)
            current = sum(pg[n] for n in gs)
            supply = min(demand, current if policy == 'S' else capacity)
            if current > supply:
                for n in gs:
                    pg[n] *= supply / current
            elif supply > current:
                headroom = sum(caps[n] - pg[n] for n in gs)
                if headroom <= 0:
                    raise PowerFlowError('no headroom for assigned reserve response')
                for n in gs:
                    pg[n] += (supply - current) * (caps[n] - pg[n]) / headroom
            if demand > 0:
                for n in comp:
                    load[n] *= supply / demand
            if abs(sum(pg[n] for n in gs) - sum(load[n] for n in comp)) > TOL_MW:
                raise PowerFlowError('island balance failed')
            islands.append({'buses': comp, 'available_capacity_mw': capacity,
                            'generation_mw': sum(pg[n] for n in gs), 'served_load_mw': sum(load[n] for n in comp),
                            'state': 'no_available_generation' if capacity == 0 else ('no_demand' if demand == 0 else 'balanced')})
        if any(v < -TOL_MW or v > caps[n] + TOL_MW for n, v in pg.items()):
            raise PowerFlowError('generator capability violation')
        return islands

    def solve_cascade(self, capabilities_mw: Mapping[int, float] | None = None, *, policy: str = 'S',
                      rule: str = 'simultaneous', max_iters: int = 30) -> CascadeResult:
        """State-carrying cascade; capability overrides apply only to named buses.

        S never increases generation. H uses all static headroom as a response
        scenario, NOT a calibrated claim of fast reserve delivery. Generator
        minima are zero in this equivalent model. Starts with the current
        failed_lines set; callers must reset between independent experiments.
        """
        if policy not in ('S', 'H') or rule not in ('simultaneous', 'sequential') or max_iters < 0:
            raise ValueError('invalid policy, removal rule or iteration limit')
        caps = {int(g['bus']): float(g['Pmax']) for g in self.generators}
        for n, value in (capabilities_mw or {}).items():
            if n not in caps or not math.isfinite(float(value)) or value < 0 or value > caps[n] + TOL_MW:
                raise ValueError(f'invalid capability override: {n}={value}')
            caps[n] = float(value)
        pg = {n: min(v, caps[n]) for n, v in self.base_dispatch().items()}
        load = {b['id']: float(b['Pd']) for b in self.buses}
        original_total = sum(load.values())
        result = CascadeResult([], [], [], False, policy=policy, rule=rule)
        for k in range(max_iters + 1):
            prev_load = dict(load)
            try:
                islands = self._balance(pg, load, caps, policy)
                flows, angles = self.dc_power_flow(pg, served_load_mw=load)
                p = self.injections_mw(pg, load)
                bm = self.build_b_matrix()
                residual = max(abs(self.base_mva * sum(bm[i][j] * angles[j] for j in range(len(p))) - p[i]) for i in range(len(p)))
            except PowerFlowError as exc:
                result.status = 'solver_failed'
                result.notes = f'round {k}: {exc}; solved trace retained, no terminal flows'
                result.line_flows_mw = []
                result.generation_mw = {}
                result.served_load_mw = {}
                result.islands = []
                result.deenergized_intact_lines = []
                result.shed_load_mw = None
                return result
            if any(load[n] > prev_load[n] + TOL_MW for n in load):
                raise PowerFlowError('implicit load restoration')
            over = self.overloaded(flows)
            pick = over if rule == 'simultaneous' or not over else [max(over, key=lambda i: (abs(flows[i]) / self.lines[i]['rate'], i))]
            if k == max_iters and over:
                pick = []
            dead = {n for island in islands if island['available_capacity_mw'] <= TOL_MW for n in island['buses']}
            result.line_flows_mw = flows
            result.generation_mw = dict(pg)
            result.served_load_mw = dict(load)
            result.islands = islands
            result.deenergized_intact_lines = [i for i, e in enumerate(self.lines) if i not in self.failed_lines and e['from'] in dead and e['to'] in dead]
            result.trace.append({'round': k, 'removed_before': list(self.failed_lines), 'overloaded': over,
                                 'newly_tripped': list(pick), 'generation_mw': dict(pg), 'served_load_mw': dict(load),
                                 'shed_mw': original_total - sum(load.values()), 'islands': islands,
                                 'max_nodal_residual_mw': residual, 'flows_mw': list(flows)})
            if not over:
                result.shed_load_mw = original_total - sum(load.values())
                return result
            if k == max_iters:
                result.status = 'iteration_limit'
                result.notes = 'overloads remain; not a terminal cascade solution'
                result.shed_load_mw = None
                return result
            self.failed_lines.extend(pick)
            result.removed_lines.extend(pick)
            result.stages.append(list(pick))
            result.cascade_triggered = True
        raise AssertionError('unreachable')

    def max_loading(self, flows: Sequence[float] | None = None) -> float:
        if flows is None:
            flows, _ = self.dc_power_flow()
        return max((abs(flows[i]) / e['rate'] for i, e in enumerate(self.lines) if i not in self.failed_lines), default=0.0)


def cascade_from_capabilities(capabilities_mw: Mapping[int, float], *, grid: IEEE39CascadeGrid | None = None,
                              policy: str = 'S', rule: str = 'simultaneous') -> CascadeResult:
    g = IEEE39CascadeGrid() if grid is None else grid
    g.reset()
    return g.solve_cascade(capabilities_mw, policy=policy, rule=rule)


def cascade_from_unit_outputs(outputs_mw: Mapping[int, float], *, grid: IEEE39CascadeGrid | None = None) -> CascadeResult:
    """Compatibility name: v0.7 interprets these values as capability bounds."""
    return cascade_from_capabilities(outputs_mw, grid=grid)


def _default_buses() -> List[Dict]:
    pd = {
        1: 97.6, 3: 322.0, 4: 500.0, 7: 233.8, 8: 522.0, 9: 6.5, 12: 8.53,
        15: 320.0, 16: 329.0, 18: 158.0, 20: 680.0, 21: 274.0, 23: 247.5,
        24: 308.6, 25: 224.0, 26: 139.0, 27: 281.0, 28: 206.0, 29: 283.5,
        31: 9.2, 39: 1104.0,
    }
    # type: 1=PQ, 2=PV, 3=Slack
    types = {31: 3}
    for b in range(30, 40):
        types.setdefault(b, 2)
    out = []
    for i in range(1, 40):
        out.append({"id": i, "type": types.get(i, 1), "Pd": float(pd.get(i, 0.0))})
    return out


def _default_generators() -> List[Dict]:
    # Buses 33 and 34 are the mapped wet-recirc units; Pg/Pmax follow the
    # MATPOWER case39 solved case and generator ratings.
    return [
        {"bus": 30, "Pg": 250.0, "Pmax": 1040.0},
        {"bus": 31, "Pg": 677.87, "Pmax": 646.0},
        {"bus": 32, "Pg": 650.0, "Pmax": 725.0},
        {"bus": 33, "Pg": 632.0, "Pmax": 652.0},
        {"bus": 34, "Pg": 508.0, "Pmax": 508.0},
        {"bus": 35, "Pg": 650.0, "Pmax": 687.0},
        {"bus": 36, "Pg": 560.0, "Pmax": 580.0},
        {"bus": 37, "Pg": 540.0, "Pmax": 564.0},
        {"bus": 38, "Pg": 830.0, "Pmax": 865.0},
        {"bus": 39, "Pg": 1000.0, "Pmax": 1100.0},
    ]


def _default_lines() -> List[Dict]:
    raw: Iterable[Tuple[int, int, float, float]] = [
        (1, 2, 0.0411, 600), (1, 39, 0.0250, 1000), (2, 3, 0.0151, 500),
        (2, 25, 0.0086, 500), (3, 4, 0.0213, 500), (3, 18, 0.0133, 500),
        (4, 5, 0.0128, 600), (4, 14, 0.0129, 500), (5, 6, 0.0026, 1200),
        (5, 8, 0.0112, 900), (6, 7, 0.0092, 900), (6, 11, 0.0082, 480),
        (7, 8, 0.0046, 900), (8, 9, 0.0363, 900), (9, 39, 0.0250, 900),
        (10, 11, 0.0043, 600), (10, 13, 0.0043, 600), (13, 14, 0.0101, 600),
        (14, 15, 0.0217, 600), (15, 16, 0.0094, 600), (16, 17, 0.0089, 600),
        (16, 19, 0.0195, 600), (16, 21, 0.0135, 600), (16, 24, 0.0059, 600),
        (17, 18, 0.0082, 600), (17, 27, 0.0173, 600), (21, 22, 0.0140, 900),
        (22, 23, 0.0096, 600), (23, 24, 0.0350, 600), (25, 26, 0.0323, 600),
        (26, 27, 0.0147, 600), (26, 28, 0.0474, 600), (26, 29, 0.0625, 600),
        (28, 29, 0.0151, 600), (2, 30, 0.0181, 900), (6, 31, 0.0250, 1800),
        (10, 32, 0.0200, 900), (11, 12, 0.0435, 500), (12, 13, 0.0435, 500),
        (19, 20, 0.0138, 900), (19, 33, 0.0142, 900), (20, 34, 0.0180, 900),
        (22, 35, 0.0143, 900), (23, 36, 0.0272, 900), (25, 37, 0.0232, 900),
        (29, 38, 0.0156, 1200),
    ]
    return [
        {"from": f, "to": t, "x": x, "rate": float(rate)} for f, t, x, rate in raw
    ]

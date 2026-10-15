# From cold-end emergencies to cascading outages: a multi-timescale mechanistic model of wet-recirculating cooling under fault contingencies

---

## Highlights

1. Wet cold-end emergencies are progressive, not instantaneous generator trips.
2. Multi-timescale model yields mechanism-resolved \(P_\mathrm{avail}(t)\) trajectories.
3. Quasi-static controls show second-to-minute lags are load-bearing for pump loss.
4. On IEEE 39, dual-unit cooling collapse cascades; single-unit trips do not.
5. At \(1.15\times\) load, black-box instant trips overstate unserved energy by ~53%.

---

## Abstract

Cooling-water failures in thermoelectric fleets are commonly encoded in power-system models as exogenous availability factors, fixed derating schedules or instantaneous generator outages. That encoding is poorly matched to wet-recirculating cold ends, where basin inventory, circulating-water hydraulics, condenser backpressure and protection evolve on seconds-to-hours scales and can produce progressive capability loss rather than a binary trip. This paper develops a literature- and standard-anchored multi-timescale mechanistic model that maps makeup interruption, circulating-pump outage and wet-bulb stress into mechanism-resolved delivered capability \(P_\mathrm{avail}(t)\), and couples dual-unit schedules to an event-driven DC cascading assessment on the synthetic IEEE 39-bus network. On the two mapped wet-recirculating units (652 MW and 508 MW), makeup interruption under ride-down with blowdown isolation trips on pump low level at 5.07 h versus 3.88 h when blowdown is maintained; full circulating-pump outage trips on backpressure protection in under one minute, whereas a quasi-static twin with frozen thermal and pump lags trips nearly an order of magnitude earlier. On the test network under simultaneous overloaded-branch removal, dual-unit capability collapse removes 13 lines across two stages, while a single-unit trip removes no branch. Relative to instantaneous trip, the mechanistic ride-down path yields about 53% lower incremental unserved energy at the studied \(1.15\times\) load level over 0–8 h. The results indicate that black-box cooling outages are not uniformly conservative and that cascading risk is a common-mode threshold question, not an automatic consequence of any cold-end contingency.

**Keywords:** wet recirculating cooling; cold-end dynamics; makeup interruption; pump outage; cascading failure; multi-timescale modelling

---

## 1. Introduction

Thermoelectric power generation depends on continuous cooling to reject condenser waste heat. In wet-recirculating plants, which remain widespread for coal- and nuclear-fired units in humid and temperate climates, evaporation, drift and blowdown close the heat-rejection loop and a steady makeup supply is required to sustain basin inventory [6, 7, 10, 16, 17]. Droughts, heat waves and tightening thermal discharge limits have repeatedly forced thermoelectric units to derate or shut down in Europe, the United States and elsewhere, converting cooling-water stress from a plant-internal operating detail into an adequacy and planning risk [3–5, 9, 11, 14, 15]. Concurrent multi-plant water stress can elevate wholesale prices, erode reserve margins and expose regional generation fleets to correlated capacity loss under climate-driven low-flow and high-temperature regimes [2, 3, 8, 12, 13, 45].

System-level water–energy research has therefore moved cooling availability into operational and planning models. Security-constrained unit commitment and economic dispatch formulations now embed river-temperature, flow and multi-level cooling-water availability constraints that bound generator output when physical or regulatory water limits bind [1, 9, 12, 43, 44]. Complementary studies quantify how short-term water constraints reshape regional dispatch, fuel switching and prices [2, 46], how hydrologic drought and heat waves threaten grid reliability when thermoelectric capability is curtailed [43], and how water-intensity factors support technology comparison across once-through, wet-recirculating and dry cooling [6, 7, 10]. Across this literature, however, cooling enters the power-system layer as an exogenous availability factor, a fixed derating schedule, a forced minimum-output or shutdown flag, or a binary generator outage. Basin inventory, circulating-pump hydraulics, condenser backpressure and protection logic remain outside the model: the unit is treated as water-constrained or not, while the time scale, trajectory and mechanism of failure are prescribed rather than resolved.

At the plant boundary, cold-end engineering is comparatively mature for design and normal off-design performance. Wet-tower analysis is anchored in Merkel and effectiveness–NTU formulations, with critical comparisons to the Poppe method clarifying when the simpler closures remain adequate [19–22], and condenser practice is organised around HEI design semantics for terminal temperature difference, cleanliness and vacuum [18]. Dynamic plant studies have begun to resolve minutes-scale tower-outlet and vacuum evolution under load and ambient disturbances in wet-recirculating systems [23], slower air-cooled cold-end transients [24], and the propagation of backpressure uncertainty into generator capability [25]; circulating-water pump trips can also drive condenser pressure toward protection set-points on second-to-minute horizons in detailed fault simulations [47]. These advances establish that cold-end dynamics are physically consequential, yet they largely address normal cycling and ambient stress rather than emergency fault spectra such as makeup interruption, full or partial circulating-pump outage, and operator or protection response, and they stop at the plant boundary without a transmission outlet. On the network side, cascading-outage research has developed branching-process and sequential overload frameworks [30, 31], dynamically induced cascade models [48], and multi-rate co-simulation principles for coupling heterogeneous time scales [34, 35]. In that setting, the generator loss that initiates cascade is almost always an exogenous injection change: the causal chain from cooling failure—whether progressive inventory drain, abrupt hydraulic collapse, or common-mode dual-unit stress—is not part of the cascading model.

The resulting knowledge gap is therefore twofold and defines the questions addressed in this study. At the plant boundary, wet-recirculating cold-end emergencies are not yet mapped into mechanism-resolved delivered-capability trajectories \(P_\mathrm{avail}(t)\) that distinguish inventory-limited hour-scale failure, hydraulics-limited vacuum trip and sustained derating without trip. At the transmission boundary, cooling-driven generation loss is still consumed as a prescribed outage shape, without testing when a single-unit event remains inside N-1 margin and when common-mode capability collapse crosses into successive line overload. Correspondingly, RQ1 asks how makeup interruption, circulating-pump outage and wet-bulb stress propagate through thermal–hydraulic coupling into distinct capability trajectories and trip labels; RQ2 asks under what common-mode conditions cooling-driven capability loss escalates from an absorbed unit contingency into cascading branch removal; and RQ3 asks what system-level bias is introduced by conventional black-box outage encodings and by quasi-static integration that freezes second-to-minute cold-end lags.

This paper develops a literature- and standard-anchored multi-timescale mechanistic model of wet-recirculating cold ends that maps makeup interruption, circulating-pump outage and wet-bulb stress into mechanism-resolved delivered capability \(P_\mathrm{avail}(t)\), and couples dual-unit schedules to an event-driven DC cascading outlet on the synthetic IEEE 39-bus network. The contributions map one-to-one onto the research questions: a multi-contingency cold-end model that distinguishes inventory-driven hour-scale failure, hydraulics-driven second-scale vacuum trip and sustained derating regimes (RQ1); a conditional common-mode cascading boundary in which a single-unit cooling trip removes no branch while dual-unit capability collapse triggers successive line overload on the test network (RQ2); and a quantitative assessment of black-box outage encodings and quasi-static integration, showing that simplified availability shapes are not uniformly conservative and that second-to-minute lags are load-bearing for fast hydraulic contingencies under the studied conditions (RQ3). Section 2 presents the four-layer plant-to-grid formulation; Section 3 specifies the calibration archetype, the two mapped units and the IEEE 39 case; Section 4 reports contingency, cascading, benchmark and sensitivity results; Section 5 discusses implications and boundaries; and Section 6 concludes.

---

## 2. Methods

### 2.1 Problem formulation: cold-end-to-grid cascading pathway

To open the black-box encoding identified in Section 1, this study maps plant-boundary wet-recirculating contingencies through thermal–hydraulic cold-end states into time-resolved delivered capability \(P_\mathrm{avail}(t)\), and couples that trajectory to an event-driven cascading assessment on a synthetic IEEE 39-bus network. The modelling object is the causal chain from contingency class through equipment state to \(P_\mathrm{avail}(t)\) and, when multiple mapped wet units lose capability together, to successive overloaded-branch removals. Once-through river thermal limits, basin-scale drought hydrology, AC security analysis and electromechanical transients are out of scope.

The model couples four layers without forcing a common time step, following co-simulation practice for heterogeneous domains [34, 35] (Fig. 1). The first layer supplies quasi-steady equipment maps for tower effectiveness–NTU, condenser UA–LMTD and pump head/NPSH. The second layer introduces first-order lags on tower outlet temperature, condenser saturation temperature, circulating-water flow and optional wet-bulb temperature. The third layer applies operator SOP and protection logic that converts thermal–hydraulic state into delivered power and a unique trip label. The fourth layer is event-driven DC cascading that consumes end-of-contingency or dual-unit generation schedules. A single shared step size is rejected because inventory, thermal and hydraulic states evolve on incompatible scales; the layered interface keeps each process at its own rate while preserving event alignment at trip or schedule endpoints.

Parameters follow a five-class evidence hierarchy recorded in the parameter registry (Table A1, Appendix A). Class G1 denotes thermodynamic and water-balance conservation that constrains design-point closure; G2 covers standards and engineering design norms for recirculating cooling and condensers [18, 28]; G3 draws on published literature and manufacturer-typical curves; G4 denotes transparent scenario assumptions for geometry, operating rules and protection set-points that cannot be uniquely fixed from the open literature; and G5 denotes sensitivity and probabilistic propagation used to test conclusion robustness. The mother archetype is a 500 MWe wet-cooled coal unit. Intensive quantities are held fixed under capacity scaling \(s = P/P_\mathrm{ref}\), while circulating-water design flow and basin plan area scale linearly with \(s\). Numerical design-point closure and network ratings are reported in Section 3. No site historian is fitted; all parameters carry the status `reference_template_not_site_measured`.

> **[Fig. 1. Four-layer coupling architecture: quasi-steady equipment maps → first-order thermal/hydraulic lags → operator SOP and protection → event-driven DC cascading.]**
> *(See `Methods_figures.html`, panel 1)*

### 2.2 Steam rejection, cooling tower and condenser

Condenser heat rejection is obtained from net electrical output through

\begin{equation}
Q_c(P) = f_\mathrm{cond}\, P \left( \frac{1}{\eta_\mathrm{net}(P)} - 1 \right),
\end{equation}

where \(\eta_\mathrm{net}(P)\) includes a quadratic part-load heat-rate penalty and \(f_\mathrm{cond}\) is the condenser waste-heat fraction. Under ride-down operation, \(Q_c\) tracks delivered \(P\); under hold-load, the steam-side heat input is frozen at its pre-contingency value so that operator policy enters the heat balance rather than being applied only as a post-hoc derating factor.

Wet-tower steady performance uses the effectiveness–NTU method of Jaber and Webb [19]. Relative to a full Poppe formulation, e-NTU shares Merkel's principal simplifications and is appropriate when the emergency outputs of interest are cold-water temperature and approach rather than exhaust-air humidity [20–22]. Design range and approach invert a reference NTU, and off-design performance is computed as

\begin{equation}
\mathrm{NTU} = \mathrm{NTU}_\mathrm{des}\, K_\mathrm{tower} \left( \frac{G_\mathrm{air}/G_w}{(G_\mathrm{air}/G_w)_\mathrm{des}} \right)^n,
\end{equation}

where \(K_\mathrm{tower}\) is the tower characteristic multiplier held at baseline 1.0 and varied only in uncertainty analysis, \(G_\mathrm{air}/G_w\) is the air-to-water mass flow ratio, and \(n\) is the off-design exponent. Effectiveness yields the quasi-steady tower outlet \(T_\mathrm{in}^*\), which is then tracked by a first-order lag \(\tau_\mathrm{tower}\) consistent with minutes-scale wet cold-end thermal response [23].

The condenser follows HEI design semantics [18, 26, 27]. Design duty, range and terminal temperature difference (TTD) invert a reference UA, and off-design performance is computed as

\begin{equation}
\mathrm{UA} = \mathrm{UA}_\mathrm{des}\, f_\mathrm{cl}\, x^m,
\end{equation}

so that TTD emerges as an output rather than a prescribed input. Saturation temperature and backpressure follow \(T_\mathrm{sat} = T_\mathrm{out} + \mathrm{TTD}\) and \(p_b = p_\mathrm{sat}(T_\mathrm{sat}) + p_\mathrm{air}\). A first-order lag on \(T_\mathrm{sat}\) with time constant \(\tau_\mathrm{cond}\) represents condenser thermal inertia. Electrical capability is obtained from the backpressure correction in Section 2.4; circulating-water flow is not allowed to scale electrical output by a direct proportion, because that shortcut bypasses the condenser–vacuum pathway that governs emergency trips.

### 2.3 Circulating pumps, basin inventory and water balance

The physical cold-end loop—from condenser steam rejection through tower heat rejection to circulating-pump recirculation and basin inventory—is shown in Fig. 2. Pump capability combines a design-anchored head–system intersection with NPSH margin in the sense of ANSI/HI 9.6.1 [29]. Falling basin level raises static lift and reduces available NPSH. Under a pump contingency of fractional capacity loss \(s\), the target circulating-water fraction is

\begin{equation}
x_\mathrm{tgt} = (1-s)\, x_\mathrm{hyd},
\end{equation}

where \(x_\mathrm{hyd}\) is the hydraulic flow fraction determined by pump–system head intersection and NPSH availability. The actual circulating-water fraction \(x\) tracks \(x_\mathrm{tgt}\) with a first-order time constant \(\tau_\mathrm{pump}\), representing combined pump rundown inertia and pipe-flow smoothing at circulating-water scale; this lag is retained because circulating-water pump trips can drive condenser pressure toward protection set-points on second-to-minute horizons [47]. A legacy linear level-band map that converts basin level directly into flow fraction is retained only as a black-box benchmark in Section 2.7, not as the mechanistic default.

Evaporation, drift and blowdown close the water balance. Evaporation is computed from tower heat balance as \(E = f_\mathrm{evap}\, Q_c / (\rho h_{fg})\), drift as \(D = r_\mathrm{drift}\, Q_{cw}\), and blowdown \(B\) from the cycles-of-concentration salt balance used in recirculating-system design practice [28]. Healthy makeup satisfies \(M = E + B + D\). A constant makeup-fraction shortcut is rejected because it breaks heat–water consistency at the design point and under load change.

Explicit basin geometry yields the inventory state equation

\begin{equation}
A \frac{\mathrm{d}H}{\mathrm{d}t} = -(E + B + D - M_\mathrm{ext}),
\end{equation}

where \(A\) is basin plan area and \(H\) is water level. Hold-up hours are a diagnostic output derived from inventory and loss rate, not an input that manufactures volume. Under makeup interruption, the default emergency policy isolates blowdown after a short detection delay; maintaining salt-balance blowdown throughout is the no-intervention counterfactual. Only makeup interruption activates the inventory drain equation; pump and wet-bulb contingencies alter thermal–hydraulic state without draining the basin ODE.

> **[Fig. 2. Wet-recirculating cold-end system schematic: condenser → circulating water → cooling tower → basin inventory → pumps.]**
> *(See `Methods_figures.html`, panel 2)*

### 2.4 Capability, operator response and protection

Turbine electrical capability uses a piecewise backpressure correction. Near-design sensitivity is taken of order \(0.5\)–\(1.5\%\) per kPa as a G3 template range for backpressure–output coupling, and the archetype uses \(0.7\%\) per kPa on the first segment and \(1.4\%\) per kPa on the high-backpressure segment; following Arastou et al. [25], these \(k_p\)-class coefficients are treated as environmentally uncertain and are varied in sensitivity analysis rather than presented as identified plant constants. Delivered power equals the ramp-limited tracking of

\begin{equation}
P_\mathrm{capability} = \min\left( P_0,\, P_\mathrm{thermal}(p_b),\, P_\mathrm{SOP}(H) \right)
\end{equation}

under ride-down operation, or of thermal capability alone under hold-load. The low-level SOP linearly reduces allowable capacity from rated to technical minimum as basin level falls from the SOP start level to the pump trip level. Delivered power therefore changes at a constrained ramp rate rather than jumping instantaneously to the capability surface.

Protection records exactly one trip mechanism among four possibilities: `pump_level` when basin level reaches the pump low-level set-point; `pump_cavitation` when hydraulic flow fraction falls below the NPSH-limited floor; `backpressure_protection` when condenser pressure exceeds the low-vacuum set-point for its specified delay; and `technical_minimum` when ride-down cannot sustain output above the technical minimum. Unique labels are required so that Results can attribute each contingency to a single mechanism rather than to an unordered conjunction of alarms.

### 2.5 Multi-timescale integration and quasi-static control

Plant-boundary thermal dynamics settle over minutes to hours after load or ambient disturbances [23, 24], whereas pump hydraulics and vacuum protection act on seconds to minutes [47]. The integrator therefore uses heterogeneous rates rather than a single stiff step across all states (Fig. 3). The slow layer evolves basin level through the inventory ODE and, when applicable, wet-bulb temperature through a first-order environmental trajectory. The intermediate layer updates tower outlet, condenser saturation temperature, delivered power and SOP constraints at a 1 s time step with the thermal lags of Section 2.2. The fast layer resolves circulating-water flow tracking and vacuum-protection delay. The event layer triggers instantaneous DC cascading evaluation when a unit trips or when dual-unit schedules reach their end states. Numerical horizons and output sampling for each contingency class are specified in Section 3.

As a methodological control for RQ3, a quasi-static twin sets all thermal and pump time constants to zero. Tower outlet, condenser saturation temperature, circulating-water flow and wet-bulb trajectory then jump to their quasi-steady targets at each step. The full circulating-water pump-outage pair—dynamic versus quasi-static—tests whether second-to-minute lags are load-bearing for fast hydraulic contingencies, in the spirit of multi-rate co-simulation arguments [34–36].

> **[Fig. 3. Multi-timescale layered integration: slow (hourly inventory) → intermediate (minute thermal) → fast (second hydraulic/protection) → event (grid cascading).]**
> *(See `Methods_figures.html`, panel 3)*

### 2.6 Transmission-level cascading: DC power flow and successive overload tripping

The transmission layer uses MATPOWER-aligned IEEE 39-bus parameters [32] in a DC power-flow formulation. Nodal active-power injections are assembled from generator outputs and bus loads, the reduced non-slack network equation \(B\theta = P\) is solved, and line flows follow from voltage-angle differences and line reactances.

Overloaded branches are identified when absolute flow exceeds the line thermal rating. At each iteration, all currently overloaded branches are removed simultaneously, the B-matrix is rebuilt without the failed lines, and the DC power flow is re-solved until no new overload appears (Fig. 4). This simultaneous-removal convention follows DC cascading simplifications used in network-level adequacy studies [30, 31, 48]; sequential relay-selective tripping with intentional time delays is out of scope, and cascade depth is therefore an order-of-magnitude estimate rather than a protection-sequence forecast.

Coupled wet units are capacity-scaled instances of the 500 MWe archetype mapped to the two wet-recirculating buses defined in Section 3. Dual-unit schedules probe common-mode cooling loss: both units driven to zero capability by pump trip, both by makeup interruption, or one by each mechanism. A single-unit trip is retained as the negative cascade probe inside N-1 margin. Remedial action schemes, automatic generation control and AC voltage collapse are not modelled [33]. The coupling is one-way from \(P_\mathrm{avail}(t)\) into the cascading layer.

> **[Fig. 4. Event-driven DC cascading algorithm flow chart: injection update → DC power flow → overload detection → simultaneous removal → iterate.]**
> *(See `Methods_figures.html`, panel 4)*

### 2.7 Contingency matrix, uncertainty protocol and verification

The initiating contingencies form a minimum set that activates distinct mechanistic pathways (Table A2, Appendix A). Makeup interruption is evaluated under blowdown isolation versus maintenance, combined with ride-down versus hold-load operation. Full circulating-water pump outage is evaluated under both dynamic and quasi-static integration to isolate the multi-timescale effect. Partial pump outage at \(50\%\) and \(30\%\) capacity loss under ride-down probes sustained derating without trip. Wet-bulb rise of \(+6\,\mathrm{K}\) with first-order lag probes environmental approach stress. Single-, dual- and mixed-unit cascade feeding probes the boundary between absorbed unit events and network cascades.

Black-box benchmarks encode the same initiating stress with four simplified conventions common in adequacy studies: instantaneous trip at \(t = 0^+\); fixed hold-up time followed by trip; linear derate to technical minimum; and a linear level-band pump map. These shapes supply reference trajectories against which the mechanistic \(P_\mathrm{avail}(t)\) paths are compared; they are definitions for RQ3, not empirical plant outage statistics.

Uncertainty propagation proceeds in four stages. One-at-a-time sweeps assess individual-parameter influence on trip time and delivered energy. Morris screening ranks influential inputs across the design space [37, 38]. Scrambled Sobol total-order indices quantify main effects and interactions [39–41]. Latin-hypercube Monte Carlo then generates scenario envelopes for trip time, delivered energy and selected power samples. Reported P05–P95 bands are envelopes from transparent input ranges, not plant-specific confidence intervals [41, 42]. Verification comprises six checks: design-point heat and water balance closure; unique trip labels for each contingency; black-box benchmark comparison; dynamic versus quasi-static control pairs; cascade probes on single- and dual-unit schedules; and OAT sensitivity sweeps. No historian fitting is claimed.

---

## 3. Generic archetype and case setup

### 3.1 500 MWe wet-recirculating archetype

The reference unit is a 500 MWe net wet-recirculating coal-fired archetype constructed as a literature- and standard-anchored engineering template rather than a historian calibration of any named plant. Intensive design quantities follow the five-class evidence hierarchy in Section 2.1 and are recorded in the parameter registry (Table A1, Appendix A). Under capacity scaling \(s = P/P_\mathrm{ref}\), intensive set-points remain fixed, while circulating-water design flow and basin plan area scale linearly with rated power so that mapped IEEE 39 units inherit the same cold-end physics at different ratings. The archetype is the design-closure and calibration basis of this study; contingency outcomes in Section 4 are reported for the mapped grid units of Section 3.2, which are capacity-scaled instances of it.

Design-point closure at the reference wet-bulb \(T_{wb} = 20^\circ\mathrm{C}\) is summarized in Table 2. Condenser heat-rejection duty, circulating-water flow, temperature profile, evaporation–blowdown–drift makeup components and basin inventory are mutually consistent through heat and water balance under the G1 closure rules of Section 2. Derived hold-up (3.29 h), obtained as usable basin volume divided by the design makeup rate, is reported only as a diagnostic ratio; it is not imposed as a manufactured trip time in any contingency.

**Table 2.** Design-point closure of the 500 MWe wet-recirculating archetype (`reference_template_not_site_measured`).

| Quantity | Symbol | Value |
|---|---|---|
| Net rated output | \(P_\mathrm{rated}\) | 500 MW\(_e\) |
| Net design efficiency | \(\eta_\mathrm{net}\) | 0.38 |
| Condenser heat rejection | \(Q_c\) | 750.5 MW\(_\mathrm{th}\) |
| Circulating-water design flow | \(Q_{cw}\) | 15.77 m³/s |
| Cold-water inlet temperature | \(T_\mathrm{in}\) | 25.55 °C |
| Hot-water outlet temperature | \(T_\mathrm{out}\) | 36.97 °C |
| Saturation temperature | \(T_\mathrm{sat}\) | 40.47 °C |
| Backpressure | \(p_b\) | 7.56 kPa |
| Tower approach | \(\Delta T_\mathrm{app}\) | 5.55 °C |
| Condenser TTD | \(\mathrm{TTD}\) | 3.50 °C |
| Evaporation rate | \(E\) | 0.253 m³/s |
| Blowdown rate | \(B\) | 0.084 m³/s |
| Drift rate | \(D\) | 0.0008 m³/s |
| Makeup rate | \(M\) | 0.338 m³/s |
| Basin plan area | \(A\) | 1600 m² |
| Normal / trip level | \(H_0 / H_\mathrm{min}\) | 3.50 / 1.00 m |
| Usable inventory (normal − trip) | \(\Delta V\) | 4000 m³ |
| Derived hold-up (diagnostic) | \(\tau_\mathrm{holdup}\) | 3.29 h |

### 3.2 IEEE 39-bus network and mapped wet units

The transmission case uses the MATPOWER-aligned IEEE 39-bus New England network [32], comprising 39 buses, 10 synchronous generators and 46 branches (34 lines and 12 transformer branches). The network is synthetic and does not represent a real interconnection; mapped machines are treated as equivalent generators without unit-specific fuel or emission constraints.

Two generators are designated as wet-recirculating cooling units and scaled from the 500 MWe archetype at their case rated capacities: Bus 33 at 652 MW (\(s = 1.304\)) and Bus 34 at 508 MW (\(s = 1.016\)). Both inherit the same cold-end parameters, protection set-points and operator policies as the reference template after capacity scaling, so their cold-end trip times and trip mechanisms are identical and their powers scale with rated capacity; reported results are therefore given for these mapped units rather than for the 500 MWe archetype. The remaining eight generators (buses 30–32 and 35–39) are treated as non-cooling-constrained thermal units with fixed outputs, and Bus 31 is the slack bus. Aggregate system load is 6254.2 MW on 21 load buses. Load levels are evaluated at three uniform perturbation factors—\(1.00\times\) (base), \(1.15\times\) (moderate stress) and \(1.20\times\) (high stress)—applied to all load buses. Generator and load totals are summarized in Table 3; the network topology and the two mapped wet units are shown in Fig. 5.

**Table 3.** IEEE 39-bus generator and load summary.

| Type | Count | Buses | Total capacity / load |
|---|---|---|---|
| Generators (total) | 10 | 30–39 | 7367.0 MW |
| &nbsp;&nbsp;Wet-recirculating coupled units | 2 | 33, 34 | 1160.0 MW (652.0 + 508.0) |
| &nbsp;&nbsp;Other thermal units | 8 | 30, 31, 32, 35–39 | 6207.0 MW |
| Load buses | 21 | 1, 3, 4, 7, 8, 9, 12, 15, 16, 18, 20, 21, 23–29, 31, 39 | 6254.2 MW |
| Branches (34 lines + 12 transformer branches) | 46 | — | thermal ratings 480–1800 MVA |

Capacities and ratings are the MATPOWER case39 values [32]: generator \(P_\mathrm{max}\), bus \(P_\mathrm{d}\) and branch `rateA`. The solved case dispatches 6297.9 MW against the 6254.2 MW load, the difference being losses in the original AC solution of the case file. Both the event-driven cascading layer and the DC-OPF adequacy layer operate on this network; the adequacy layer takes the pandapower case39 derivative, which carries the same 46 electrical branches partitioned as lines and transformers.

> **[Fig. 5. IEEE 39-bus New England network topology; Buses 33 and 34 highlighted as the two mapped wet-recirculating cooling units.]**
> *(See `Fig5_ieee39_topology.html`)*

### 3.3 Simulation horizon and scenario configuration

Plant-boundary contingencies are integrated on contingency-specific horizons chosen to resolve the governing time scale. Makeup-interruption cases (S1a/S1b/C1) run for 0–8 h from design steady state; full circulating-pump outages (S2/S2qs) run for 0–1 h so that second-to-minute vacuum evolution remains resolved. Unless otherwise stated, the reference wet-bulb is \(20^\circ\mathrm{C}\). The plant integrator uses a 1 s time step, and output states are sampled every 60 s for trajectory reporting. The DC cascading layer is event-triggered: it evaluates the network when a unit trips or when dual-unit schedules reach their end-of-contingency capability state, consistent with the multi-timescale interface in Section 2.5.

The primary contingency set and pathway labels follow Table A2 and the definitions in Section 2.7, covering makeup interruption, full and partial pump outage, wet-bulb rise, and single-/dual-/mixed-unit cascade feeding. Black-box benchmark encodings are evaluated on the same 0–8 h horizon used for the mechanistic makeup comparisons so that delivered-energy differences share a common window. Uncertainty propagation and verification procedures remain those of Section 2.7 and are not repeated here. All case parameters carry the status `reference_template_not_site_measured`.

---

## 4. Results

### 4.1 Makeup interruption: progressive inventory failure (RQ1)

Using the mapped units of Section 3.2 (primary unit Bus 33, 652 MW), makeup interruption under ride-down with blowdown isolation (S1a) began derating at approximately 2.56 h once basin level crossed the operator shed-start threshold, and tripped on `pump_level` at 5.07 h (304 min) (Fig. 6). Maintaining salt-balance blowdown throughout (S1b) advanced the same inventory-limited trip to 3.88 h (233 min)—about 71 min earlier—because the retained blowdown stream increased net water loss under zero external makeup. Hold-load operation with blowdown isolation (C1) tripped at 4.29 h (258 min), between S1a and S1b. Simulated trip times differed from the diagnostic hold-up of 3.29 h in Table 2, confirming that hold-up must not be treated as a manufactured trip input.

At the S1a trip, circulating-water fraction remained near 0.93 and condenser backpressure stayed below the template low-vacuum set-point (15 kPa) on all makeup-interruption paths, so failure was inventory-limited rather than flow- or vacuum-limited. Ride-down lengthened the resilience window relative to hold-load by reducing evaporative loss as delivered power fell; over the common 0–8 h horizon, however, delivered energy on the Bus 33 unit was 2748 MWh under ride-down versus 2792 MWh under hold-load, showing that a later trip need not imply more delivered energy. Wet-bulb rise of \(+6\,\mathrm{K}\) (S4) produced no trip and settled at 640 MW (\(-1.8\%\)) on Bus 33 and 499 MW on Bus 34, consistent with approach stress as sustained derating rather than an initiating fault. Table 4 summarises cold-end outcomes across the contingency matrix.

> **[Fig. 6. Delivered-power trajectories under makeup interruption on the primary mapped unit (Bus 33, 652 MW): S1a ride-down + isolate blowdown (5.07 h trip), S1b ride-down + maintain blowdown (3.88 h trip), C1 hold-load (4.29 h trip).]**
> *(See `Results_figures.html`, panel 1)*

**Table 4.** Cold-end contingency outcomes on the two mapped wet-recirculating units (Bus 33, 652 MW; Bus 34, 508 MW). Trip times and mechanisms are identical across the two units because both inherit the same cold-end parameter package and differ only by capacity scaling; the 500 MWe archetype of Table 2 is the calibration basis, and the same percentage derates appear on it.

| ID | Contingency / policy | Trip mechanism | \(t_\mathrm{trip}\) | \(P_\mathrm{end}\), Bus 33 (MW) | \(P_\mathrm{end}\), Bus 34 (MW) |
|---|---|---|---|---|---|
| S1a | Makeup; isolate blowdown; ride-down | `pump_level` | 5.07 h (304 min) | 0 | 0 |
| S1b | Makeup; maintain blowdown; ride-down | `pump_level` | 3.88 h (233 min) | 0 | 0 |
| C1 | Makeup; isolate; hold-load | `pump_level` | 4.29 h (258 min) | 0 | 0 |
| S2 | Full pump outage; dynamic integration | `backpressure_protection` | 0.47 min | 0 | 0 |
| S2qs | Full pump outage; quasi-static (C2 control) | `backpressure_protection` | 0.05 min | 0 | 0 |
| S3a | −50% pump capacity; ride-down | none | — | 616 | 480 |
| S3b | −30% pump capacity; ride-down | none | — | 640 | 499 |
| S4 | Wet-bulb rise +6 K; ride-down | none | — | 640 | 499 |

### 4.2 Pump contingencies: why multi-timescale matters (RQ1+RQ3)

Full circulating-water pump outage under dynamic integration (S2) produced a `backpressure_protection` trip at 0.47 min (≈28 s) (Fig. 7). The quasi-static twin (S2qs), with all thermal and pump time constants set to zero, tripped on the same mechanism at 0.05 min (≈3 s)—nearly an order of magnitude earlier. The two trajectories share the same terminal label and the same qualitative shape of rapid backpressure rise followed by protection activation, but differ in the interval over which that rise unfolds.

Freezing first-order lags is therefore not a harmless numerical convenience for fast hydraulic contingencies. Retaining \(\tau_\mathrm{pump} = 10\,\mathrm{s}\) and \(\tau_\mathrm{cond} = 90\,\mathrm{s}\) extends the pre-trip window by roughly a factor of ten relative to the quasi-static twin; jumping directly to no-flow targets advances the protection trigger and would mis-time both an operator response window and any cascading event keyed to unit trip.

Partial circulating-pump capacity loss under ride-down did not trip within the 8 h horizon (Fig. 8). A \(-50\%\) pump outage settled at 616 MW (\(-5.6\%\)) on Bus 33 and 480 MW on Bus 34, and a \(-30\%\) outage at 640 MW (\(-1.8\%\)) and 499 MW respectively. Because the derate is a backpressure effect, the same percentage losses appear on the 500 MWe calibration archetype, where the two cases settle at 472 MW and 491 MW. The hold-load counterpart of the \(-50\%\) case tripped on backpressure at 5.2 min, confirming that operator response mode belongs inside the contingency definition: the same equipment fault yields sustained derating under ride-down but a protection trip under hold-load.

> **[Fig. 7. Full circulating-pump outage: dynamic integration (0.47 min trip) vs quasi-static control (0.05 min trip) — backpressure evolution over time.]**
> *(See `Results_figures.html`, panel 2)*

> **[Fig. 8. Sustained derating scenarios on the primary mapped unit (Bus 33, 652 MW): S3a (−50% pump → 616 MW), S3b (−30% pump → 640 MW), S4 (+6 K wet-bulb → 640 MW).]**
> *(See `Results_figures.html`, panel 3)*

### 4.3 Cascading is a common-mode outcome (RQ2)

On the synthetic IEEE 39-bus network of Section 3, a single-unit full trip at Bus 33 (G1)—whether driven by pump outage or makeup interruption—removed zero transmission branches under the cascading rule (Fig. 9; Table 5). Section 4.4 shows that this is not the same as an event with no system consequence at the adequacy tier, where branch ratings enter as constraints rather than as trip triggers. Dual-unit schedules that drove both mapped wet units (Buses 33 and 34) to zero capability—dual pump trip (G2), dual makeup trip (G3) and mixed pump-plus-makeup (G4)—each removed 13 overloaded lines in two successive stages under the simultaneous-removal DC cascading rule of Section 2.6. Dual partial derating at the S3a level (\(-50\%\) pump on both units) did not cascade.

> **[Fig. 9. Cascading outcomes: G1 single-unit trip (0 lines removed), G2/G3/G4 dual-unit collapse (13 lines, 2 stages), dual partial derate (0 lines).]**
> *(See `Results_figures.html`, panel 4)*

**Table 5.** Cascading outcomes on synthetic IEEE 39.

| ID | Capability schedule | Cascade? | Lines removed | Stages |
|---|---|---|---|---|
| G1 | Bus 33 → 0 MW (single-unit trip) | No | 0 | 0 |
| G2 | Buses 33 & 34 → 0 MW (dual pump trip) | Yes | 13 | 2 |
| G3 | Buses 33 & 34 → 0 MW (dual makeup trip) | Yes | 13 | 2 |
| G4 | Bus 33 pump + Bus 34 makeup → 0 MW | Yes | 13 | 2 |
| — | Dual S3a-level derate only (−50% pump each) | No | 0 | 0 |

Cascade depth was identical across G2, G3 and G4 on this network, indicating that the outcome depended primarily on whether total wet-unit capability loss crossed the N-1 absorption threshold, not on the initiating mechanism or on the time trajectory leading to zero. Together with the non-cascade G1 and dual-derate cases, these results bound the claim: under the stated DC cascading convention, cooling contingencies became cascading outages only when common-mode capability collapse exceeded system absorption.

### 4.4 Black-box outage shapes are not uniformly conservative (RQ3)

For the makeup–adequacy comparison on the primary mapped unit (Bus 33, 652 MW) at \(1.15\times\) case load over 0–8 h, incremental unserved energy varied by a factor of about 2.1 across encoding conventions (Fig. 10). Instantaneous trip at \(t = 0^+\) produced 4634 MWh of incremental unserved energy, more than twice the mechanistic ride-down value of 2169 MWh. Linear derating to technical minimum yielded 3266 MWh, fixed inventory hold-up followed by trip 2739 MWh, and the legacy linear level-band pump model 2529 MWh; mechanistic hold-load produced 2163 MWh. Repeating the comparison on the second mapped unit (Bus 34, 508 MW) preserved the ordering and the contrast, with 3560 MWh for instantaneous trip against 1665 MWh for mechanistic ride-down.

> **[Fig. 10. Incremental unserved energy across black-box encoding conventions vs mechanistic trajectory: primary mapped unit Bus 33 (652 MW), 1.15× load, 0–8 h.]**
> *(See `Results_figures.html`, panel 5)*

Relative to instantaneous trip, mechanistic ride-down was approximately 53% lower at this \(1.15\times\) load level, with the overstatement concentrated in the early hours. The conversion from a plant event into system unserved energy is conditioned jointly on demand level, unit capacity and network position. At \(1.00\times\) base load the Bus 33 unit already added 122 MW of shed, because the departure of its 632 MW injection loads the 2–3 corridor to its 500 MVA rating; the smaller Bus 34 unit added 8 MW at the same demand level. Generic capacity margin is therefore not a sufficient screen: the same cold-end fault is absorbed at one location and converts into unserved load at another. Black-box encodings are also not uniformly conservative in this case: instantaneous trip overstates early energy shortfall, while fixed-hold-up and linear-derate shapes can overstate or understate depending on the comparison baseline.

### 4.5 Sensitivity analysis: controlling parameters and mechanism robustness

One-at-a-time sweeps on the S1a makeup path showed that tower characteristic multiplier \(K_\mathrm{tower}\) and condenser cleanliness \(f_\mathrm{cl}\) changed trip time by less than 1 min, whereas evaporative heat fraction and basin plan area shifted trip time by tens of minutes. On the S2 pump-outage path, tower/cleanliness effects were of order one second, while the vacuum set-point moved trip time by tens of seconds. Trip labels remained stable across OAT perturbations (`pump_level` for makeup paths; `backpressure_protection` for full pump loss).

Morris screening and scrambled Sobol total-order indices confirmed the same ranking: inventory and water-balance parameters dominated trip-time variance, while tower and condenser state parameters were secondary. Latin-hypercube Monte Carlo with 384 samples produced a 99.5% majority of `pump_level` trips for the makeup-interruption ensemble, with P05–P95 trip-time bounds of 4.14–6.16 h. These bands are scenario envelopes from transparent input ranges, not plant-specific posteriors. The results support retaining tower degradation and condenser fouling as equation-level uncertain states rather than elevating them to primary initiating contingencies.

---

## 5. Discussion

### 5.1 The contingency-resolved capability pathway

The central advance is not a new heat-transfer correlation but a contingency-resolved capability pathway: the same wet-recirculating cold-end physics yields qualitatively different \(P_\mathrm{avail}(t)\) trajectories according to the initiating event. Makeup interruption drains basin inventory over hours and trips on `pump_level`; full circulating-pump outage collapses flow in seconds and trips on low-vacuum protection; partial pump loss and wet-bulb stress produce sustained derating without trip within the studied horizon. That mechanistic diversity is what availability-factor and black-box outage encodings omit when cooling failure is reduced to a binary generator outage or exogenous derating factor [1, 43, 44].

The hour-scale makeup trip and second-to-minute vacuum trip are consistent in order of magnitude with plant-level wet cold-end dynamics under load or ambient disturbance [23, 24] and with condenser pressure rise after circulating-water pump trips in detailed fault simulations [47]. The contribution here is not to extend those plant-boundary transients for their own sake, but to emit a mechanism-labelled \(P_\mathrm{avail}(t)\) that adequacy and cascading layers can consume, and to show how operator policies (ride-down versus hold-load; blowdown isolation versus maintenance) shift both the trajectory and its terminal trip time.

### 5.2 Multi-timescale necessity and operational implications

The S2–S2qs pair shows that multi-timescale integration is load-bearing for fast hydraulic contingencies rather than a numerical refinement. Eliminating \(\tau_\mathrm{pump}\) and \(\tau_\mathrm{cond}\) advances the vacuum trip by nearly an order of magnitude and would mis-time any downstream cascading trigger keyed to unit loss. This result gives a concrete wet-recirculating instance of the broader multi-rate co-simulation argument [34–36].

The ride-down versus hold-load comparison carries a related operational implication. Ride-down extended the resilience window but did not increase 0–8 h delivered energy on the mapped units (2748 MWh under ride-down versus 2792 MWh under hold-load on the Bus 33 unit), because reduced evaporative loss during derating was offset by lost thermal output before the delayed trip. Trip time alone is therefore a poor operational objective; the integrated energy trajectory, together with the time available for makeup restoration or re-dispatch, governs system impact.

### 5.3 Common-mode cascading: planning implications

The IEEE 39 experiments reframe the planning question from whether cooling outages cause blackouts to under what common-mode conditions they cross the N-1 absorption threshold. On this synthetic network and under the stated DC simultaneous-removal rule, a single wet-unit trip removed no branch, whereas dual-unit capability collapse removed 13 lines in two stages with identical depth across pump-driven, makeup-driven and mixed schedules. Cascade outcome tracked whether total wet-unit loss exceeded absorption, not which cold-end mechanism produced the loss [30, 31, 48]. Branch-removal absorption and adequacy-tier absorption are distinct questions: at \(1.00\times\) demand the same single-unit loss produced 122 MW of shed in the OPF layer without removing any branch, because the binding limit there is a transfer constraint on the 2–3 corridor rather than an overload cascade.

The corresponding planning implication is that cooling-system independence between neighbouring wet units can matter as much as absolute reserve margin. Shared makeup sources, shared auxiliary power or shared protection logic can turn two unit assets into one common-mode contingency. The present results do not support a universal claim that cooling faults cause cascading blackouts; they support the narrower claim that, when common-mode cooling loss pushes aggregate wet-unit capability beyond N-1 margin on this test system, successive branch overload follows. The non-cascade G1 and dual-derate cases bound that claim from below.

### 5.4 Limitations and future work

Several boundaries follow from the evidence base and modelling choices. Parameters remain literature- and standard-anchored templates (`reference_template_not_site_measured`), not historian-calibrated values for a named station. The cascading layer is a DC simultaneous-removal estimate without remedial actions, AGC or AC voltage collapse, so the reported 13-line depth is an order-of-magnitude indicator rather than a relay-sequence forecast. Coupling is one-way from plant to grid. The tower model uses e-NTU/Merkel simplifications appropriate for cold-water temperature and approach, not full Poppe humidity closure [20–22]. Monte Carlo P05–P95 bands are scenario envelopes from transparent ranges, and the approximately 53% unserved-energy contrast is specific to the \(1.15\times\) load case, the mapped units and the 0–8 h horizon.

Three extensions would resolve the most consequential uncertainties. Historian calibration of thermal time constants and protection set-points would replace template \(\tau\) and trip settings with site estimates. Two-way co-simulation with remedial schemes would move the cascading outlet beyond DC successive removal. Expanding the contingency set to once-through thermal limits, intake blockage and compounded heat-wave–drought stress would broaden coverage beyond recirculating-tower emergencies.

---

## 6. Conclusions

This study opened the wet-recirculating cold-end black box and linked emergency contingencies to grid-level cascading through mechanism-resolved \(P_\mathrm{avail}(t)\) on a synthetic IEEE 39-bus case. Three findings answer the research questions within the stated modelling boundaries.

Different initiating contingencies produce qualitatively distinct capability trajectories (RQ1): makeup interruption yields hour-scale inventory-limited `pump_level` trips whose timing depends on blowdown and operator policy; full circulating-pump outage yields second-scale `backpressure_protection` trips; partial pump loss and wet-bulb stress yield sustained derating without trip over the studied horizons. Cascading is a common-mode, threshold-conditioned outcome rather than an automatic consequence of any cooling fault (RQ2): on the test network under DC simultaneous branch removal, a single wet-unit trip removed no branch, whereas dual-unit capability collapse triggered successive overload with depth set by total wet-unit loss rather than by the cold-end initiating mechanism. Black-box outage encodings are not uniformly conservative, and multi-timescale integration is methodologically necessary for fast hydraulic contingencies (RQ3): at the studied \(1.15\times\) load level, instantaneous-trip assumptions substantially overstated early incremental unserved energy relative to the mechanistic ride-down path, and a quasi-static twin advanced the full-pump-outage trip by nearly an order of magnitude.

Adequacy and resilience studies should therefore not reduce cooling-water loss to a binary generator outage or a fixed derating factor without checking mechanism, time scale and common-mode structure. The present templates, DC cascading layer and case-specific unserved-energy contrasts bound that recommendation; plant-calibrated parameters and AC security assessment with remedial actions remain necessary before site-level prediction.


---

## References

1. Wang Y, Zhou Z, Betrie G, Zhang K, Yan E. Appl Energy 2025;377:124440. https://doi.org/10.1016/j.apenergy.2024.124440
2. Byers EA, Coxon G, Freer J, Hall JW. Nat Commun 2020;11:2239. https://doi.org/10.1038/s41467-020-16012-2
3. van Vliet MTH, Yearsley JR, Ludwig F, Vögele S, Lettenmaier DP, Kabat P. Nat Clim Chang 2012;2:676–81. https://doi.org/10.1038/nclimate1546
4. DeNooyer TA, Peschel JM, Zhang Z, Stillwell AS. Appl Energy 2016;162:363–71. https://doi.org/10.1016/j.apenergy.2015.10.071
5. Shuai H, Li F, Zhu J, Tingen WJ II, Mukherjee S. Appl Energy 2024;363:122977. https://doi.org/10.1016/j.apenergy.2024.122977
6. Macknick J, Newmark R, Heath G, Hallett KC. Environ Res Lett 2012;7:045802. https://doi.org/10.1088/1748-9326/7/4/045802
7. Meldrum J, Nettles-Anderson S, Heath G, Macknick J. Environ Res Lett 2013;8:015031. https://doi.org/10.1088/1748-9326/8/1/015031
8. van Vliet MTH, Wiberg D, Leduc S, Riahi K. Nat Clim Chang 2016;6:375–80. https://doi.org/10.1038/nclimate2903
9. Miara A, Macknick JE, Vörösmarty CJ, Tidwell VC, Newmark R, Fekete B. Nat Clim Chang 2017;7:793–8. https://doi.org/10.1038/nclimate3417
10. Peer RAM, Sanders KT. Environ Res Lett 2016;11:124030. https://doi.org/10.1088/1748-9326/aa51d8
11. Förster H, Lilliestam J. Reg Environ Change 2010;10:327–38. https://doi.org/10.1007/s10113-009-0104-x
12. van Vliet MTH, Vögele S, Rübbelke D. Environ Res Lett 2013;8:035010. https://doi.org/10.1088/1748-9326/8/3/035010
13. Liu L, Hejazi M, Li H, Forman B, Zhang X. Nat Energy 2017;2:17133. https://doi.org/10.1038/nenergy.2017.109
14. Bartos MD, Chester MV. Nat Clim Chang 2015;5:748–52. https://doi.org/10.1038/nclimate2648
15. Burillo D, Chester MV, Ruddell B, Johnson N. Appl Energy 2017;206:267–77. https://doi.org/10.1016/j.apenergy.2017.08.141
16. Pan S-Y, Snyder SW, Packman AI, Lin YJ, Chiang P-C. Water-Energy Nexus 2018;1:26–41. https://doi.org/10.1016/j.wen.2018.04.002
17. Stillwell AS, King CW, Webber ME, et al. Tex Water J 2010;1:33–41. https://doi.org/10.21423/twj.v1i1.1042
18. Heat Exchange Institute. Standards for Steam Surface Condensers. 12th ed. 2017.
19. Jaber H, Webb RL. J Heat Transfer 1989;111:837–43. https://doi.org/10.1115/1.3250794
20. Kloppers JC, Kröger DG. J Eng Gas Turbines Power 2005;127:1–7. https://doi.org/10.1115/1.1787504
21. Kloppers JC, Kröger DG. Int J Heat Mass Transfer 2005;48:765–77. https://doi.org/10.1016/j.ijheatmasstransfer.2004.09.004
22. Kloppers JC, Kröger DG. Appl Therm Eng 2005;25:1325–36. https://doi.org/10.1016/j.applthermaleng.2004.09.003
23. Wang C, Liu M, Zhao Y, Qiao Y, Chong D, Yan J. Energy 2018;145:734–46. https://doi.org/10.1016/j.energy.2017.12.146
24. Wu T, Ge Z, Yang L, Du X. Energy 2019;181:1202–12. https://doi.org/10.1016/j.energy.2019.06.030
25. Arastou A, Ahmadi P, Karrari M. IEEE Syst J 2022;16:2979–88. https://doi.org/10.1109/jsyst.2021.3122228
26. Anozie AN, Odejobi OJ. Appl Therm Eng 2011;31:4083–90. https://doi.org/10.1016/j.applthermaleng.2011.08.014
27. Zeng Z, Meng L, Li X, et al. Appl Therm Eng 2012;40:294–303. https://doi.org/10.1016/j.applthermaleng.2012.02.028
28. GB/T 50102-2014. Code for design of industrial recirculating water cooling. Beijing: China Planning Press; 2014.
29. ANSI/HI 9.6.1. Rotodynamic Pumps—Guideline for NPSH Margin. Parsippany, NJ: Hydraulic Institute.
30. Dobson I, Carreras BA, Lynch VE, Newman DE. Chaos 2007;17:026103. https://doi.org/10.1063/1.2737822
31. Vaiman M, Bell K, Chen Y, Chowdhury B, Dobson I, Hines P, et al. IEEE Trans Power Syst 2012;27:631–41. https://doi.org/10.1109/TPWRS.2011.2177868
32. Zimmerman RD, Murillo-Sánchez CE, Thomas RJ. IEEE Trans Power Syst 2011;26:12–19. https://doi.org/10.1109/TPWRS.2010.2051168
33. Kundur P, Paserba J, Ajjarapu V, et al. IEEE Trans Power Syst 2004;19:1387–401. https://doi.org/10.1109/TPWRS.2004.825981
34. Palensky P, Van Der Meer AA, Lopez CD, Joseph A, Pan K. IEEE Ind Electron Mag 2017;11(1):34–50. https://doi.org/10.1109/MIE.2016.2639825
35. Palensky P, van der Meer AA, Lopez CD, Joseph A, Pan K. IEEE Ind Electron Mag 2017;11(2):6–21. https://doi.org/10.1109/MIE.2017.2671198
36. Barbierato L, Pons E, Bompard EF, et al. IEEE Syst J 2023;17:3354–65. https://doi.org/10.1109/JSYST.2022.3230092
37. Morris MD. Technometrics 1991;33:161–74. https://doi.org/10.1080/00401706.1991.10484804
38. Campolongo F, Cariboni J, Saltelli A. Environ Model Softw 2007;22:1509–18. https://doi.org/10.1016/j.envsoft.2006.10.004
39. Pianosi F, Beven K, Freer J, et al. Environ Model Softw 2016;79:214–32. https://doi.org/10.1016/j.envsoft.2016.02.008
40. Sarrazin F, Pianosi F, Wagener T. Environ Model Softw 2016;79:135–52. https://doi.org/10.1016/j.envsoft.2016.02.005
41. Saltelli A, Sobol’ IM. Reliab Eng Syst Saf 1995;50:225–39. https://doi.org/10.1016/0951-8320(95)00099-2
42. Refsgaard JC, van der Sluijs JP, Højberg AL, Vanrolleghem PA. Environ Model Softw 2007;22:1543–56. https://doi.org/10.1016/j.envsoft.2007.02.004
43. Lubega WN, Stillwell AS. Appl Energy 2018;210:538–49. https://doi.org/10.1016/j.apenergy.2017.06.091
44. Gjorgiev B, Sansavini G. Appl Energy 2018;210:568–79. https://doi.org/10.1016/j.apenergy.2017.09.011
45. Behrens P, van Vliet MTH, Nanninga T, Walsh B, Rodrigues JFD. Nat Energy 2017;2:17114. https://doi.org/10.1038/nenergy.2017.114
46. Kumar Y, Hoesly R, Venkatesh A, Shuster E, Iyengar A. ACS ES&T Water 2022;2:749–58. https://doi.org/10.1021/acsestwater.1c00450
47. Lu C, Yang J, Zhang Q. Energies 2024;17:1210. https://doi.org/10.3390/en17051210
48. Schäfer B, Witthaut D, Timme M, Latora V. Nat Commun 2018;9:1975. https://doi.org/10.1038/s41467-018-04287-5

---

## Appendix A. Supplementary tables

**Table A1.** Key parameter registry of the 500 MWe wet-recirculating archetype.

Evidence classes: G1 = thermodynamic / water-balance conservation closure; G2 = standards & engineering design norms; G3 = published literature / manufacturer typical curves; G4 = transparent scenario assumptions (geometry, operating rules, protection set-points); G5 = sensitivity / probabilistic propagation. All parameters carry status `reference_template_not_site_measured`.

| Parameter | Symbol | Unit | Reference value | Lower bound | Upper bound | Evidence class | Sensitivity treatment |
|---|---|---|---|---|---|---|---|
| Net design efficiency | \(\eta_\mathrm{net}\) | — | 0.38 | 0.30 | 0.48 | G1+G3 | Design-point closure; efficiency envelope |
| Part-load heat-rate penalty | \(\alpha_\mathrm{hr}\) | — | 0.25 | 0.00 | 0.80 | G3+G4 | Scenario-level; not global Sobol core |
| Condenser waste-heat fraction | \(f_\mathrm{cond}\) | — | 0.92 | 0.80 | 0.98 | G1 | Design-point range check |
| Circulating-water design flow | \(Q_{cw,\mathrm{des}}\) | m³/s | 15.77 | 5.0 | 40.0 | G1 | Scales with capacity; design closure |
| Design approach | \(\Delta T_\mathrm{app,des}\) | °C | 5.55 | 2.5 | 8.0 | G1+G2 | Design closure; tower sensitivity |
| Design TTD | \(\mathrm{TTD}_\mathrm{des}\) | °C | 3.50 | 1.5 | 6.0 | G1+G2 | Design closure; condenser sensitivity |
| Tower characteristic multiplier | \(K_\mathrm{tower}\) | — | 1.0 | 0.6 | 1.5 | G3+G4 | OAT + Morris + Sobol + MC |
| Tower NTU off-design exponent | \(n\) | — | 0.45 | 0.0 | 1.0 | G3 | OAT sweep |
| Condenser cleanliness factor | \(f_\mathrm{cl}\) | — | 1.0 | 0.7 | 1.1 | G3+G4 | OAT + Morris + Sobol + MC |
| Condenser UA flow exponent | \(m\) | — | 0.80 | 0.4 | 1.1 | G3 | OAT sweep |
| Air partial pressure | \(p_\mathrm{air}\) | kPa | 0.0 | 0.0 | 1.0 | G4 | Scenario check only |
| Evaporative heat fraction | \(f_\mathrm{evap}\) | — | 0.82 | 0.65 | 0.95 | G1+G3 | OAT + Morris + Sobol + MC |
| Drift fraction | \(r_\mathrm{drift}\) | — | 5×10⁻⁵ | 0.0 | 5×10⁻⁴ | G2+G3 | Fixed low-sensitivity |
| Cycles of concentration | \(N_\mathrm{CoC}\) | — | 4.0 | 2.0 | 8.0 | G1+G2 | Morris + Sobol + MC |
| Backpressure sensitivity (low segment) | \(k_{p,1}\) | 1/kPa | 0.007 | 0.003 | 0.015 | G3 | Mechanism & scenario checks |
| Backpressure sensitivity (high segment) | \(k_{p,2}\) | 1/kPa | 0.014 | 0.005 | 0.030 | G3 | Mechanism & scenario checks |
| Basin plan area | \(A\) | m² | 1600 | 50 | 20000 | G1+G4 | OAT + Morris + Sobol + MC |
| Pump NPSH required (design) | \(\mathrm{NPSHr}_\mathrm{des}\) | m | 8.0 | 3.0 | 20.0 | G3 | Morris + Sobol; cavitation check |
| Pump design head | \(H_\mathrm{pump,des}\) | m | 22.0 | 8.0 | 45.0 | G1+G3 | Pump curve scenario; design closure |
| Static lift (design) | \(H_\mathrm{static,des}\) | m | 10.0 | 3.0 | 35.0 | G1+G4 | Pump curve scenario; level check |
| Tower thermal time constant | \(\tau_\mathrm{tower}\) | s | 300 | 30 | 1800 | G3+G4 | Dynamic trajectory sensitivity |
| Condenser thermal time constant | \(\tau_\mathrm{cond}\) | s | 90 | 10 | 600 | G3+G4 | Dynamic trajectory sensitivity |
| Pump flow tracking time constant | \(\tau_\mathrm{pump}\) | s | 10 | — | — | G4 | Fixed (rundown + water-hammer smoothing) |
| Blowdown detection delay | \(\Delta t_\mathrm{bd}\) | h | 0.25 | — | — | G4 | Fixed operational assumption |
| Low-vacuum set-point | \(p_\mathrm{vac,set}\) | kPa | 15.0 | — | — | G4 | Fixed protection set-point |

---

**Table A2.** Primary contingency matrix and expected mechanistic pathway.

| ID | Initiating event | Operator policy | Blowdown policy | Integration mode | Primary mechanism class | Expected trip label |
|---|---|---|---|---|---|---|
| **S1a** | Makeup water interruption | Ride-down | Isolated | Dynamic | Basin inventory drain | `pump_level` |
| **S1b** | Makeup water interruption | Ride-down | Maintained | Dynamic | Basin inventory drain (faster) | `pump_level` |
| **C1** | Makeup water interruption | Hold-load | Isolated | Dynamic | Basin inventory drain (faster than S1a) | `pump_level` |
| **S2** | Full circulating-pump outage | Ride-down | — | Dynamic | Flow loss → backpressure rise | `backpressure_protection` |
| **S2qs** | Full circulating-pump outage | Ride-down | — | Quasi-static (C2 control) | Flow loss → backpressure rise | `backpressure_protection` |
| **S3a** | −50% pump capacity | Ride-down | — | Dynamic | Sustained derating (no trip) | none |
| **S3b** | −30% pump capacity | Ride-down | — | Dynamic | Sustained derating (no trip) | none |
| **S4** | Wet-bulb temperature +6 K | Ride-down | — | Dynamic | Approach stress (no trip) | none |
| **G1** | Single-unit trip (any mechanism) | — | — | Event DC cascade | N-1 absorption | no cascade |
| **G2** | Dual-unit pump trip (common-mode) | — | — | Event DC cascade | Common-mode overload | successive line trips |
| **G3** | Dual-unit makeup interruption | — | — | Event DC cascade | Common-mode slow derate | successive line trips |
| **G4** | Mixed: pump trip + makeup loss | — | — | Event DC cascade | Asymmetric common-mode | successive line trips |

Black-box benchmark encodings (RQ3 reference points): instantaneous trip at \(t=0^+\); fixed hold-up time followed by trip; linear derate to technical minimum; linear level-band pump map. These are evaluated against mechanistic ride-down / hold-load pairs on the same 0–8 h horizon.

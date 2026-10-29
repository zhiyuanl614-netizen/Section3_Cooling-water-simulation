# Mechanistic modelling of cooling-water systems and the cascading consequences of concurrent supply-line failures in multi-unit power systems

**Authors and affiliations to be assigned**

**Keywords:** cascading failure; cooling-water system; multi-hazard interaction; power system resilience; dependent failures; wet cooling tower; underfrequency load shedding

> **Manuscript conventions.** Figure and table call-outs follow the Nature format
> (Fig. 1 | ...). Figures M1–M5, A1–A3, R1–R3, R5–R8 and D1–D2, together with
> Tables M2–M3, A3, R1–R4 and D1, are generated as editable SVG from
> `src/analysis/build_manuscript_figures.py` and `src/analysis/build_manuscript_tables.py`;
> numbering will be fixed at typesetting.

---

## Abstract

Cooling-water systems are routinely treated as black boxes in hydro–power coupling studies, represented either by fixed coefficients mapping operating state to unit trip times or by imposed failure chronologies. Such representations cannot answer which of a set of thermal constraints binds first, how trip timing responds to redispatch, or whether the timing of one unit's failure alters another's. Here we replace the black box with a mechanistic model of a wet-recirculating cooling system—tracking basin inventory, pump flow availability under cavitation limits, tower effectiveness, condenser heat transfer with thermal inertia, and turbine backpressure capability—and embed it in an event-driven, three-timescale coupling architecture with grid-side frequency dynamics and AC cascade evaluation. We then enumerate all $\binom{6}{1}+\cdots+\binom{6}{6}=63$ combinations in which the independent makeup-water lines of one to six units rupture simultaneously, in a regional setting where units share a water source but not a delivery line.

Across the 63 scenarios, 22 produced hard service loss, of which two are conditional on unproven solver convergence. Hard service loss occurred in 22 of the 48 combinations containing the slack unit G1 and in none of the 15 combinations excluding it, making G1's presence a necessary condition in this operating point; the trigger rate rose monotonically with the number of failed units, from 0% at one unit to 100% at five and six. The condition is necessary but not sufficient: of nine two-unit combinations containing G1, only G1+G2 cascaded. Mechanistic modelling revealed what a black box could not: under concurrent failure, the same unit trips 9.9–45.4% earlier than under isolated failure, because redispatch raises surviving units' output and hence their evaporative demand. Service loss is topological throughout: across the enumeration all 366 lost buses are separated from in-service generation, the unsolvable branch of the criterion never being taken, which reflects in part a test system that remains capacity-rich at every stage. In the canonical case 23 buses are lost with the frequency nadir at 59.36 Hz and underfrequency load shedding inactive, and the loss is produced by cascading overload trips rather than being present at the instant the units are lost.

These results establish cooling-water failure timing as a property of the failure set rather than of the individual unit, and demonstrate that combination-dependent cascade behaviour is inaccessible to black-box treatment. The findings are conditional on the operating point, the capacity position of the test system, the unit subset and the parameter set examined, and do not constitute a replication of dependent-failure theory.

---

## 1. Introduction

Cascading failure in power systems has been defined as "a sequence of dependent failures of individual components that successively weakens the power system"^1^, and it has been the subject of extensive methodological work spanning detailed reconstruction of individual blackouts^2,3^, statistical modelling of outage distributions^4,10^, and reduced-order models intended to explain bulk properties such as critical loading^6,7,8^. A common feature of this body of work is that the initiating disturbance is specified externally: which component fails, and when, is an input rather than an output. This is a defensible simplification for many questions, but it precludes any analysis of whether the *timing* of one failure alters the timing of another—a question that arises whenever several components fail for reasons correlated with the system state they share.

The modelling literature has accordingly pursued several distinct routes, with different implications for what can be asked. Detailed reconstruction of individual events^2,3^ has established the dominant cascade mechanisms, including the protective-relay and voltage-instability contributions documented for the 2003 North American blackout^28^ and in subsequent protection-coordination reviews^35^. Statistical and probabilistic approaches^4,10^ characterize outage distributions and the probability that a disturbance propagates, and graph-theoretic approaches^6^ identify structurally pivotal components from network topology alone. Reduced-order and branching-process models^7,8^ reproduce bulk statistics such as the scale distribution of cascade size, a result consolidated in a dedicated monograph on cascading-failure risk assessment^9^. Benchmarks and validation protocols developed for cascade-analysis tools^3^ have clarified what "validation" can mean in this domain. What these approaches share, for all their differences, is the treatment of the initiating disturbance as given.

It is against this background that two further gaps in the modelling literature become relevant. Recent reviews of cascade-simulation models note that much of the field focuses on fast transients, at the expense of slower process layers whose coupling to the electrical state is often left implicit^4^, and that protection modelling remains an incomplete part of many otherwise sophisticated frameworks^12^. A hybrid architecture that resolves a slow thermal-hydraulic process layer explicitly and couples it to frequency dynamics and AC cross-sections addresses both gaps, and is the architecture adopted here.

Such correlation is the defining feature of a class of hazards that has become increasingly consequential for thermal generation: water availability. Cooling accounts for the large majority of freshwater withdrawal by thermal power generation^18,19,20^, and satellite assessment of global thermal-plant water use confirms that the cooling configuration, rather than the generation technology, dominates water intensity^23^. Regional analyses show that water stress on thermoelectric generation is both substantial and seasonally structured, with many regions already exceeding sustainable supply^21,22^. The regional concentration of water-stressed generation means that multiple units at one site commonly draw on a shared source^21,22^, and the domestic literature has accordingly begun to treat shared water systems as a coupled resource^37,38^. When that source or its delivery infrastructure is impaired, the resulting failures are neither independent nor simultaneous in the way assumed by conventional reliability models. They are *concurrent*: each unit's failure depends on its own thermal state, which evolves in response to a grid operating point that is itself being reshaped by the other units' failures.

Existing treatment of cooling-water constraints in power-system studies has largely followed a **derating** pathway. Unit-level cooling-water availability constraints are imposed, output is reduced accordingly, and the system-level consequences are evaluated through dispatch, congestion and load-curtailment modelling^21^. A parallel line of work in China builds explicit electricity–water cross-layer coupling models for grid vulnerability assessment^37^. This approach is well suited to gradual resource depletion, and the resulting insights into curtailment volumes and regional stress are valuable. It is not, however, structured to answer the question that arises when delivery failure is abrupt and discontinuous: not how much output is lost, but *when* each unit becomes unavailable relative to the others, and whether that relative timing determines whether the disturbance remains local or propagates.

The distinction matters because a unit that trips is not interchangeable with a unit that is derated. A trip removes a generator from the network instantaneously and irreversibly; its contribution cannot be restored by reducing the demand on the remaining cooling water. It also propagates differently: a tripping unit triggers the frequency response, the redispatch and the protection cascades that constitute the machinery of system collapse, whereas a derated unit participates in none of these. The transition from a derating problem to a trip problem is therefore a transition between qualitatively different regimes, and the conditions under which it occurs are not visible to derating-based models. The physical basis for that transition is itself well documented in the cooling-system literature: makeup demand is the sum of evaporation, drift, blowdown and other losses^14,15,16,17^, so that a loss of makeup supply depletes basin inventory on a timescale set by operating load, and the condenser, tower and backpressure response to the resulting flow degradation determine when protection is reached^13^.

A further obstacle has been methodological. Because the consequences of a multi-unit cooling-water failure depend on the relative timing of the individual trips, any model in which trip times are imposed rather than computed cannot exhibit the effects of interest: the combination effect is then a property of the input assumption and not of the system. In probabilistic treatments of dependent failures, this situation is well recognised—the literature distinguishes statistical dependency models, which capture correlations without representing their physical origin, from mechanistic models, which do^24^. Mechanistic dependency models for multi-unit configurations remain scarce^24^, and the regulatory literature provides the corresponding taxonomy: the CCF database and analysis system^26^ and multi-unit PSA methodology^27^, while the common-cause criteria of NUREG/CR-5485^25^ define precisely where a shared-cause event ends and independent-but-concurrent failure begins. The specific case of thermal-hydraulic failure propagation into grid operation has received limited attention relative to the maturity of cascade simulation on the electrical side^30,31^.

This study addresses both obstacles. It pursues two connected objectives.

**First, we construct a mechanistic model of the wet-recirculating cooling system** in which the unit trip time is an emergent property of the simulated thermal state rather than an imposed input. The model resolves the physical chain from basin inventory through pump flow availability, tower performance, condenser heat transfer and turbine backpressure capability to the protection criteria that terminate operation, and it is coupled to grid-side frequency dynamics and AC cascade evaluation through an event-driven architecture. **Second, we use this model to simulate the cascading consequences of concurrent cooling-water system failures** across the complete enumeration of 63 failure sets, and examine what combination-dependent structure emerges that a black-box treatment could not have produced.

The distinction between the two objectives is one of logical dependency, and it is worth making explicit at the outset. The second objective is not well posed without the first: if trip times are imposed, combinations differ only in the inputs they carry, and no question about interaction can be asked. The first objective therefore supplies the precondition for the second, and the second supplies the evidence for the first—if the mechanistic model were to fail to produce combination-dependent structure, the modelling strategy itself would require reassessment.

The contribution of this work is consequently threefold: a mechanistic replacement for the black-box treatment of cooling-water systems, coupling at the level of physical state variables rather than prescribed coefficients; a quantified characterization of how concurrent failure compresses an individual unit's trip timeline relative to its isolated failure, as a consequence of redispatch-driven increases in evaporative demand; and a necessary-but-not-sufficient structural condition governing the onset of hard service loss in the studied operating point, together with the confounds that limit the generality of that condition.

The scope of these claims is deliberately bounded. All scenarios share a single base-case operating point and a six-unit subset of the IEEE 30-bus system^29,30^. Cold-end parameters are anchor values rather than field measurements, and the coupling-side parameters are reference assumptions, with no measured values among them (Methods, Section 2.5.2). The physical background is concurrent but not common-cause failure: the units share a water source, but each makeup line fails independently, and no single upstream event disables all units simultaneously^25,26^. The study does not replicate a dependent-failure theory, nor does it reconstruct a historical blackout^28^; it addresses a bounded question within one operating point — what combination-dependent structure accompanies concurrent cooling-water failure, and under what conditions does it become a cascade.

---

## 2. Methods

### 2.1 Modelling framework and operating point

#### 2.1.1 Problem setting

We consider a region in which several generating units share a common water source while drawing water through individually distinct makeup lines. The failure under study is the concurrent, independent rupture of those makeup lines at a common instant $t_0$. The resulting failure set is therefore concurrent but not common-cause: no single upstream event disables all units simultaneously, and the distinguishing structure of a common-cause event—a shared cause linked by a coupling mechanism acting within an established ^25^—is absent.

This distinction has methodological consequences that determine what can be studied. Under a common-cause loss of supply, all units would fail on a common timeline, and no inter-unit timing structure could arise. Under independent but concurrent failures, each unit's trip time is determined by its own thermal state, and that state depends on the grid operating point, which the other units' failures are concurrently reshaping. The feedback loop that results is the object of interest here.

The closest existing work on this problem applies multi-level cooling-water availability constraints at the unit level and evaluates the resulting output reductions through power-system ^21^. That pathway is well matched to gradual resource depletion. Here, cooling-water failure is not treated as continuous derating but as a discrete event in which cold-end protection actions trip the unit, and the subsequent redistribution of output and its propagation to grid service loss are carried within the same simulation. The consequence of this difference in modelling pathway is that the quantities at issue are failure *chronology* and combination *structure* rather than derating curves.

#### 2.1.2 Test system and unit characteristics

The test system is the ^29,30^: 30 buses, 41 branches, six generators (five PV and one slack), a 100 MVA system base and a total load of 189.2 MW (Fig. A1). Unit bus assignments, rated capacities and base-case active power outputs are given in Table 1 and, in full, in Table R1.

**Table 1 | Unit cold-end characteristics and base-case operating point.**

| Unit | Bus | Type | Rated (MW) | $P_{g0}$ (MW) | Loading (%) | Normal level (m) | Trip level (m) | Basin area factor | CoC | Approach (K) | Cleanliness | $t_{\text{trip}}^{\text{iso}}$ (h) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G1 | 1 | Slack | 80 | 23.54 | 29.4 | 4.2 | 1.00 | 1.20 | 4.5 | 6.0 | 0.94 | 13.7061 |
| G2 | 2 | PV | 80 | 60.97 | 76.2 | 3.6 | 1.10 | 1.10 | 4.0 | 5.0 | 0.95 | 4.6564 |
| G13 | 13 | PV | 40 | 37.00 | 92.5 | 3.2 | 1.20 | 0.85 | 3.5 | 5.5 | 0.92 | 2.3003 |
| G22 | 22 | PV | 50 | 21.59 | 43.2 | 3.5 | 1.00 | 1.00 | 4.5 | 5.8 | 0.88 | 7.0181 |
| G23 | 23 | PV | 30 | 19.20 | 64.0 | 2.9 | 1.15 | 0.90 | 3.0 | 7.0 | 0.90 | 2.7372 |
| G27 | 27 | PV | 55 | 26.91 | 48.9 | 3.8 | 1.00 | 1.15 | 5.0 | 4.5 | 1.00 | 8.4069 |

The initial outputs follow from the base-case AC power flow and serve as the initial conditions for the cold-end state variables. G1 is connected at bus 1 and is the system's slack unit: its active output is determined by the power flow rather than by a prescribed setpoint, whereas the remaining five units operate as PV machines at their specified outputs. This asymmetry is treated explicitly in Section 5.2, where it emerges as a principal confound in the interpretation of results involving G1.

The six units differ systematically in their cold-end characteristics (Fig. A2), and this heterogeneity is a precondition for the combination-level analysis: were the units thermally identical, combination effects would reduce to a function of size alone. The heterogeneity spans the basin area factor (0.85–1.20), cycles of concentration (3.0–5.0), tower approach (4.5–7.0 K), condenser cleanliness (0.88–1.00) and initial loading (29.4–92.5%).

#### 2.1.3 Timescale stratification and coupling architecture


The simulation adopts a **three-timescale stratified architecture** rather than a single-step transient co-simulation. The cold-end process layer is integrated at 1 s; the frequency layer uses a reduced-order swing equation integrated at 0.01 s; and the AC layer is solved at event-driven cross-sections. AC voltages are thus obtained only at cross-sections and do not participate in the 0.01 s frequency integration. This is a hybrid architecture, and its implications are stated in Section 2.5.

The **coupling interface** constitutes the substantive content of the modelling exercise. Between the cold-end process and the grid side, a closed loop operates:

$$P_g(t) \longrightarrow \dot{V}_{\text{loss}}(t) \longrightarrow t_{\text{trip}} \longrightarrow P_g^{\text{post}}(t) \longrightarrow \dot{V}_{\text{loss}}(t)$$

in which the first arrow denotes downward coupling (output determines the rate of water loss), the second the reporting of a protection event, and the third upward coupling (redispatch alters the output of surviving units). This closed loop is what distinguishes the present formulation from a black-box treatment. Where trip times are imposed, combination effects are absorbed entirely into the input assumption; here $t_{\text{trip}}$ is endogenous and the failure combination is an argument of the model.

The architecture is summarized in Fig. M1, and the corresponding assessment protocol in Fig. M5. Coupling is realized by event-driven segmented advancement. Within each segment, the cold-end layer is integrated at the current $P_g$ until the next protection event or cross-section; the frequency layer resolves the trajectory and the post-trip redispatch; the AC layer solves the islanded power flow at the resulting steady-state dispatch and classifies bus states; and the resulting output distribution becomes the input condition for the next cold-end segment. The sequence continues until all faulted units have tripped or a stopping criterion is met.
**Figure M1 | Modelling framework and timescale stratification.** Coupling architecture of the mechanistic cold-end model with the grid-side model. The cold-end block resolves basin inventory, pump flow availability, tower heat transfer, condenser heat transfer and turbine backpressure capability on the hydraulic timescale; the grid block resolves frequency response, ramp-limited redispatch, UFLS and AC cascade evaluation. The two are coupled through an event-driven interface in which cold-end trips and cap changes are the only quantities exchanged, and the coupling is closed because the trajectory of $P_g$ drives $\dot{V}_{\text{loss}}$. Timescale stratification permits the fast electromechanical dynamics to be integrated between cold-end events rather than concurrently with them.

![Figure M1 — Modelling framework and timescale stratification](../results/paper/figures/fig_M1_framework.svg)


**Figure M5 | The single service-loss criterion F3 and the hard service loss indicator.** (a) Solution sequence at each cascade stage. Islands are re-identified at every stage from the current branch status, so the connectivity on which F3 is judged is that of the evolved network, not that at the instant of unit loss. (b) F3 has two causal paths — an island with no in-service source, and an island whose AC power flow has no solution at any load level — and both count toward $H=\mathbb{1}[\mathrm{F3}]$. Voltage-limit violations, load shedding and frequency excursions are recorded but are not service-loss criteria. Counts are taken over all 63 scenarios.

![Figure M5 — Bus service state criteria and the hard service loss indicator](../results/paper/figures/fig_M5_cascade_judgement.svg)

### 2.2 Mechanistic model of the wet-recirculating cooling system

#### 2.2.1 System boundary and state variables


The cooling system modelled for each unit is a wet-recirculating tower system, bounded from the circulating-water pump sump to the condenser outlet, and comprising the basin, the pump, the tower, the condenser and the connecting pipework (Fig. M2). The state variables are the basin level $L(t)$ (m), the available pump flow fraction $x(t)\in[0,1]$, the tower outlet temperature $T_{\text{in}}(t)$ (${}^\circ$C) and the condenser saturation temperature $T_{\text{sat}}(t)$ (${}^\circ$C), together with the condenser backpressure $p_b(t)$ (kPa). The external excitation is a loss of makeup supply: from $t_0$ onward the makeup flow to the affected unit is identically zero, while all other processes continue to evolve under their conservation laws.
**Figure M2 | System boundary and state variables of the wet-recirculating cooling system.** Control volume of a single unit's cooling system, bounded from the circulating-water pump sump to the condenser outlet. The basin, pump, tower, condenser and connecting pipework are represented; the makeup supply enters at the basin and is the only external water source. State variables are basin level $L$, basin temperature $T_{\text{in}}$ and condenser saturation temperature $T_{\text{sat}}$. The makeup line is the failure locus: its rupture sets $\dot{V}_{\text{makeup}}=0$ while all other flows continue.

![Figure M2 — System boundary and state variables of the wet-recirculating cooling system](../results/paper/figures/fig_M2_coldend_boundary.svg)

#### 2.2.2 Pump flow availability and the cavitation limit

The available circulating flow is constrained jointly by hydraulic head balance and by cavitation margin. Writing $H_{so}$ for the shut-off head, $H_{st}(L)$ for the static head and $H_d$ for the design head, the hydraulically available fraction takes a square-root form:

$$x_{\text{hyd}} = \sqrt{\frac{H_{so} - H_{st}(L)}{H_{so} - H_{st}^{\text{des}}}} \tag{2.1}$$

The cavitation constraint is expressed through the net positive suction head balance:

$$\text{NPSH}_a = \frac{p_{\text{atm}} - p_{\text{sat}}(T_{\text{in}})}{\rho g} + (L - z_{\text{eye}}) - h_{\text{suction}}, \qquad \text{NPSH}_r = \text{NPSH}_{r}^{\text{des}} x_{\text{hyd}}^{2} \tag{2.2}$$

with $x_{\text{npsh}} = 1$ when $\text{NPSH}_a \geq \text{NPSH}_r + \Delta_{\text{req}}$, $x_{\text{npsh}} = 0$ when $\text{NPSH}_a \leq 0$, and linear interpolation otherwise; the operating fraction is $x = \min(x_{\text{hyd}}, x_{\text{npsh}})$. This joint constraint is necessary rather than decorative: after a makeup interruption, falling basin level raises the static head and reduces hydraulic availability, while rising water temperature raises the saturation pressure and reduces $\text{NPSH}_a$. The competition between the two makes low basin level and cavitation *distinguishable* trip mechanisms rather than a single low-level protection.

#### 2.2.3 Tower heat transfer

The cooling tower is represented by an effectiveness–NTU reduction in which the outlet temperature follows from the heat load to the water capacity ratio $R = Q/(\dot{m}_w c_p)$ and the effectiveness $\varepsilon$:

$$T_{\text{out}} = T_{\text{wb}} + \frac{R\,(1-\varepsilon)}{\varepsilon}, \qquad \varepsilon = 1 - e^{-\text{NTU}} \tag{2.3}$$

with the NTU varying with the air-to-water ratio,

$$\text{NTU} = \text{NTU}_{\text{des}} \cdot \kappa_{\text{tower}} \cdot \left(\frac{\dot{V}_{\text{air}}}{\dot{V}_w}\right)^{\!n} \tag{2.4}$$

The tower characteristic multiplier $\kappa_{\text{tower}}$ thus serves as an inter-unit heterogeneity parameter: a reduced value, corresponding to degraded fill or limited design margin, raises the approach at a given load.

#### 2.2.4 Condenser heat transfer and thermal inertia

The condenser exchanges heat through a UA–LMTD relation in which the conductance varies with water flow:

$$Q_{\text{cw}} = UA \cdot \Delta T_{\text{lm}}, \qquad UA \propto \dot{V}_w^{\,\alpha} \chi_{\text{clean}}, \qquad \alpha = 0.8 \tag{2.5}$$

Thermal inertia in the condensate is represented as a lumped capacitance advanced by the enthalpy balance

$$C_{\text{cond}}\frac{dT_{\text{sat}}}{dt} = Q_{\text{steam}} - Q_{\text{cw}}, \qquad C_{\text{cond}} = \tau_{\text{cond}} (UA\,\Delta T)_{\text{des}} \tag{2.6}$$

Equation (2.6) is what makes the low-vacuum path operative. When circulating flow falls, the condenser cannot reject steam-side heat at the rate at which it arrives; saturation temperature and hence backpressure rise. This pathway is independent of basin level and can therefore act before the low-level protection threshold is reached.

#### 2.2.5 Water balance and basin inventory

The cold-end water balance follows the standard engineering decomposition^14,15,16,17^, with the evaporation and blowdown split expressed in the standard engineering form^16^. Evaporation and drift are

$$\dot{V}_{\text{evap}} = \frac{\varepsilon_{\text{evap}} Q_{\text{cw}}}{\rho h_{fg}(T_{\text{in}})}, \qquad \dot{V}_{\text{drift}} = f_{\text{drift}} \dot{V}_w \tag{2.7}$$

Blowdown follows from the salt balance $\text{CoC} = \dot{V}_{\text{makeup}}/\dot{V}_{\text{salt}}$, with $\dot{V}_{\text{salt}} = \dot{V}_{\text{blow}} + \dot{V}_{\text{drift}}$:

$$\dot{V}_{\text{blow}} = \frac{\dot{V}_{\text{evap}}}{\text{CoC} - 1} - \dot{V}_{\text{drift}} \tag{2.8}$$

and the total makeup requirement is the sum of the three terms,

$$\dot{V}_{\text{makeup}} = \dot{V}_{\text{evap}} + \dot{V}_{\text{blow}} + \dot{V}_{\text{drift}} \tag{2.9}$$

The basin inventory follows from conservation, advanced by trapezoidal integration of the loss rate across each interval:

$$L(t+h) = L(t) - \frac{\dot{V}_{\text{loss}}(t) + \dot{V}_{\text{loss}}(t+h)}{2}\cdot\frac{h}{A_{\text{basin}}} \tag{2.10}$$

The trapezoidal form avoids the spurious slope that an explicit Euler scheme would introduce at the instant at which blowdown is isolated.

**Timing of blowdown isolation.** Following a makeup interruption, blowdown continues until operators confirm the condition, after which it is isolated; the corresponding detection delay is $t_{\text{det}} = 0.25$ h. The implementation applies a right-continuous jump at the detection instant and credits the pre-jump blowdown to the interval being integrated. This detail is physically material: it produces a transient *increase* in the loss rate during the early phase of the fault, followed by a decrease once isolation has occurred, after which the loss rate settles at the sum of evaporation and drift.

#### 2.2.6 Turbine thermal capability and protection criteria

The condenser backpressure follows from the saturation temperature and the air partial pressure,

$$p_b = p_{\text{sat}}(T_{\text{sat}}) + p_{\text{air}}, \tag{2.11}$$

and the deliverable power is corrected for backpressure by a piecewise relation, with a small capped bonus below the design point and two sensitivity regimes above it:

$$P_{\text{thermal}}(p_b) = P_{\text{rated}} f(p_b), \qquad f(p_b) = \begin{cases}\min\!\left(1 + \delta_{\max},\; 1 + \kappa_b(p_b^{\text{ref}} - p_b)\right), & p_b \leq p_b^{\text{ref}}\\[3pt] \max\!\left(0,\; 1 - \kappa_1\min(\Delta p, \Delta p_b) - \kappa_2\max(0, \Delta p - \Delta p_b)\right), & p_b > p_b^{\text{ref}}\end{cases} \tag{2.12}$$

where $\Delta p = p_b - p_b^{\text{ref}}$. Equation (2.12) makes rising backpressure directly reduce deliverable power and hence reduce heat rejection, closing a negative feedback between output and water demand; under redispatch, this same loop operates in the opposite sense and amplifies.

**Operator strategy.** As the basin level falls to $L_{\text{shed}} = L_{\text{trip}} + 1.0$ m, operating practice calls for load reduction, and the capability is constrained linearly in level:

$$P_{\text{cap}} = \min\!\left(P_{0},\; P_{\text{thermal}}(p_b),\; P_{\text{rated}}\left[f_{\min}^{\text{tech}} + (1 - f_{\min}^{\text{tech}})\frac{L - L_{\text{trip}}}{L_{\text{shed}} - L_{\text{trip}}}\right]\right) \tag{2.13}$$

Actual output tracks $P_{\text{cap}}$ subject to a ramp limit,

$$P(t+h) = P(t) + \operatorname{clip}\!\left(P_{\text{cap}} - P(t),\; -\dot{P}_{\max} h,\; +\dot{P}_{\max} h\right) \tag{2.14}$$

**Protection criteria and their ordering.** A trip is triggered by one of four mechanisms, evaluated in a fixed priority order: (i) low basin level, $L \leq L_{\text{trip}}$; (ii) cavitation floor, $x \leq x_{\text{floor}}$; (iii) low-vacuum protection, $p_b \geq p_b^{\text{trip}}$ sustained for the declared delay; and (iv) technical minimum output, where capability falls below $f_{\min}^{\text{tech}}P_{\text{rated}}$ and actual output has reached that level. The ordering is fixed so that, when several criteria approach their thresholds simultaneously, the mechanism that acts first is the one acting most directly on cooling-water availability (low level), followed by the mechanism acting on hydraulic availability (cavitation), then the one acting on thermal state (low vacuum), and finally the consequence of operating strategy (technical minimum). A fixed order guarantees that the trip mechanism is unique and reproducible for any given scenario.

For the operating point and parameters examined here, all 184 unit trips across the 63 scenarios were triggered by the low basin level criterion. The remaining three mechanisms are implemented and participate in the evaluation but are not activated in this case. This is itself informative: it indicates that with the basin margins adopted, the low-level protection acts before cavitation and low-vacuum protection, whereas a configuration with smaller basin margins or a faster makeup interruption could reorder them. This limitation is carried into Section 5.4.

It should be emphasized that a trip does not require complete depletion of the basin. The trip occurs when $L$ reaches the specified protection threshold; the trip levels listed in Table 1 (1.00–1.20 m) are protection setpoints, not drain points.

#### 2.2.7 Self-consistent pre-fault equilibrium

The initial state of the cold-end model cannot be prescribed arbitrarily; it is determined by the self-consistent healthy operating point before the fault. The closure of output, backpressure and heat rejection is obtained by iterating $P = \min(P_{\text{set}}, P_{\text{thermal}}(p_b))$ to a fixed point, using damped iteration with a convergence criterion of $|P^{(k+1)} - P^{(k)}| < 10^{-7}$ MW. The initial state is additionally required to satisfy the protection setpoints: if $p_b(0) \geq p_b^{\text{trip}}$, the condition is rejected as an invalid starting point, since a unit already at its trip threshold cannot be said to have tripped because of the fault.

### 2.3 Cold-end–grid coupling model

#### 2.3.1 Event-driven coupling architecture

The coupling simulation advances in five steps. First, the cold-end layer is integrated for each faulted unit at the current $P_g$ until a protection action, recording the trip time $t_{\text{trip}}$ and the pre-trip output. Second, the frequency layer resolves the trajectory, governor response, AGC ramp and any underfrequency load shedding (UFLS) action. Third, the ramp is allowed to complete and the resulting steady-state dispatch is recorded. Fourth, island decomposition and AC power flow are solved at that dispatch, VCLS is applied where necessary, and bus states are classified. Fifth, if no further unit has tripped and no stopping criterion has been met, the steady-state dispatch updates the cold-end initial conditions and the sequence returns to the first step.

Under this architecture the sequence of trip events is endogenous to the cold-end process, and the failure combination is accordingly an argument of the model rather than a descriptor of its input.

#### 2.3.2 Frequency response, ramp-limited redispatch and UFLS

Frequency dynamics are represented by a reduced-order swing equation in the relative frequency deviation $w$ and governor power $p_m$:

$$\frac{dw}{dt} = \frac{p_m + \Delta P - D w}{2H}, \qquad \frac{dp_m}{dt} = \frac{-w/R - p_m}{T_g} \tag{2.15}$$

with $H = 5.0$ s, $R = 0.05$, $D = 1.0$ and $T_g = 0.30$ s.

**Primary frequency response** is apportioned among surviving units in proportion to their pre-event upward margin,

$$\Delta P_{\text{gov}} = \operatorname{clip}\!\left(p_m P_{\text{gen}}^{0},\; -P_{\text{down}}^{\max},\; +P_{\text{up}}^{\max}\right), \qquad P_{\text{up}}^{\max} = \sum_{b\in\mathcal{G}}\left(P_{\max,b} - P_{g,b}^{0}\right) \tag{2.16}$$

**AGC redispatch** begins after the reference delay $t_{\text{delay}}$, apportions the residual deficit among units in proportion to their target increments, and is subject to a ramp limit:

$$\Delta P_{\text{AGC},b}(t+h) = \Delta P_{\text{AGC},b}(t) + \operatorname{clip}\!\left(P_b^{\text{target}} - \Delta P_{\text{AGC},b}(t),\; -\dot{P}_{\max,b} h,\; +\dot{P}_{\max,b} h\right) \tag{2.17}$$

The ramp rate is $0.05\,P_{\max}$ per minute. The limiting term in equation (2.17) is the direct source of the redispatch lag examined here: a power deficit arising from a trip is not restored instantaneously, but filled at a bounded rate.

**UFLS** operates on three frequency stages at 59.30, 58.90 and 58.50 Hz, each shedding 7% of the remaining load. The first-stage setpoint follows the NERC PRC-006-SERC-02 requirement that the highest UFLS setting be ^33^, with generator frequency protection settings ^32^. Relay operation requires the frequency to remain below the setpoint for a delay $\tau_{\text{relay}} = 0.2$ s.

The model additionally records the positive generation-deficit area within the ramp window, which is used to distinguish the power not yet restored by the ramp from unserved customer energy; the two differ in both physical meaning and accounting, and the former is not included in shed load.

#### 2.3.3 AC cascade at event cross-sections

The AC cascade is solved at the steady-state dispatch reached after the ramp. Islands are identified by connectivity; each is treated according to whether it contains a source.

**Source-free islands (F3).** Where an island contains no online generator, all its buses are de-energized, and their loads are recorded as shed in proportion to bus load.

**Unsolvable islands (F3).** Where the AC power flow has no solution at any load level, including after VCLS, the island cannot supply its buses. They are assigned the same state, F3, and their loads are shed in proportion to bus load. The two paths are not separated in the reported endpoint because they denote the same physical outcome, but they are distinguished in the solution log.

Islands are re-identified at the start of every cascade stage from the current branch status. F3 is therefore evaluated on the evolved network rather than on the connectivity at the instant of unit loss — a distinction that is substantive rather than cosmetic, and which is tested directly in Section 4.4.

To quantify unserved load in an island whose power flow does not converge at full load, a uniform load-shedding-to-convergence procedure (VCLS) is applied^36^. The maximum supportable load fraction is located by bisection on the convergence of the AC power flow:

$$\lambda^{*} = \max\left\{\lambda \in [0,1] : \text{AC power flow converges at load } \lambda P_{\text{load}}\right\} \tag{2.18}$$

with unserved load $(1-\lambda^{*})\sum P_{\text{load}}$ allocated across buses in proportion to bus load. The same procedure supplies the test for the unsolvable branch of F3: an island for which no $\lambda > 0$ admits a convergent solution is unsolvable. The bisection scales load and generation together so that island power balance is preserved at every trial; $\lambda^{*}$ is therefore a **loadability margin** — the largest uniformly scaled operating point the island can support — rather than the solution of a cost-minimising shed allocation. The term VCLS is retained for continuity with the implementation, but the procedure is deliberately *not* an optimal shedding scheme. An AC optimal power flow formulation was rejected for two reasons: solver failure becomes frequent under exactly the high-stress conditions of interest, and a minimum-weighted-shed objective embeds a subjective valuation of lost load. The cost of this choice is that the *location* of shed load is allocated proportionally rather than optimised; this is quantified in Section 4.4 and taken up as a limitation in Section 5.4.

**Overload tripping.** A branch whose loading exceeds 1.25 is tripped and removed from the topology, prompting a further cross-section. The cascade proceeds for at most 15 stages.

#### 2.3.4 The service-loss criterion

Bus service loss is assigned by a single criterion. F3 holds when an island cannot supply its buses — either because it contains no in-service source, or because its AC power flow has no solution at any load level. Both paths are reported as one state because they denote the same physical outcome: the bus cannot be supplied.

The hard service loss criterion is

$$H = \mathbb{1}\!\left[\mathrm{F3}\right] \tag{2.19}$$

where $H$ is a count of buses. Two consequences of this definition are worth stating explicitly. First, $H$ is a bus count, not a load ratio; shed load in MW is a separate quantity; expected energy not served is a third. The three are not interconvertible and are kept strictly separate throughout. Second, because there is only one criterion, $H$ is identically the number of F3 buses: no decomposition of $H$ by service state needs to be reported, and none is.

Voltage magnitude is not itself a service criterion. A transient voltage recovery criterion — voltage not remaining below 0.8 p.u. for longer than 10 s for planning events^39^ — was deliberately not adopted as a loss-of-service test, because it draws a distinction (recoverable versus unrecoverable low voltage) that is not the distinction of interest here; the question put to the model is whether a bus can be supplied at all. Voltage nevertheless enters the cascade through protection and control — the two UVLS stages at 0.92 and 0.88 p.u., and generator terminal-voltage tripping below 0.90 or above 1.10 p.u. — and through these it shapes the topology on which F3 is finally evaluated. A bus may therefore be at severely depressed voltage and still be counted as in service, which makes the reported $H$ conservative with respect to voltage effects.


### 2.4 Performance metrics and numerical quality assurance

#### 2.4.1 Metrics

Three strictly separated classes of metric are used: the **hard service loss count** $H$ (equation 2.19); **shed load** $S_{\text{shed}} = S_{\text{static}} + S_{\text{UFLS}}$ in MW, with static curtailment from VCLS and source-free islands recorded separately from UFLS action; and **frequency metrics**, comprising the nadir $f_{\text{nadir}}$, the rate of change of frequency and the UFLS stage and cumulative shed. Auxiliary quantities recorded include the cold-end makeup demand, basin level trajectories, trip mechanism and pre-trip output, ramp completion time and the positive generation-deficit area within the ramp window.

**Why a bus count is the primary endpoint.** The three metric classes answer different questions, and the ordering adopted here is a choice that should be stated rather than assumed. Load shed in MW measures the *magnitude* of the consequence; a bus count measures its *spatial extent*. Both are in standard use — NERC reports blackout size as load shed together with customers affected, and the cascade literature predominantly records load shed in MW^9^ — but they are not interchangeable, and for the present question the spatial extent is the object of interest. The study asks how a localised cold-end failure becomes a system-level loss of service, which is a question about *reach*; a metric in MW would answer a question about severity that is already answered by the shed-load figures reported alongside $H$. $H$ is therefore reported as the primary endpoint, with shed load in MW as a parallel and strictly separate measure of magnitude, and no attempt is made to combine them into a single index.

**Expected energy not served is not used.** The scenarios constitute a deterministically specified set of concurrent failures, the combinations being given by protocol rather than sampled with probability weights. Aggregating deterministic scenario outcomes into an expectation under arbitrary weights would be misleading. This point is carried into the limitations in Section 5.4.

#### 2.4.2 Numerical quality assurance

Because the convergence of the power-flow solver determines the unsolvable branch of F3, the solver state is a precondition of the results rather than an implementation detail, and it is audited explicitly.

Across the 63 scenarios, 60 solved without singular or divergence warnings. Three did not converge, each with a combination of rank-deficiency and runtime warnings: K4-G1-G2-G13-G22, K4-G2-G13-G22-G27 and K5-G1-G2-G13-G22-G27. The solver health annotation accompanying the source results states explicitly that non-convergence means internal convergence is not proven and that the reported $H$ values are conditional on that limitation. We accordingly report the count of hard-service-loss scenarios as 22, of which two are conditional results of this kind.

**Sensitivity to the non-converged cases.** Recomputing all statistics with the three scenarios excluded leaves the substantive conclusion unchanged. The 15 combinations excluding G1 yield no hard service loss under either accounting, so the necessity of G1's presence is unaffected; the trigger rate by unit count changes from 0%, 6.7%, 25%, 60.0%, 100% and 100% to 0%, 6.7%, 25%, 61.5%, 100% and 100%, preserving the monotonic trend. The core conclusions are therefore insensitive to the non-converged cases. It remains relevant to note, however, that the two non-converged scenarios with $H > 0$ both fall among the most severe outcomes in the set.

**Table R4 | Scenarios with unproven solver convergence.**

| Layer | Failed units | Rank warnings | Divergence warnings | $H$ | Shed load (MW) | $f_{\text{nadir}}$ (Hz) |
|---|---|---:|---:|---:|---:|---:|
| K4 | 1+2+13+22 | 60 | 54 | 25 | 180.5 | 58.7507 |
| K4 | 2+13+22+27 | 60 | 54 | 0 | 87.0 | 59.2556 |
| K5 | 1+2+13+22+27 | 120 | 108 | 29 | 186.8 | 57.9628 |

> Convergence is not proven for these three of the 63 scenarios (MatrixRankWarning and RuntimeWarning). The reported $H$ values are therefore conditional results. Two of the three are among the most severe scenarios in the set, which is the reason their possible exclusion is examined explicitly in Section 4.6 rather than left implicit.


### 2.5 Model assumptions and conditions of applicability

The following assumptions and bounds are stated so that the conclusions are not extended beyond the mechanisms actually modelled.

#### 2.5.1 Structural assumptions

(i) *Hybrid timescale architecture.* The cold-end process, frequency dynamics and AC cross-sections are solved on their respective timescales; AC voltages are obtained only at cross-sections and do not enter the 0.01 s frequency integration. This is accordingly a hybrid architecture and not a full transient co-simulation: electromechanical transient detail—excitation, automatic voltage regulation, transient stability, switching dynamics—is not represented. The quantitative consequences of cascade losses therefore depend on quasi-steady cross-sectional criteria rather than on complete transient trajectories.

(ii) *Lumped-parameter cold end.* The cooling tower is represented by an effectiveness–NTU reduction and the condenser by a UA–LMTD relation with a single-node thermal capacitance; the spatial distribution of tower flow, the temporal evolution of fill fouling and the zonal behaviour of tube bundles are not modelled.

(iii) *Single failure mode.* Only makeup-line rupture is represented; fouling, blockage and freezing are not.

(iv) *Uniformity of the trip mechanism.* Four trip mechanisms are implemented, but all 184 trips across the 63 scenarios were triggered by the low basin level criterion and the remaining three were not activated. The results on failure chronology therefore describe the behaviour under a single mechanism, and differences between mechanisms are not covered by this case.

(v) *Reduced-order governor and AGC.* The governor is represented by a single-time-constant droop characteristic and the AGC by an idealised ramp-limited apportionment; inter-unit coordination, AGC deadbands, frequency deadbands and the re-optimization of reserve allocation are not represented.

#### 2.5.2 Limits on parameter provenance

**None of the coupling-side parameters is a field-measured value** (Table M2). This includes the unit ramp rate, redispatch delay, makeup response time constant, UFLS relay delay and post-trip cold-end observation window. Cold-end parameters (Table 1) are anchor values whose assignment follows the engineering characteristics of the units—loading, basin margin, fill degradation—and are likewise not field measurements.

The conclusions are therefore conditional on the parameter set adopted. The influence of parameter uncertainty has not been quantified by sensitivity sweeps, because the ranges and sampling strategy for such sweeps have not been fixed; no such sweep has been undertaken here. This is carried into the limitations in Section 5.4.

**Table M2 | Coupling-side model parameters and their provenance.**

| Parameter | Value | Unit | Provenance |
|---|---:|---|---|
| Unit ramp rate | 0.05 | $P_{\max}$/min | Reference assumption |
| Redispatch delay | 10 | s | Reference assumption |
| Makeup capacity factor | 1.0 | p.u. of full-load design | Reference assumption |
| Makeup response time constant | 60 | s | Reference assumption |
| UFLS relay delay | 0.2 | s | Reference assumption |
| Power-flow time step | 1 | s | Study setting |
| Frequency time step | 0.01 | s | Study setting |
| Post-trip cold-end observation window | 24 | h | Reference assumption |

#### 2.5.3 Conditions of applicability

The conclusions hold under the following conditions and do not extend beyond them. The operating point is fixed: all 63 scenarios share one base-case power flow and one initial dispatch, and results for other operating points would require recomputation, which this study does not provide. The unit subset is limited: the enumeration covers all six units of a 30-bus, 335 MW system, and the conclusions are not scalable. The failure scenario is concurrent: simultaneous independent makeup-line rupture at $t_0$ is represented, whereas staggered failure times, repeated failures and restoration are not. Finally, cold-end heterogeneity is prescribed: the six units' cold-end parameters are anchor values, and the robustness of the conclusions to perturbation of those values has not been tested.

#### 2.5.4 Relation to existing work

The difference in modelling pathway from the closest existing work has been ^21^. The present study does not replicate a dependent-failure theory in the electrical domain; it is an application of that framework to a specific failure mode within one operating point. The relevant taxonomy of dependency models and the normative boundary between common-cause and dependent failure are taken from the ^24,25^. Although the physical background involves multiple units sharing an external water source, the failures are independent events and do not ^25^.

---

## 3. Archetype and setup

### 3.1 System archetype and the choice of units


The archetype is a regional group of six thermal generating units drawing on a common water source through independent makeup lines, connected to a 30-bus transmission network with 189.2 MW of load. The six units are not a selection made for convenience: they are the complete generating fleet of the ^29,30^, and the study therefore analyses the full unit set rather than an extract. This matters for the combination analysis, because an incomplete fleet would make the enumeration of failure sets unrepresentative of any actual configuration.

The units are, however, heterogeneous in ways that matter for the present questions (Fig. A2). Their rated capacities span 30–80 MW, their base-case loading spans 29.4–92.5% of rating, and their cold-end parameters differ systematically in basin area factor, cycles of concentration, tower approach and condenser cleanliness (Table 1). This heterogeneity is a precondition for the combination-level analysis rather than a complication of it: were the units thermally identical, the outcome for a given set size would be determined by that size alone, and the compositional effects reported in Section 4.1 could not arise.

One further property of the archetype requires early statement, because it recurs as a confound in the results. G1 is the system's slack unit, located at bus 1; its active output is a consequence of the power flow rather than a prescribed setpoint, whereas the other five units operate as PV machines. G1 is simultaneously the least-loaded unit in the fleet, at 29.4% of rating, and the unit with the largest basin inventory, with 3.2 m of headroom above its trip level. These three attributes are properties of the same unit and cannot be varied independently within a fixed operating point. Their joint role in the results is examined in Section 5.2.
**Figure A1 | IEEE 30-bus test system and the six generating units.** The test system, showing the location of the six generating units that constitute the complete generating fleet of the IEEE 30-bus system. Units are labelled by bus; G1 at bus 1 is the slack unit. The six units are not a selected subset but the full set of generators in the test case, which removes selection bias from the failure-set enumeration.

![Figure A1 — IEEE 30-bus test system and the six generating units](../results/paper/figures/fig_A1_grid_topology.svg)


**Figure A2 | Cold-end heterogeneity across the six units.** Cold-end characteristics that govern isolated-failure trip time: available basin headroom, basin area factor, cycles of concentration, tower approach and condenser cleanliness. The units differ substantially in all five, and the resulting isolated-failure trip times span 2.3003 h (G13) to 13.7061 h (G1). G1 combines the lowest loading with the largest available headroom, which places it last in the isolated-failure trip order.

![Figure A2 — Cold-end heterogeneity across the six units](../results/paper/figures/fig_A2_coldend_heterogeneity.svg)

### 3.2 Scenario protocol


The failure protocol enumerates every non-empty subset of the six units, giving $\sum_{n=1}^{6}\binom{6}{n} = 63$ combinations (Table 5, Fig. A3). The enumeration is exhaustive with no exclusions, and each combination is simulated once (Table A3). Within every scenario, the affected units' makeup lines rupture simultaneously at $t_0 = 0$; no scenario involves staggered failure times, repeated failures or restoration.

**Table 5 | Scenario enumeration protocol.**

| Layer | Units per set | Combinations $\binom{6}{n}$ | Simulated | Failure instant | Failure mode |
|---|---:|---:|---:|---|---|
| K1 | 1 | 6 | 6 | $t_0 = 0$ | Independent makeup-line rupture |
| K2 | 2 | 15 | 15 | $t_0 = 0$ | Independent makeup-line rupture |
| K3 | 3 | 20 | 20 | $t_0 = 0$ | Independent makeup-line rupture |
| K4 | 4 | 15 | 15 | $t_0 = 0$ | Independent makeup-line rupture |
| K5 | 5 | 6 | 6 | $t_0 = 0$ | Independent makeup-line rupture |
| K6 | 6 | 1 | 1 | $t_0 = 0$ | Independent makeup-line rupture |
| **Total** | 1–6 | **63** | **63** | | |

> The six units share a common water source, but each makeup line fails independently. This is a concurrent but not common-cause failure set: no single upstream event disables all units simultaneously, and the common-cause criteria of a shared cause acting through a coupling mechanism within an established ^25^.

The choice of $t_0$ concurrency is deliberate rather than incidental. Concurrent failure is the limiting case of staggered failure and therefore the most demanding test of whether a coupled model produces interaction effects: if units fail simultaneously, no unit's failure can have preceded another's, and any timing dependence that emerges must arise from the mutual reshaping of the operating point rather than from the order in which the failures were imposed. It is also the physically relevant case for a common external driver acting on parallel delivery infrastructure.

The simulation is terminated when either all faulted units have tripped or a hard service loss criterion has been attained. The latter criterion accounts for the six early-terminating scenarios reported in Section 4.5.
**Figure A3 | Scenario matrix of the complete failure-set enumeration.** The 63 scenarios, organised by failure-set size $n$ and membership. Every non-empty subset of the six units is simulated once, giving $\sum_{n=1}^{6}\binom{6}{n}=63$ combinations. The enumeration is exhaustive with no exclusions, which permits outcome statistics to be stratified both by set size and by membership.

![Figure A3 — Scenario matrix of the complete failure-set enumeration](../results/paper/figures/fig_A3_scenario_matrix.svg)

### 3.3 Operating point and its disclosure

All 63 scenarios share one base-case operating point: one AC power flow solution, one initial dispatch and one initial allocation of reactive support. The initial outputs in Table 1 are the results of that solution, and the cold-end state variables are initialized from the self-consistent healthy operating point described in Section 2.2.7.

This design is a limitation as well as a simplification, and it is disclosed here rather than deferred. Because the operating point is common to all scenarios, the results isolate the effect of the failure set from the effect of the dispatch. But the alternative — varying the operating point across scenarios — would confound the two, and would in particular alter the slack unit's output, which is one of the attributes implicated in the results. Fixing the operating point is thus the appropriate choice for the question being asked, while leaving the dispatch dimension as an acknowledged gap.

Three quantities in the results must be kept distinct throughout, and we state the convention here rather than at each point of use. **$H$** is a count of buses that have lost service, determined by equation 2.19. **Shed load** is a power quantity in MW, and is further subdivided into static curtailment arising from voltage-collapse minimum shedding and source-free islands, and UFLS curtailment arising from the frequency dynamics. **The positive generation-deficit area** within the ramp window is a third quantity again, recording the power not yet restored by the constrained redispatch; it is a property of the recovery trajectory and is not unserved customer energy. The three are never interconvertible, and only the first two appear in the outcome statistics of Section 4.

## 4. Results

### 4.1 Cold-end failure behaviour under isolated and concurrent conditions


The cold-end model produces a distinct trip ordering under isolated failure, and that ordering is a direct consequence of the units' initial loading rather than of their nominal size. G13, the most heavily loaded unit at 92.5% of rating, trips first at 2.3003 h, followed by G23 at 2.7372 h and G2 at 4.6564 h; G22 trips at 7.0181 h, G27 at 8.4069 h and G1 last at 13.7061 h (Fig. R1, Table 1). The rank order is therefore close to the inverse of loading, and G1 — at 29.4% of rating — is the outlier, being protected by the largest available basin inventory (3.2 m of headroom above its trip level) rather than by any difference in nominal capacity. No isolated unit failure produced hard service loss, and only G27 alone produced any load shed (2.01 MW), with the frequency nadir remaining above 59.35 Hz in every case.

Under concurrent failure, the trip times of the same units shift substantially. For G1, which participates in 27 of the combinations and therefore provides the largest sample of concurrent conditions, the trip time ranges from 7.4781 to 12.3433 h against an isolated-failure benchmark of 13.7061 h. The concurrent trip therefore occurs between **9.9% and 45.4% earlier** than the isolated trip, with the earliest instance at 7.4781 h in the combination G1+G2+G13+G23.

The shift grows with the number of concurrently failed units (Fig. D1). Among combinations containing G1, the advance in trip time relative to isolated failure ranges from 9.9–28.9% at two units, through 19.6–43.8% at three and 26.4–45.4% at four, to 40.3–45.4% at five. The compression of the timeline is thus a function of the failure set and not of the individual unit, and within any one set size the spread remains substantial — 19.0–24.2 percentage points across the two-, three- and four-unit combinations — indicating that set *composition* matters independently of set *size*.
**Figure R1 | Cold-end inventory depletion and unit availability under isolated failure.** Basin level, makeup loss rate and the resulting trip time for each of the six units under isolated makeup-line rupture. Depletion is approximately linear because the loss rate is dominated by evaporation, which scales with rejected heat and therefore with the unit's own output; the ordering of trip times is therefore governed principally by available headroom and basin geometry rather than by loading alone.

![Figure R1 — Cold-end inventory depletion and unit availability under isolated failure](../results/paper/figures/fig_R1_coldend_evolution.svg)


**Figure R2 | Trip-time ordering and its physical drivers.** Decomposition of the isolated-failure trip time for each unit into the contributions of available basin headroom, basin area and loss rate. The ordering is not monotonic in any single attribute: G13 trips first because it combines the smallest headroom with the highest loading, while G1 trips last because it combines the largest headroom with the lowest loading. This heterogeneity is what makes the concurrent-failure problem combinatorial rather than aggregate.

![Figure R2 — Trip-time ordering and its physical drivers](../results/paper/figures/fig_R2_trip_time_decomposition.svg)

### 4.2 Combination structure in the severity of service loss


Of the 63 combinations, 22 produced hard service loss and 41 did not (Fig. R5, Table 2; per-scenario outcomes in Table R2). The 22 affected scenarios involve **22 distinct combinations**: no two share the same failure set. The premise that a recurring "dominant unit pairing" organizes the outcome is therefore not supported by these data, and the analysis below proceeds instead from conditions identifiable in the unit and set attributes.

The clearest such condition involves G1. Of the 48 combinations containing G1, 22 produced hard service loss; of the 15 combinations excluding G1, none did (Fig. R5a). G1's presence is thus a **necessary condition** for hard service loss within this operating point. The condition is far from sufficient: among the nine two-unit combinations containing G1, only G1+G2 cascaded (Fig. R5), the remaining eight yielding $H = 0$.

The trigger rate rises monotonically with the number of failed units: 0% at one unit, 6.7% at two, 25.0% at three, 60.0% at four and 100% at five and six (Fig. R5b, Table 2). This progression holds within the G1-containing subset as well (11.1%, 31.2%, 64.3%, 100.0%, 100.0%), confirming that G1's presence does not substitute for set size but compounds with it.

Severity, where it occurs, is concentrated. Among the 22 scenarios with $H > 0$, the median is 24 hard-lost buses, with the distribution falling into two groups: a minor group at $H = 2$ (8 scenarios) and $H = 4$ (1 scenario), and a major group spanning $H = 23$ to 29 (13 scenarios) (Fig. R5c). The major group corresponds closely to near-total loss of the 30-bus system; the minor group corresponds to the early termination scenarios discussed in Section 4.5.
**Figure R5 | Hard service loss by G1 presence, by set size and in frequency distribution.** Outcome structure of the 63 scenarios. Left: hard service loss occurs only where G1 is present, establishing G1's presence as a necessary condition within this operating point. Centre: trigger rate rises monotonically with failure-set size, from 0% at one unit to 100% at five and six. Right: distribution of $H$ over the 22 affected scenarios, showing that the necessary condition is far from sufficient and that consequence severity is broadly distributed.

![Figure R5 — Hard service loss by G1 presence, by set size and in frequency distribution](../results/paper/figures/fig_R5_outcome_drivers.svg)


**Figure R8 | Distribution of non-cascading and early-terminated scenarios.** The 41 scenarios without hard service loss, together with the six that terminate early. Non-cascading scenarios occur at every set size up to four units, and their $H=0$ outcomes are not concentrated in any single layer. The six early-terminated scenarios are shown separately because their observation windows are censored by the stopping rule rather than by the absence of further failure.

![Figure R8 — Distribution of non-cascading and early-terminated scenarios](../results/paper/figures/fig_R8_no_cascade.svg)

**Table 2 | Outcome statistics by failure-set size.**

| Layer | Units | Combinations | $H = 0$ | $H > 0$ | Trigger rate (%) | $H$ range | UFLS acts | Early termination | $f_{\text{nadir}}$ range (Hz) | Shed load range (MW) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| K1 | 1 | 6 | 6 | 0 | 0.0 | 0–0 | 0 | 0 | 59.36–59.80 | 0.0–2.0 |
| K2 | 2 | 15 | 14 | 1 | 6.7 | 0–23 | 0 | 0 | 59.31–59.73 | 0.0–164.3 |
| K3 | 3 | 20 | 15 | 5 | 25.0 | 0–27 | 5 | 0 | 58.94–59.61 | 0.0–186.2 |
| K4 | 4 | 15 | 6 | 9 | 60.0 | 0–28 | 13 | 2 | 58.40–59.61 | 16.7–189.2 |
| K5 | 5 | 6 | 0 | 6 | 100.0 | 2–29 | 5 | 3 | 57.96–59.61 | 39.6–189.2 |
| K6 | 6 | 1 | 0 | 1 | 100.0 | 2–2 | 1 | 1 | 59.27–59.27 | 66.9–66.9 |
| **Total** | 1–6 | **63** | **41** | **22** | **34.9** | **0–29** | **24** | **6** | **57.96–59.80** | **0.0–189.2** |

### 4.3 The trip time of G1 predicts, but does not determine, service loss


Because G1 appears in 27 combinations with a recorded trip time, it is possible to ask how tightly its trip time is associated with the outcome. The association is strong but not deterministic, and the distinction matters for how the result should be used.

Grouped by outcome, the 14 scenarios with $H > 0$ all trip G1 by 9.7383 h and the 13 with $H = 0$ all trip it no earlier than 8.4397 h. The two ranges therefore **overlap across 8.4397–9.7383 h**, within which five scenarios of each outcome are interleaved (Fig. D1a). A single trip time is thus not sufficient to determine whether hard service loss follows. The correct statement is that G1's trip time is **negatively associated** with severity: the Spearman rank correlation with $H$ is −0.78 ($p = 1.7\times10^{-6}$), and with the binary indicator of any hard service loss it is −0.75 ($p = 5.8\times10^{-6}$).

Quantifying the gradient by quartile of G1's trip time makes the structure explicit (Fig. D1b): the earliest quartile trips G1 before 8.18 h and all eight scenarios produced hard service loss; the second quartile produced it in four of six cases; the third in two of six; and the latest quartile, in which G1 trips after 10.09 h, in none of seven. The gradient is monotonic and steep, and it is what supports the statement that an early G1 trip is a reliable *precursor* of cascade under this operating point. It is not a criterion, and the overlap noted above precludes such a reading.
**Figure D1 | G1's trip time across combinations, its association with outcome, and its dependence on set size and composition.** Trip time of G1 across the 27 combinations in which it participates. The isolated-failure benchmark of 13.7061 h is advanced to between 7.4781 and 12.3433 h under concurrent failure, an advance of 9.9–45.4% that depends on both set size and set composition. The association with outcome is monotonic but not determinative: the trip times of the $H=0$ and $H>0$ groups overlap across 8.4397–9.7383 h, so no trip-time threshold separates the two outcomes.

![Figure D1 — G1's trip time across combinations, its association with outcome, and its dependence on set size and composition](../results/paper/figures/fig_D1_trip_time_evolution.svg)


**Figure R3 | Coupled cross-domain time series for the canonical G1+G2 case.** Time series for the two-unit case, showing on the cold-end side the basin levels and makeup demand of G1 and G2, and on the grid side the frequency, the redispatch of surviving units and the bus service state. G2 trips at 4.6564 h; redispatch then raises G1 from 25.97 to 52.64 MW, raising its makeup demand from 71.7 to 128.8 m³/h against an identically zero supply. G1 trips at 9.7383 h and the loss of buses 1 and 2 cascades to 23 hard-lost buses with 164.3 MW shed, without UFLS action.

![Figure R3 — Coupled cross-domain time series for the canonical G1+G2 case](../results/paper/figures/fig_R3_k2_coupled_timeseries.svg)


**Figure D2 | Event-chain causality and makeup balance in the G1+G2 case.** Causal chain of the canonical case, from the loss of G2 through redispatch, the rise in G1's rejected heat, the rise in its evaporative demand and the acceleration of its basin depletion to its trip at 9.7383 h. The makeup balance panel shows the composition of the loss rate for G1 before and after redispatch, confirming that the dominant term is evaporation and that it scales with output.

![Figure D2 — Event-chain causality and makeup balance in the G1+G2 case](../results/paper/figures/fig_D2_event_chain.svg)


### 4.4 Mechanism of service loss: static topology rather than frequency dynamics


The canonical case, G1+G2, shows the coupling in full (Fig. R3, Fig. D2). G2 trips at 4.6564 h. Redispatch then raises G1 from 25.97 to 52.64 MW, and because evaporation scales with rejected heat, G1's makeup demand rises from 71.7 to 128.8 m³/h — an increase of 80% — while the makeup supply remains identically zero. G1's basin level falls from 4.20 m to the 1.00 m trip threshold, and G1 trips at 9.7383 h. The loss of both units de-energizes buses 1 and 2 and cascades to 23 hard-lost buses, with 164.3 MW of load shed.

The decisive feature of this cascade is that it is **not** a frequency event. The frequency nadir is 59.36 Hz, comfortably above the first UFLS stage of 59.30 Hz, and UFLS does not act (Fig. R7). The 23 lost buses arise entirely through F3. The service loss is thus a consequence of the network's structure as it evolves under the cascade, rather than of a frequency-driven protection cascade.

This pattern is not confined to the canonical case. Across the 63 scenarios, UFLS acts in 24 (Fig. R7a), and the frequency nadir separates cleanly between the two groups: scenarios in which UFLS acts span 57.96–59.28 Hz, and those in which it does not span 59.30–59.80 Hz, with no overlap at the 59.30 Hz threshold. Where UFLS acts, the shed load consists of 10.3–57.1 MW of frequency-driven curtailment combined with up to 173.2 MW of static curtailment, indicating that even in the scenarios with the most severe frequency excursions the two mechanisms coexist.

**Hard service loss is topological across the whole enumeration, and it is produced by the cascade rather than given by the initial connectivity.** Across all 63 scenarios, 366 buses are lost. That every one of them is F3 is an identity rather than a finding, since F3 is the only criterion (Section 2.3.4); the substantive question is which of its two paths is taken. **The unsolvable path is never taken.** No island in any scenario had an AC power flow without a solution at every load level, so all 366 buses are lost through the source-free path: separation from every in-service generator.

That this separation is produced by the cascade, rather than being present as soon as the units are lost, was tested directly rather than assumed. In the canonical case the network is still a single connected island containing four units in service immediately after G1 and G2 are removed, so no island is source-free at that point and the F3 count is zero. A counterfactual run in which the overload trip threshold is raised until no branch ever trips returns F3 = 0 for the same failure set, whereas the modelled sequence of overload trips yields the observed loss. All 22 scenarios with $H > 0$ record at least one line overload trip. F3 is therefore an outcome of the cascade in this study: without the overload trips there would be no service loss to report, and the endpoint cannot be recovered from the connectivity at the instant of unit loss.

The condition under which the unsolvable path stays empty, and the reason it stays empty, are established immediately below, and that finding should not be separated from them.

This is not an artefact of the shedding procedure rescuing islands that would otherwise have collapsed. VCLS is invoked in 37 of the 63 scenarios, but the load it removes is modest: across those scenarios it sheds a median of 9.6% of the surviving island's load and never more than 40.5%, a range consistent with the 5–20% typical of practical undervoltage load-shedding schemes^41^. In the canonical case it removes nothing at all: the entire 164.3 MW of shed load is the load of the 23 de-energized buses, and the seven surviving buses continue to be supplied in full. The finding is therefore properly stated as follows — no scenario produced a voltage collapse that load shedding could not arrest, and in the most severe cases the loss of supply was topological from the outset rather than the endpoint of a voltage decline.

**Why voltage collapse does not occur: the capacity position of the test system.** The unsolvable path of F3 is never taken, and this is not a coincidence of the enumeration but a consequence of where the system sits relative to its loadability limit. The test case carries 189.2 MW of load against 335 MW of installed capacity, a system load factor of 56.5%. Defining the capacity margin as the capacity remaining after a failure set is removed minus the load the surviving units must then serve, the margin across the 63 scenarios has a median of 70.3 MW and a minimum of 0.0 MW, and is never negative: at no point in any scenario did the surviving units face a load they could not in principle serve. Voltage collapse is a phenomenon of a system operating near its loadability limit, and a system that retains this much reserve through every stage of every cascade is not near that limit. The emptiness of the unsolvable path is therefore a property of this operating point on this test system, and the mechanism finding must be stated conditionally — **under a capacity-rich operating point, service loss is topological** — rather than as a property of cold-end failure cascades in general.

This conditional reading is supported by the correlation structure, which also cautions against a stronger claim. The capacity margin is strongly rank-correlated with $H$ ($\rho = -0.627$, $p = 3.7 \times 10^{-8}$), but it is correlated still more strongly with the number of failed units ($\rho = -0.811$), and within strata of fixed failure-set size the margin–$H$ association is not significant at any size ($n=2$: $\rho = -0.31$, $p = 0.26$; $n=3$: $\rho = -0.29$, $p = 0.21$; $n=4$: $\rho = -0.35$, $p = 0.20$). The apparent predictive power of the margin is attributable to set size rather than to the margin itself, so it is not reported as a finding. What the margin does establish is the condition under which the topological mechanism was observed: the system was capacity-rich throughout, and it is under that condition that service loss was topological. Whether the same holds in a system operating closer to its limit is not determined by the present design, and is taken up in Section 5.4.
**Figure R7 | Frequency nadir, UFLS action and shed-load composition.** Frequency behaviour and shed-load composition across the scenarios. UFLS acts in 24 of the 63 scenarios, spanning 57.96–59.28 Hz, while the remaining 39 do not reach the first stage at 59.30 Hz. Shed-load composition separates static curtailment from frequency-driven curtailment; the two coexist in the most severe cases, and treating them as alternatives would understate those cases.

![Figure R7 — Frequency nadir, UFLS action and shed-load composition](../results/paper/figures/fig_R7_frequency_ufls.svg)

### 4.5 Spatial pattern and early termination


The spatial distribution of lost load is highly concentrated (Fig. R6). Buses 25 and 26 are lost in all 22 scenarios with $H > 0$, and buses 1–7 in 13 of the 22 (59.1%). The loss of the generating buses themselves accounts for a substantial share of the total, indicating that the cascades are initiated by the loss of the two generating units and propagate into the load buses they supply.

Six scenarios terminate early, on the criterion that hard service loss has already been attained (Table 3; full list in Table R3). In all six the observed $H$ is 2, with shed load of 39.6 or 66.9 MW, and the observation window closes after 3.06–3.32 h. These values reflect the stopping rule rather than the ultimate consequence: one or more faulted units had not yet tripped when the simulation ended, and their trip times are unobserved. The identical $H = 2$ across all six arises from the common stopping criterion, not from equivalence of consequence, and these scenarios must not be read as milder outcomes than the others.
**Figure R6 | Spatial concentration of lost buses.** Bus-level pattern of hard service loss across the affected scenarios. Loss is spatially concentrated rather than diffuse: buses cluster around the de-energised generating buses and propagate along the transmission structure connecting them. The concentration is consistent with the topological mechanism of Section 4.4, in which service loss follows from the inability of the remaining structure to sustain load rather than from a frequency excursion.

![Figure R6 — Spatial concentration of lost buses](../results/paper/figures/fig_R6_bus_loss_pattern.svg)

**Table 3 | Scenarios terminating early on attainment of hard service loss.**

| Layer | Failed units | Trips before stop | Units tripped, in trip order | Censored units | $H$ | Shed load (MW) | Observation window (h) |
|---|---|---:|---|---|---:|---:|---:|
| K4 | 1+13+22+23 | 3/4 | 13, 23, 22 | 1 | 2 | 39.6 | 3.3175 |
| K4 | 13+22+23+27 | 3/4 | 13, 23, 22 | 27 | 2 | 39.6 | 3.3175 |
| K5 | 1+13+22+23+27 | 3/5 | 13, 23, 22 | 1, 27 | 2 | 39.6 | 3.3175 |
| K5 | 1+2+13+22+23 | 4/5 | 13, 23, 2, 22 | 1 | 2 | 66.9 | 3.0589 |
| K5 | 2+13+22+23+27 | 4/5 | 13, 23, 2, 22 | 27 | 2 | 66.9 | 3.0589 |
| K6 | 1+2+13+22+23+27 | 4/6 | 13, 23, 2, 22 | 1, 27 | 2 | 66.9 | 3.0589 |

> Unit numbers omit the G prefix. Censored units had not tripped when the simulation ended; their trip times are unobserved and must not be counted as non-trips. The identical $H = 2$ across all six scenarios reflects the common stopping criterion, not equivalence of consequence. The observed trip order follows the isolated-failure order of Section 4.1 and is truncated by the stopping rule: G13 trips first at 2.3003 h, G23 at 2.6942 h, and then either G2 at 4.4281 h or G22 at 5.6178 h, depending on whether G2 is among the failed units; where G2 trips, G22 follows at 5.3592 h. The censored units are those whose trip times would have exceeded the observation window, and their absence from the trip column is a censoring artefact rather than evidence of endurance.


### 4.6 Sensitivity analysis

The results above rest on a single numerical realization of each scenario, and two features of the model could in principle bias them: the three scenarios whose AC solution did not converge, and the choice of a single operating point. The first of these can be tested directly, because the converged and non-converged scenarios are separately identified in the solution record; the second is examined by the structure of the enumeration rather than by re-simulation.

**Sensitivity to the non-converged scenarios.** Three of the 63 scenarios did not converge, and their reported $H$ values are conditional on unproven internal convergence (Section 2.4.2). Recomputing the principal statistics with these three removed yields the comparison in Table R4b.

**Table R4b | Sensitivity of the principal conclusions to the exclusion of non-converged scenarios.**

| Accounting basis | $H>0$ scenarios | $H>0$ among G1-containing | $H>0$ among G1-excluding | 4-unit trigger rate (%) | G1 necessary? |
|---|---|---|---|---:|:---:|
| All 63 scenarios | 22 / 63 | 22 / 48 | 0 / 15 | 60.0 | Yes |
| 60 converged scenarios only | 20 / 60 | 20 / 45 | 0 / 15 | 61.5 | Yes |

> Reproduction of Table R4b, generated from the scenario record; per-scenario convergence status is given in Table R4.

The conclusions are unchanged under the stricter accounting. The count of scenarios with hard service loss falls from 22 to 20 and its incidence among G1-containing combinations falls from 22/48 to 20/45, both as a direct consequence of removing two affected scenarios. More importantly, the **necessary-condition finding is untouched**: the 15 combinations excluding G1 yield no hard service loss under either accounting, and the G1-containing subset remains the only source of cascades. The trigger rate at four units moves from 60.0% to 61.5%, which preserves the monotonic progression across set sizes (0%, 6.7%, 25.0%, 61.5%, 100.0%, 100.0%) and shifts it marginally in the conservative direction.

One asymmetry does arise, and it bears on how the severity distribution should be read. The two non-converged scenarios with $H > 0$ are among the most severe in the set, with $H = 25$ and $H = 29$. Removing them removes two points from the upper tail, so the reported severity distribution is biased **upward** by their inclusion, and the true distribution is, if anything, slightly less severe than reported. The direction of this bias is therefore known and opposite to the concern that non-convergence might be masking a worse behaviour.

**Sensitivity to the operating point.** The sensitivity of the findings to the dispatch cannot be quantified from the present design, because all 63 scenarios share one base-case power flow and one initial dispatch (Section 3.3). This is not a limitation that can be discharged by re-analysis, and it is reported as such: the trigger-rate progression and the necessary-condition finding are conditional on the operating point, and the three attributes of G1 that the necessary condition depends on — slack status, low loading and large basin inventory — cannot be varied independently within it. What the enumeration does establish is that the finding is not an artifact of a single scenario, since it holds across 48 combinations that differ in composition and size, and fails to hold in all 15 that exclude G1. A genuine test of operating-point sensitivity requires either a set of operating points or a formal treatment of the slack bus as a dependent variable; both are identified in Section 5.4 as future work.

**Summary.** The one sensitivity test that the available data permit leaves the principal findings intact, and identifies the direction of the one bias it exposes. The remaining sources of uncertainty — parameter provenance, the uniform trip mechanism, the fixed operating point and the absence of a probability basis — are not testable within the present design and are stated as limitations rather than as results.

---


## 5. Discussion

### 5.1 What the mechanistic model adds

The central methodological claim of this study is that the trip time of a unit under concurrent cooling-water failure is a property of the failure set rather than of the unit, and that this property is inaccessible to a black-box treatment. The results support the claim on two counts (Table D1 sets out the representational difference in terms of capability rather than in numerical terms).

First, the advance in G1's trip time under concurrent failure is systematic and large — between 9.9% and 45.4% — and is not a constant. Were the coupling represented by a fixed coefficient or an imposed chronology, this advance could not appear at all, since it would be fixed by construction. Its dependence on set size (9.9–28.9% at two units rising to 40.3–45.4% at five) and on set composition (spreads of 19.0–24.2 percentage points within a single set size) are both consequences of the mechanism: redispatch redistributes output onto surviving units, which raises their rejected heat, which raises their evaporative demand, which accelerates their depletion. The chain itself is not new physics — makeup demand is understood as the sum of evaporation, drift and blowdown^14,15,16,17^, and evaporative loss scales with rejected heat — but its expression as a *combination-dependent* quantity is. A model in which the cold end is represented by a fixed coefficient or an imposed chronology cannot produce it, because in such a model the advance is fixed by construction rather than computed.

Second, the direction of this effect is established by the physics rather than assumed. The canonical case makes the chain explicit: the loss of G2 at 4.6564 h raises G1's output by 26.67 MW, which raises its makeup requirement by 57.1 m³/h, which accelerates its basin depletion from a 13.71 h isolated trip time to 9.74 h. This is the closed loop of Section 2.1.3 realized in a single scenario.

The position of this work relative to the closest existing study^21^ is consequently one of modelling pathway rather than of subject matter. That study treats cooling-water shortage through unit-level derating constraints and evaluates the consequences through system operation modelling, which is well suited to gradual depletion. The present work treats the failure as a protection-triggered trip, and thereby reaches a different class of observable: not how much output is lost, but when each unit becomes unavailable relative to the others, and whether that relative timing determines whether the disturbance propagates. These are complementary rather than competing treatments, and a study addressing both would be a natural extension. The same distinction applies to the cross-layer electricity–water coupling models developed for grid vulnerability assessment^37^, which represent the water side as a shared availability constraint rather than as a set of independently failing delivery paths; and to the parallel treatment of shared water systems in hydro-mechanical coupling^38^, whose object is the tailrace system rather than the cooling system but whose central concern — the coupling of multiple units through a common water inventory — is the same one that the present work treats through the thermal-hydraulic route.

The wider methodological position is that mechanistic dependency models remain scarce in the dependent-failure literature. The systematic review on which this argument rests distinguishes statistical from mechanistic approaches and notes the predominance of the former^24^; the regulatory treatment of multi-unit sites supplies a corresponding methodology for identifying dependency between units sharing plant-level infrastructure^26,27^. The present contribution is a worked instance of the mechanistic type in a specific physical configuration, and its value should be judged against the criterion that review sets out — whether the physical origin of the dependency is represented rather than merely its statistical signature.

**Table D1 | Representational capability: fixed versus mechanistic cold-end treatment.**

| Capability | Fixed representation | Mechanistic representation |
|:---|:---|:---|
| Depends on the initial operating point | No (preset coefficient) | Yes (driven by $P_{g0}$) |
| Depends on failure-set composition | No | Yes (independent integration per unit) |
| Yields a trip ordering | No (order must be prescribed) | Yes (set by the water-loss rate) |
| Feeds back to the grid side | No (open loop) | Yes (makeup $\to$ ramp $\to$ grid) |
| Distinguishes the mechanism of service loss | No | Yes ($H=\mathbb{1}[\mathrm{F3}]$) |

> The comparison is qualitative and carries no numerical content. "Fixed representation" denotes any treatment in which trip times are prescribed by coefficients or by an imposed chronology. The cost of the mechanistic representation is that it requires cold-end parameters; in the present case those on the coupling side are reference assumptions rather than field measurements (Table M2), which is the principal limitation of the mechanistic route in this instance.


### 5.2 The necessary condition, and what limits it

Within this operating point, G1's presence is a necessary condition for hard service loss: none of the 15 combinations excluding G1 produced any, while 22 of the 48 including it did. The condition is not sufficient, as the eight non-cascading two-unit combinations containing G1 demonstrate.

This result is of a different kind from the topological identification of pivotal components by graph-theoretic analysis^6^, and the difference is worth stating. Graph approaches identify elements that are structurally connected to many others, and they do so from topology alone, without reference to the operating state or to any physical failure process. The condition identified here is *operational*: it holds because of a specific combination of slack status, loading and basin inventory in a specific dispatch, and it is not recoverable from the network graph. That it does not survive a change in the operating point — which has not been tested — is precisely the point. The methodological literature on cascade simulation has long distinguished vulnerability assessment from the dynamic behaviour that follows a disturbance^2,5^, and the present finding belongs to the second category.

Two features of this result require care, and both bear on how the condition should be interpreted.

**The condition is a statement about a particular unit in a particular position, not a general property of large or pivotal generators.** G1 is simultaneously the system's slack unit, the lowest-loaded unit at 29.4% of rating, and the unit with the largest basin inventory at 3.2 m of headroom above its trip level. These three attributes cannot be separated in the present data: a unit that is slack, lightly loaded and endowed with a large basin is a compound description of G1, and the analysis cannot determine which of the three is responsible for the outcome. The absence of hard service loss in the 15 G1-excluding combinations is thus a fact about a specific configuration, and any extension to other systems would need to establish which attribute carries the effect. This is a limitation of the single-operating-point design rather than a finding about slack units in general.

**The trigger rate is also confounded with G1's presence.** The progression from 0% to 100% across set sizes holds both in the full set and within the G1-containing subset (11.1%, 31.2%, 64.3%, 100.0%, 100.0%), which is reassuring, but the full set cannot contain a five- or six-unit combination that excludes G1. The condition and the size effect are therefore not fully separable, and the present data cannot establish which dominates.

A related observation is that the strongest single predictor available — the timing of G1's own trip — is predictive but not determinative, as Section 4.3 establishes. The overlap between the two outcome groups across 8.4397–9.7383 h, and the interleaving of five scenarios of each type within it, mean that neither a trip-time threshold nor any other single observable can serve as a criterion for cascade onset in this operating point. The practical implication is that pre-failure screening of failure sets would require the combination's full trajectory, not a summary statistic. This bears on the wider question of whether cascade onset can be predicted *before* the initiating failure, a problem on which the branching-process approach^7,8^ offers a statistical rather than a mechanistic answer, and which the present results answer only in the restricted sense that the cold-end trajectory itself is the informative object.

### 5.3 Why the cascade is topological rather than dynamic, and what that depends on

The finding that the 23-bus loss in the canonical case arose entirely through F3, with the frequency nadir at 59.36 Hz and UFLS inactive, is more than a description of one scenario. It bears on how this class of failure should be assessed.

The distinction is between two mechanisms with different precursors and different mitigation. A frequency-driven cascade requires the frequency to traverse the UFLS stages and is therefore preceded by a measurable frequency excursion; the 24 scenarios in which UFLS acted span 57.96–59.28 Hz and were unambiguously dynamic, and the settings that produced this behaviour are those of the current UFLS requirements^33^ and the corresponding relay-application guidance^34^. A topologically driven cascade arises when generating capacity is lost in a configuration whose transmission structure cannot sustain the remaining load, and may proceed with the frequency essentially undisturbed. The service loss in such a case is not preceded by a frequency signature at all.

This distinction is of a kind that the cascade literature has had to grapple with. The 2003 North American blackout report attributed a substantial share of the final collapse to the progressive tripping of generators by protection actions, a mechanism that spans the boundary between frequency and topology and that motivated the protection-coordination reviews subsequently issued^35^. The present results show that under the capacity-rich operating point established in Section 4.4 the two mechanisms can separate cleanly, and that the topological one can produce near-total service loss with the frequency essentially undisturbed. Whether such a separation is observable in practice depends on monitoring, and it is precisely here that the mechanism identification carries practical weight.

This has a practical implication for the monitoring question. If the loss of service in a cold-end failure cascade is topological, then frequency monitoring is an insensitive detector of the precursor, and a precursor may lie instead in the redispatch trajectory — the rising output of surviving units, and the rising makeup demand that accompanies it. This is a hypothesis raised by the present results rather than one tested here, since no monitoring-design study was undertaken, and it is listed among the directions for future work below.

The worth of a negative result deserves to be stated plainly, because a null finding invites the question of whether the apparatus that produced it was needed at all. It was. The claim that the voltage mechanism did not participate is a claim about the physics, and it is available only from a model that represents that mechanism and then finds it inactive: without the island power-flow solution, the VCLS procedure and the solvability test, the same simulation record would have supported only the weaker statement that voltage behaviour had not been examined. The unsolvable branch of F3 is empty not because the model cannot reach it — an island with no solution is assigned F3 — but because no island reached it, and the same holds for the frequency channel — that frequency was undisturbed is established by the trajectory having been computed rather than assumed. The grid-side model here therefore serves to **exclude** mechanisms rather than to produce them. That is a less visible contribution than generating a larger cascade would have been, but it is the one on which the mechanism finding rests, and it is what distinguishes the assertion "service loss is topological" from the untested default that it is assumed to be.

It should also be noted that the two mechanisms are not exclusive. The clearest instance is the five-unit combination G1+G2+G13+G22+G27, in which the frequency reaches 57.96 Hz, UFLS acts, and 29 buses are lost; here static curtailment and frequency-driven curtailment coexist, contributing up to 173.2 MW and 57.1 MW respectively. Any assessment that treats the two as alternatives would understate the compound cases, and the same caution applies to the general point that protection modelling remains an incompletely resolved element of many cascade frameworks^12^. It is likewise consistent with the finding that cascade propagation can be dynamically induced even where the network topology is not itself degraded^11^, and the present results extend that observation by showing that the converse also occurs: a cascade that is purely topological, and that proceeds without the dynamic signature by which cascades are conventionally detected.

### 5.4 Limitations and future work

The following limitations qualify the findings above.

**Parameter provenance.** The coupling-side parameters are not field-measured and the cold-end parameters are engineering anchors rather than measurements (Section 2.5.2, Table M2); the conclusions are conditional on this parameter set. The influence of parameter uncertainty has not been quantified, because the ranges and sampling strategy for a sensitivity study have not been fixed and no such study was undertaken. This is a deliberate omission rather than an oversight, and it is the most consequential gap in the present work. The engineering literature provides the bounds that such a study would need — plant water usage and loss characteristics^17^, and the standard cooling-tower water balance and concentration definitions^14,15,16^ — but the coupling-side values used here are reference assumptions, and their uncertainty is unquantified.

**Solver convergence.** Three of the 63 scenarios did not converge, and their reported $H$ values are conditional on unproven internal convergence. Excluding them leaves the necessary-condition finding and the monotonic trigger-rate trend intact, but the two non-converged scenarios with $H > 0$ are among the most severe in the set, so the severity distribution may be biased upward by their inclusion (Sections 2.4.2 and 4.6). The broader concern is the one raised by the benchmarking literature: cascade-analysis tools are difficult to validate in the absence of cross-tool comparison on common scenarios^3^, and the present study is a single-tool, single-scenario-family application that has not undergone such comparison.

**Test system size.** The IEEE 30-bus system is small by the standards of cascade analysis: the benchmarking literature notes that cascading is inherently a large-scale problem and that most forms of cascading failure analysis call for test cases of at least 100 buses^3^. With 30 buses and six units, the present system cannot exhibit the long-range propagation paths or the depth of cascade stages available in larger networks, and the absolute bus counts reported here should be read with that ceiling in mind. The enumeration is complete for the system studied, which is what makes the *relative* findings — the necessary condition and the monotonic trigger rate — interpretable; the *absolute* magnitude of service loss is not transferable to larger systems.

**Capacity position, and the scope of the mechanism finding.** The finding that service loss is topological rests on a system that is capacity-rich at every stage: 189.2 MW of load against 335 MW of installed capacity, a system load factor of 56.5%, and a capacity margin that is never negative in any of the 63 scenarios (Section 4.4). A system operating closer to its loadability limit would place the post-contingency operating point nearer the nose of the P–V curve, where the same failure set could open a voltage-collapse pathway instead of, or in addition to, the topological one; the unsolvable branch of F3 would no longer be empty, and the mechanism could differ in kind rather than in degree. The mechanism finding is therefore conditional on the load factor, and it should not be carried over to more heavily loaded systems without re-examination. The present design cannot reach that regime, because the operating point is shared by all 63 scenarios and was not varied.

**Location of shed load under VCLS.** The shedding procedure allocates unserved load across buses in proportion to bus load (Section 2.3.3). This is a uniform-shedding approximation, and it departs from practice in the *location* of the shed load rather than in its amount: practical undervoltage schemes act through distributed relays at buses where voltage falls below a threshold, typically shedding 5–20% per step at settings of 0.85–0.95 p.u. with time delays of 1–10 s^40,41^, and the choice of location materially affects outcomes. The amount is in a defensible range — VCLS sheds a median of 9.6% of the surviving island's load and never more than 40.5% — but a scheme that targeted the weakest buses would shed less total load for the same stabilising effect, and would redistribute it. Since $H$ counts only F3 buses, this limitation affects the shed-load figures and not the hard service loss counts.

**The solvability test behind the unsolvable branch of F3.** F3 is assigned to an island where the power flow has no solution at any load level. Non-convergence of a Newton-type solver is evidence about the algorithm and not necessarily about the physics: divergence can reflect a poor initial guess or numerical ill-conditioning rather than the absence of a solution, and only continuation or holomorphic-embedding methods give certainty about feasibility^42,43^. This is a genuine limitation of the test. Its bearing on the present results is nevertheless nil, because the unsolvable branch is empty in all 63 scenarios and every one of the 366 lost buses is source-free; the finding that service loss is topological under this operating point does not rest on a single instance of the divergence test. Confirming that emptiness with a continuation or holomorphic-embedding solver would remove the caveat entirely and is a straightforward extension.

**Uniformity of the trip mechanism.** All 184 trips were triggered by the low basin level criterion (Section 2.5.1); the results therefore describe behaviour under a single protection pathway. Configurations with smaller basin margins, faster makeup interruption or different pump characteristics could reorder the mechanisms and change the timing relationships that underlie the findings, and this sensitivity is untested. This matters more than it might appear, because the ordering of protection criteria relative to generator frequency protection settings^32^ determines whether a cold-end trip is the initiating event or a consequence of an earlier disturbance.

**Operating point.** All 63 scenarios share one base-case power flow and one initial dispatch (Section 3.3). The confounding among G1's slack status, low loading and large basin inventory (§5.2) cannot be resolved within this design, because varying the loading of a slack unit necessarily changes the operating point. Resolving it requires either a set of operating points or a formal treatment of the slack bus as a dependent variable.

**Absence of a probability basis.** The scenarios are a deterministically specified enumeration, and the results are reported as conditional outcomes rather than as expected quantities. No expected energy not served is computed, since doing so would require probability weights that the protocol does not supply. A probabilistic treatment, in which failure sets are sampled with weights reflecting plausible water-availability scenarios, would allow the findings to be expressed in risk metrics and is the most obvious extension of the present work. This is the direction taken by the probabilistic modelling literature for cascading dynamics^10^, and it is the route by which the deterministic conditional results reported here would acquire a risk interpretation.

**Scope of the mechanism.** The failure mode modelled is a single category — makeup-line rupture — and the thermal-hydraulic detail is lumped. Fouling, blockage and freezing are not represented, and the tower and condenser are reduced-order representations. The literature on dynamic cooling-system behaviour indicates that an equivalent treatment of the condenser as part of an integrated hydraulic system, with dynamic fouling rather than a fixed factor, is the state of the art^13^; the present model approximates this but does not implement the fouling dynamics, and its cold-end parameters are correspondingly less grounded.

**Unvalidated against data.** The model has not been validated against measurements from an actual plant. The literature notes that such validation is an essential and non-trivial step in this class of model^13^, and the absence of validation is a limitation of the present work independent of the parameter-provenance issue.

Several directions follow. The most immediate is a sensitivity study over the coupling-side parameters, together with a formal treatment of the slack-bus confound, which together would establish how much of the necessary-condition finding is robust. Second, a probability-weighted enumeration, following the probabilistic treatment of cascading dynamics^10^ and the dependency-modelling framework of the reliability literature^24,25^, would convert the conditional findings into risk statements. Third, extending the enumeration beyond IEEE 30^29,30^ and to more than one operating point would test whether the necessary condition is a property of the configuration or of the system; cross-system comparison of the kind the cascade-tool benchmarking literature calls for^3^ would strengthen it further. For the mechanism finding the most direct test is a load-scaling study in which system loading is raised while the failure protocol is held fixed, which would locate the load factor at which the topological mechanism gives way to a voltage-driven one — or establish that it does not within the usable range. Fourth, the monitoring hypothesis raised in §5.3 — that the redispatch trajectory, rather than the frequency, is the sensitive precursor — is testable within the present framework by comparing the observability of the two quantities. Fifth, because the present failure set is concurrent but not common-cause^25^, extending the protocol to include a genuine common-cause event — a shared upstream source failure, the configuration addressed by the multi-unit PSA methodology^27^ — would allow the contrast between the two regimes to be drawn within a single model.


---

## 6. Conclusions

The two objectives of this study were to replace the black-box treatment of the cooling-water system with a mechanistic model in which trip time is emergent, and to use that model to characterize the cascading consequences of concurrent failure across the complete enumeration of failure sets. Both were met within a single operating point.

The mechanistic model converts trip time from an input into an output, and in doing so exposes a structure that a black-box representation cannot produce: under concurrent failure, the same unit trips 9.9–45.4% earlier than under isolated failure, with the advance governed by set size and set composition alike. The consequence of this coupling for system-level outcomes is a necessary-but-not-sufficient condition — G1's presence — together with a trigger rate that rises monotonically from 0% to 100% with the number of failed units. That condition is a property of a particular configuration rather than a general law, and it is confounded among G1's three simultaneous attributes as slack unit, light-loaded unit and large-basin unit, which the present design cannot separate.

A second finding concerns mechanism, and it is conditional on the capacity position of the test system. The service loss in the canonical case is topological rather than dynamic: 23 buses lost through F3 following the loss of both generating buses, with the frequency nadir at 59.36 Hz and UFLS inactive. Across the full enumeration all 366 lost buses are separated from in-service generation, with the unsolvable branch of F3 never taken. In the canonical case the loss is produced by the cascade rather than present at the instant of unit loss: with overload tripping disabled, the same failure set yields no service loss at all. That the unsolvable branch stays empty is attributable in part to the system being capacity-rich throughout — a load factor of 56.5% and a capacity margin that is never negative — rather than solely to the physics of cold-end failure (Sections 4.4 and 5.4). The practical implication, offered as a hypothesis for future work rather than as a demonstrated result, is that the sensitive precursor to such a cascade may lie in the redispatch trajectory rather than in the frequency.

The scope of these conclusions is bounded and has been stated explicitly throughout: one capacity-rich operating point at a 56.5% system load factor, one six-unit subset, anchor rather than measured cold-end parameters, reference rather than measured coupling parameters, one protection mechanism actually exercised, three scenarios of unproven numerical convergence, and no validation against plant data. Within those bounds the results stand. Beyond them, the most valuable next steps are the sensitivity study and probability-weighted extension identified above.

---

## References

1. IEEE PES CAMS Task Force on Understanding, Prediction, Mitigation and Restoration of Cascading Failures. *Initial review of methods for cascading failure analysis in electric power transmission systems.* IEEE PES General Meeting, Pittsburgh, PA (2008). DOI: 10.1109/PES.2008.4596430.
2. IEEE PES CAMS Task Force. *Risk assessment of cascading outages: methodologies and challenges.* IEEE Trans. Power Syst. **27**, 631–641 (2011).
3. IEEE Working Group on Understanding, Prediction, Mitigation and Restoration of Cascading Failures. *Benchmarking and validation of cascading failure analysis tools.* IEEE Trans. Power Syst. **31**, 4887–4900 (2016).
4. Guo, Z., Sun, K., Su, X. & Simunovic, S. A review on simulation models of cascading failures in power systems. *iEnergy* **2**, 284–296 (2023).
5. IEEE PES CAMS Task Force. *Vulnerability assessment for cascading failures in electric power systems.* IEEE PES Power Systems Conf. and Exposition, Seattle, WA (2009).
6. Sun, K. et al. Interaction graphs for cascading failure analysis in power grids: a survey. *Energies* **13**, 2219 (2020). DOI: 10.3390/en13092219.
7. Dobson, I., Carreras, B. A., Newman, D. E. et al. *Risk analysis of critical loading and blackouts.* Lawrence Berkeley National Laboratory Final Report.
8. Dobson, I., Carreras, B. A. & Newman, D. E. A branching process approximation to cascading load-dependent system failure. *IEEE Int. Conf. Circuits Syst.* Vancouver, Canada (2004).
9. Carreras, B. A., Dobson, I. & Newman, D. E. *Cascading failures in power grids: risk assessment, modeling, and simulation.* Springer (2024).
10. Mousavi, S. A. et al. A probabilistic model for the dynamics of cascading failures in power grids. *IEEE PES General Meeting* (2012).
11. Zhang, J. et al. Dynamically induced cascading failures in power grids. *Nat. Commun.* **9**, 2897 (2018).
12. Valivarthi, R. et al. A systematic review on cascading failures models in renewable power systems with dynamics perspective and protections modeling. *Int. J. Electr. Power Energy Syst.* (2022).
13. Souza, A. J. et al. The dynamic behavior of once-through cooling water systems under fouling phenomena. *Heat Transfer Eng.* **43**, 15–16 (2021). DOI: 10.1080/01457632.2021.1963083.
14. EnergyPlus Engineering Reference. *Cooling towers and evaporative fluid coolers.* U.S. DOE, Building Technologies Office.
15. Bhatia, A. *Cooling towers.* CED Engineering, Course M07-001 (2013).
16. Public Utilities Board (Singapore). *Technical reference for water conservation in cooling towers* (2017).
17. U.S. DOE/NETL. *Power plant water usage and loss study* (2007).
18. Kenny, J. F. et al. The water implications of generating electricity: water use across the United States based on different electricity pathways through 2050. *Environ. Res. Lett.* **7**, 045803 (2012).
19. Macknick, J. et al. *A review of operational water consumption and withdrawal for thermoelectric power generation.* NREL/TP-5000-50900 (2011).
20. Macknick, J. et al. The water–energy nexus: a comprehensive review of the interrelationships between water and energy. *WIREs Energy Environ.* (2015).
21. Zhang, Y. et al. Power generation–cooling water nexus: impacts of cooling water shortage on power system operation—a simulation case study in Illinois, U.S. *Appl. Energy* (2024). DOI: 10.1016/j.apenergy.2024.124863.
22. Jurasic, T. et al. Regional and seasonal water stress analysis of United States thermoelectricity. *J. Clean. Prod.* **260**, 120686 (2020).
23. Frew, B. et al. Global scenarios for significant water use reduction in thermal power plants based on cooling water demand estimation using satellite imagery. *Nat. Energy* **4**, 1065–1072 (2019).
24. Zio, E. Dependent failure behavior modeling for risk and reliability: a systematic and critical literature review. *Reliab. Eng. Syst. Saf.* (2023).
25. NUREG/CR-5485. *Guidelines on modeling common-cause failures in probabilistic risk assessments.* U.S. NRC/INL (1998).
26. NUREG/CR-6268, Rev. 1. *Common-cause failure database and analysis system.* U.S. NRC/INL (2007).
27. IAEA-TECDOC-1820. *Technical approach to probabilistic safety assessment for multiple-unit nuclear power plant sites.* IAEA (2018).
28. U.S.–Canada Power System Outage Task Force. *Final report on the August 14, 2003 blackout in the United States and Canada.* NERC (2004).
29. IEEE PES CAMS Task Force & NERC. *IEEE 30-bus test system.* Power Systems Test Case Archive, University of Washington.
30. Molzahn, F. et al. *The Power Grid Library for benchmarking AC optimal power flow algorithms.* IEEE PES Task Force on Benchmarking AC Optimal Power Flow Algorithms.
31. Overbye, T. et al. Modeling and analysis of cascading failures in large-scale power grids. *IEEE PES General Meeting* (2011).
32. NERC PRC-024-3. *Frequency and voltage protection settings for generating resources.* North American Electric Reliability Corporation (2020).
33. NERC PRC-006-SERC-02. *Automatic underfrequency load shedding requirements.*
34. IEEE Std C37.117-2007. *IEEE guide for the application of protective relays used for abnormal frequency load shedding and restoration.*
35. NERC & IEEE PES Joint Session. *Power plant and transmission system protection coordination.* Technical Reference Document, Rev. 2 (2015).
36. NERC. *Considerations for power plant and transmission system protection coordination.* Technical Reference Document.
37. 张剑, 等. 基于电—水跨层耦合模型的城市电网脆弱性评估. *电力系统自动化* **48**, 16 (2024).
38. 刘振亚, 等. 水电站多机共用尾水系统并网运行稳定性及动态特性分析. *水力发电学报* **44**, 2 (2025).
39. ISO New England Inc. *Whitepaper on transient voltage response criteria.* ISO-NE Planning Advisory Committee (2022).
40. NERC. *PRC-010-2 — Undervoltage load shedding.* North American Electric Reliability Corporation.
41. *Techno-economic impacts of automatic undervoltage load shedding under emergency.* (2015). DOI: 10.1016/j.ijepes.2015.11.001.
42. Trias, A. The holomorphic embedding load flow method. *IEEE PES General Meeting* (2012); Mehta, D. & Turitsyn, K. Recent advances in computational methods for the power flow equations. *IEEE American Control Conf.* (2016).
43. *Power flow feasibility assessment: distinguishing non-convergence from infeasibility.* arXiv:2607.09122.

---

*The complete working catalogue, with the citation-distribution plan and the mapping between library numbering and the numbering used here, is given in `docs/参考文献库.md`.*

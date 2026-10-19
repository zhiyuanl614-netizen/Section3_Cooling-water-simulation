# Mechanistic modeling of wet-recirculating cooling contingencies for cascading failure assessment in power systems

**[Author Name 1]^a,*, [Author Name 2]^a,b, [Author Name 3]^b**

^a *[Department / Institute, University / Organization, City, Postal Code, Country]*  
^b *[School / Key Laboratory, University / Organization, City, Postal Code, Country]*  
*\* Corresponding author. E-mail address: `[corresponding.author@institution.edu]`*

> **Submission-formatted illustrated candidate, v0.7.2 — 17 October 2026.** The three original research questions are retained verbatim from the historical manuscript, with RQ1–RQ3 evidence (including the migrated v0.7.2 six-encoding, five-load and G34 adequacy comparisons), six newly rendered 170 mm figures, 11 tables, 27 editable display equations and all 59 full-title bibliographic entries verified. Author names, affiliations and funding numbers above and in the Declarations section are structured placeholders to be filled in by the authors prior to journal upload; external plant transient calibration remains an explicit future-work boundary (`NOT_ESTABLISHED_DATA_GAP`).

## Highlights

1. Inventory, flow and pressure states resolve different cooling-failure pathways.
2. Finite condenser storage preserves the steady UA map without a trip-driven target.
3. Single/dual-unit DC consequences depend on balancing and branch-removal rules.
4. Mechanistic UAE remains 52.03–53.31% below immediate loss in the tested settings.
5. Inadmissible zero-lag controls are excluded rather than given finite bias factors.

## Abstract

Cooling emergencies are often represented as prescribed derating or immediate generator loss, although wet-recirculating plants lose capability through distinct inventory, hydraulic and pressure pathways. We formulate a reference-anchored, finite-storage cold-end surrogate and pass its available-power trajectory as a ceiling to separate DC adequacy and overload-propagation models without fitting site transient data. For a 652 MW equivalent unit, makeup interruption reaches low-level protection at 5.047 h with blowdown isolation versus 3.855 h with maintained blowdown, whereas holding initial steam duty trips at 4.296 h (2796.950 versus 2738.433 MWh reference energy). Across an 18-setting thermal stress matrix, makeup trips remain inventory-controlled at 4.907–5.065 h, while full pump-loss trips span 42.43–572.50 s. At 1.15 times demand on the IEEE 39-bus network, one-minute event-aware DC adequacy integration gives 2170.680 MWh incremental unserved energy for reference ride-down versus 4634.437 MWh for immediate loss (−53.16%; 18-setting LP-dual/monotone bounds: 52.025–53.306%); migrating all six benchmark encodings, five demand levels (1.00–1.20) and unit G34 confirms this ordering across 36.13–63.09% reduction. Recoupled state-carrying DC cascade snapshots across dual 50% pump-loss derating (615.715/479.729 MW), single-unit loss, detuned makeup first trip (G34 = 0, G33 = 351.663 MW at 4.274 h) and dual-zero ceilings show non-monotonic rule dependence: under nominal simultaneous headroom redistribution (H), the detuned intermediate state removes 11 branches and sheds 1909.5 MW (14 branches and 3154.9 MW at 0.9 ratings), exceeding single-unit (1753.2 MW) and dual-zero (1087.2 MW) outcomes. A 34-setting exact-zero lag ablation separates inadmissible zero-storage/zero-flow pump-loss controls from valid conditional and joint ablations: omitting condenser storage in full pump loss understates trip time by 89.660% (10.063 versus 97.315 s), omitting all three lags in 50% pump loss causes a spurious 3.0005 s trip (−99.989% energy), and omitting condenser storage in makeup interruption shifts trip time by +93.0 to +94.0 s (−9.826 to −10.018 MWh unserved energy).

**Keywords:** wet-recirculating cooling; basin inventory; condenser thermal storage; capability trajectories; DC adequacy; island balancing

## Nomenclature

| Symbol | Definition | Unit |
|---|---|---|
| $A,H,H_0,H_s,H_{trip}$ | basin area; actual, normal, SOP-start and trip levels | m²; m |
| $E,B,D,M_{ext}$ | evaporation, blowdown, drift and external makeup | m³/s |
| $Q_{steam},Q_{water}$ | prescribed steam-side heat input and actual water-side transfer | MW$_{th}$ |
| $W,G,UA$ | water heat-capacity rate, effective exchange coefficient, overall conductance | MW/K |
| $C_{eff}$ | reference-anchored effective condenser heat capacity | MJ/K |
| $T_{in},T_{out},T_s,T_{wb}$ | condenser water inlet/outlet, saturation and wet-bulb temperatures | °C |
| $Q_{cw},x,r_a$ | circulating-water flow, its design fraction, tower air-flow ratio | m³/s; –; – |
| $\rho_w,c_{p,w},h_{fg},g$ | water density, specific heat, latent heat, gravitational acceleration | kg/m³; J/(kg K); J/kg; m/s² |
| $P_r,P_0,P_{cap},P_{rated}$ | reference-operation power, its initial value, control target, rating | MW |
| $P_{avail},p_g,\bar p_g$ | exported capability, actual grid injection, generator ceiling | MW |
| $p_b,p_{ref},p_{air},p_{atm}$ | backpressure, reference, air partial and atmospheric pressure | kPa(a) |
| $R_{ramp},p_{min}$ | ramp fraction per minute and technical-minimum fraction | min⁻¹; – |
| $\tau_{cond,des},\tau_{tower},\tau_{pump},\tau_{wb}$ | design-point condenser anchor and tower/pump/weather lag constants | s |
| $\Delta t_s,\Delta t_{vac},\Delta t_{bd}$ | integration interval, vacuum delay, blowdown-detection delay | s |
| $q_c,D_c,G_c,C_c$ | island supply target, inherited demand/generation and total ceiling | MW |
| $F_{ij},d_i,\theta_i$ | branch flow, served bus demand and voltage angle | MW; MW; rad |
| $\rho_{rate},\delta,S_B$ | rating multiplier, overload tolerance and electrical base | –; MW; MVA |
| $L(c),U,E_r$ | optimized shed load, incremental UAE, reference-operation energy | MW; MWh; MWh |

Thermal equations use seconds unless stated otherwise; energy integration uses hours. All pressure-to-head conversions explicitly convert kPa to Pa. A bar over a quantity denotes a ceiling or interval average, as specified locally; it does not denote an ensemble mean. The cold-end reference-operation output is not the actual dispatched output of a grid-connected unit.

## 1. Introduction

Thermoelectric production depends on continuous heat rejection. In wet-recirculating systems, evaporation, drift and blowdown require makeup water to sustain inventory [6,7,10,16,17]. Heat waves, low flows and water constraints can reduce thermoelectric availability and affect regional dispatch and adequacy [2–5,8,9,11–15,43–46]. System-level models often represent these constraints as generator availability limits or prescribed output schedules [1,9,12,43,44]. Such representations are useful for their intended planning scale, but do not by themselves resolve the emergency pathway from an interrupted makeup supply or circulating-pump failure to a protection event.

At the equipment boundary, tower-transfer methods, condenser design practice and pump/NPSH guidance provide engineering structure [18–22,26–29]. They do not uniquely identify dynamic thermal storage, pump coastdown, protection settings or operator actions for a generic unit. Published cold-end studies examine load and ambient disturbances [23–25], detailed condenser fault simulations [47], and steam-condensation experiments [56–58]. The distinction between those sources and validation of a particular reduced-order model is essential. In particular, an independently modelled nuclear bypass transient cannot calibrate a coal-unit effective heat capacity merely because the reported times have a similar order of magnitude.

A second modelling boundary appears at the transmission system. A capability ceiling does not specify the realized generation or the balancing response after a disturbance. DC cascade models use different generation, demand and branch-removal rules [30,31,50–55]. Consequently, cooling-loss magnitude alone cannot establish the number of overload trips or the final served load. A topology-only sequence also lacks a calibrated physical protection clock [33,48].

The research questions are unchanged from the historical manuscript. RQ1 asks how makeup interruption, pump outage and wet-bulb stress produce distinct trajectories and trip labels; RQ2 asks how single- and dual-unit capability loss interacts with island balancing, reserve response and branch-removal rules; RQ3 asks how black-box outage encodings and omission of second-to-minute plant lags bias the studied outcomes.

The contributions remain organized around a multi-contingency cold-end model (RQ1), a state-carrying island-balanced DC outlet with explicit response assumptions (RQ2), and comparisons of outage encoding and plant-lag representation (RQ3). Finite-storage repair and deterministic thermal-parameter checks strengthen the evidence rather than introduce a replacement research objective. To answer RQ3 in full without fabricating an equilibrium where none exists, the encoding comparison is paired with a fault-specific exact-zero lag-ablation design across all three endogenous plant lags ($\tau_{cond,des}$, $\tau_{tower}$, $\tau_{pump}$) plus the exogenous wet-bulb ramp ($\tau_{wb}$), explicitly separating physically inadmissible zero-storage/zero-flow controls from converged conditional and joint omission biases. Recoupled v0.7.2 single-unit, dual-derate and detuned two-unit capability snapshots address response, rule and rating dependence across all 8 minimal-gate and 60 robustness/decorrelation settings within RQ2 while keeping independent state snapshots distinct from a continuous topology-carrying time-domain cascade. Sections 2–3 define the model and experiments, Section 4 reports the evidence, and Sections 5–6 distinguish supported answers from remaining gaps. The DC policies are explicit scenarios, not calibrated governors, and the separate clocks do not constitute an accelerated multirate plant algorithm.

## 2. Methods

### 2.1 Model boundary, operating reference and evidence hierarchy

The mother archetype is a 500 MWe wet-recirculating coal unit. Capacity scaling preserves intensive reference quantities while scaling design circulating flow and basin area with rating. Two IEEE 39-bus equivalent machines, at buses 33 and 34, are designated as mapped wet units. Current transient and thermal-stress results concern G33; this scope is not silently extended to a recomputed full G34 experiment set.

The cold-end solver advances a reference-operation power $P_r(t)$, inventory, flow and thermal states. Before protection, the trajectory exported to the grid is $P_{avail}=P_r$; after the first trip it is zero. In each grid solve, actual injection satisfies $0\le p_g\le\bar p_g$, with the mapped ceiling given by $P_{avail}$. The steam-duty surrogate depends on $P_r$, not on the injection selected by the grid optimizer. Thus the coupling is one-way: it is not a closed-loop simulation of steam duty responding to network redispatch.

Evidence is classified by purpose: conservation and algebraic closure; standards/design semantics; related empirical or modelling literature; transparent scenario assumptions; and numerical sensitivity/verification. None of these labels alone constitutes site validation. Reference parameters remain `reference_template_not_site_measured`. Effective storage and tower dynamics are unidentifiable from healthy steady observations in this formulation, so their sensitivity settings are not presented as measured intervals.

The numerical implementation is in `cooling/dynamics.py`, `cooling/transient.py` and `cooling/prototype_500mw.py`. The operational meaning of the equations below is the declared surrogate, not a claim to reproduce full steam-volume compressibility, wall/water inventories or tower humidity dynamics.

The model interfaces and one-way coupling are summarized in Fig. 1.

![Figure 1: Finite-storage cold-end pathway and independent DC outlets.](figures/fig01.png){width=170mm}

**Figure 1. Finite-storage cold-end pathway and independent DC outlets.** a, Steam-side duty, condenser storage, water-side heat transfer, the lagged cooling inlet and basin/pump availability form the implemented thermal–inventory pathway. Arrows indicate model dependencies, not an equipment drawing or a complete steam-cycle balance. Protection acts on monitored states and the exported capability, not on the process temperature target. b, Available capability is an upper bound on actual injection and is passed to separate DC adequacy and S/H overload-propagation models. Adequacy integrates incremental unserved energy; cascade probes report terminal shedding, cuts and island states. Network redispatch is not fed back into the thermal reference. This is a conceptual schematic, with no measured observations or statistical sample.

### 2.2 Steam duty, serial heat exchange and finite storage

For positive reference-operation power, the steam-side input is prescribed by

$$
Q_{steam}(P_r)=f_{cond}P_r\left[\eta_{net}(P_r)^{-1}-1\right],\qquad
\eta_{net}(P_r)=\frac{\eta_{des}}{1+\alpha_{hr}(1-P_r/P_{rated})^2}.
\tag{1}
$$

The power fraction is clamped to its implementation range; zero power gives zero duty. Ride-down evaluates this function at the evolving $P_r$. Hold-load instead freezes the steam duty at its initialized value. The latter is a scenario convention, not a complete steam-cycle energy model linking backpressure, electrical work and all rejected heat.

With water density and specific heat in the units of the nomenclature, define

$$
W(x)=\frac{\rho_w c_{p,w}Q_{cw,des}x}{10^6},\qquad
UA(x)=UA_{des}f_{cl}x^m,\qquad
G(x)=W(x)\left[1-e^{-UA(x)/W(x)}\right],\quad G(0)=0.
\tag{2}
$$

Band multipliers, when used, multiply the equipment factors; current reference results use the base band. The instantaneous water-side heat and flowing outlet observation are

$$
Q_{water}=G(x)(T_s-T_{in}),\qquad
T_{out}=T_{in}+Q_{water}/W(x)\quad(x>0).
\tag{3}
$$

At zero flow there is no flowing outlet temperature; the output is marked undefined, not replaced by $T_s$. Saturation temperature remains a state. The steady limit $T_s=T_{in}+Q_{steam}/G$ is algebraically equivalent to the existing UA–LMTD map, for which

$$
UA_{des}=\frac{Q_{des}}{\Delta T_{des}}\ln\left(1+\frac{\Delta T_{des}}{TTD_{des}}\right),\qquad
\Delta T_{des}=Q_{des}/W(1).
\tag{4}
$$

The finite-storage surrogate is

$$
C_{eff}=\tau_{cond,des}G_{des},\qquad
C_{eff}\frac{dT_s}{dt}=Q_{steam}-Q_{water}.
\tag{5}
$$

Here $G_{des}$ is evaluated at clean design conditions, so cleanliness does not artificially change the reference heat capacity. At zero flow and positive capacity the model has a finite linear warming rate. A zero-capacity, zero-flow state with positive steam duty has no finite algebraic equilibrium and raises `NoQuasiStaticEquilibrium`; it is not assigned a protection-dependent temperature target. No dynamic/quasi-static full-loss trip-time ratio is defined for that singular case.

The tower is a design-anchored effectiveness surrogate, not a demonstrated complete Jaber–Webb, Merkel or Poppe implementation [19–22]. Its target uses actual positive water-side transfer:

$$
NTU=NTU_{des}K_{tower}(r_a/x)^n,\quad
\varepsilon=\min(0.999,1-e^{-NTU}),\quad
T_{in}^*=T_{wb}+\frac{\max(Q_{water},0)}{W(x)}\frac{1-\varepsilon}{\varepsilon}.
\tag{6}
$$

The design effectiveness is $\varepsilon_{des}=\Delta T_{des}/(\Delta T_{des}+\Delta T_{app,des})$, with $NTU_{des}=-\ln(1-\varepsilon_{des})$. Actual $T_{in}$ tracks its target through a tower lag; the condenser uses this actual inlet state, not the unlagged target. At exactly zero flow, the implementation holds $T_{in}$ rather than requesting an undefined flowing tower outlet. This is a boundary convention, not a model of stagnant-loop natural convection.

Backpressure uses the implemented empirical saturation relation

$$
p_b=p_{air}+0.6108\exp\left(\frac{17.27T_s}{T_s+237.3}\right)\quad\mathrm{kPa}.
\tag{7}
$$

The fixed air partial pressure and empirical saturation map are additional approximations. No independent steam-table error bound or gas-inventory validation is inferred from agreement at the design point.

### 2.3 Pump availability, heat-based water loss and inventory

A falling basin level raises static lift. For $H>H_{trip}$ the design-anchored hydraulic fraction is

$$
H_{st}=H_{st,des}+H_0-H,\qquad
x_h=\sqrt{\frac{\max(H_{sh}-H_{st},0)}{\max(H_{sh}-H_{st,des},10^{-9})}}.
\tag{8}
$$

The model estimates available and required NPSH using

$$
NPSH_a=\frac{10^3[p_{atm}-p_{sat}(T_{in})]}{\rho_w g}+H-z_{eye}-h_{suc},\qquad
NPSH_r=NPSH_{r,des}x_h^2.
\tag{9}
$$

With margin $m_{npsh}$, $x_n=\Pi_{[0,1]}[NPSH_a/(NPSH_r+m_{npsh})]$ and $x_{hyd}=\max(0,\min(x_h,x_n))$; at or below the trip level, $x_{hyd}=0$. This simple availability rule is motivated by pump/NPSH semantics [29], not a measured cavitation curve. Under fractional pump-capacity loss $f_{loss}$, the flow target is

$$
x^*=(1-f_{loss})x_{hyd},\qquad Q_{cw}=Q_{cw,des}x.
\tag{10}
$$

Only the pump-failure contingency applies the fractional-loss factor. Flow tracks this target with the prescribed pump lag. Reverse flow is not represented. The previous linear level-band map remains in software as a legacy option but is not used for current results.

Evaporation depends on actual water-side heat, rather than all instantaneous steam input:

$$
E=\frac{10^6 f_{evap}\max(Q_{water},0)}{\rho_w h_{fg}(T_{in})},\qquad
D=r_{drift}Q_{cw},\qquad
B^*=\max\left(0,\frac{E}{N_{CoC}-1}-D\right).
\tag{11}
$$

The latent-heat approximation is $h_{fg}=\max[2.20\times10^6,10^3(2501-2.43T_{in})]$ J/kg. The cycles-of-concentration balance sets the normal blowdown rule [28]; it is not a dynamic salt-concentration state. In makeup interruption, maintained blowdown uses $B=B^*$, whereas isolation sets $B=0$ after the stated detection delay. Emergency isolation therefore suspends the design salt-balance condition rather than preserving it at all times.

Basin inventory evolves only on the makeup-interruption path:

$$
A\frac{dH}{dt}=-(E+B+D-M_{ext}).
\tag{12}
$$

External makeup is zero on that path. In the pump and wet-bulb probes, basin level is held at its normal value; inventory depletion is deliberately not combined with those faults. Normal makeup matches the loss terms. The diagnostic hold-up $A(H_0-H_{trip})/M_{des}$ is not imposed as a trip time. The tower and piping do not have a fully resolved thermal-energy inventory; the exact condenser interval balance below must not be described as a whole-plant energy validation.

### 2.4 Reference-operation limits, initialization and protection

Healthy initialization uses the same iterative steady operating calculation as the equipment map, with requested load as an upper limit. It supplies $P_0$, $T_{in,0}$ and $T_{s,0}$ at design circulating flow. If this equilibrium already reaches the vacuum set-point, the input is explicitly rejected as IneligibleInitialState, rather than counted as a fault-induced immediate trip or silently resampled. The first recorded state at $t=0$ is this healthy pre-fault state.

Let $\Delta p=p_b-p_{ref}$. The thermal-capability factor is

$$
\phi(p_b)=\begin{cases}
\min[1+k_b(p_{ref}-p_b),1+c_b],&p_b\le p_{ref},\\
\max[0,1-k_{p,1}\min(\Delta p,\Delta p_{brk})-k_{p,2}\max(0,\Delta p-\Delta p_{brk})],&p_b>p_{ref},
\end{cases}\qquad P_{thermal}=P_{rated}\phi(p_b).
\tag{13}
$$

These coefficients are template assumptions for the backpressure–output map [25], not identified turbine characteristics. During makeup ride-down, the SOP cap before protection uses the continuation

$$
P_{SOP}=P_{rated}\left[p_{min}+(1-p_{min})\Pi_{[0,1]}\left(\frac{H-H_{trip}}{H_s-H_{trip}}\right)\right].
\tag{14}
$$

At the trip boundary this is the left-limit control target, not the post-trip power. Ride-down with an active makeup SOP uses $P_{cap}=\min(P_0,P_{thermal},P_{SOP})$; other current cases, including hold-load, use $P_{cap}=\min(P_0,P_{thermal})$. Both strategies obey the same reference-operation ramp rule:

$$
P_r^{+}=P_r+\Pi_{[-r\Delta t_s,r\Delta t_s]}(P_{cap}-P_r),\qquad
r=R_{ramp}P_{rated}/60.
\tag{15}
$$

Here $R_{ramp}$ is a fraction of rating per minute, so $r$ has units MW/s. Because hold-load also freezes steam input and omits the SOP cap, the strategy pair is not a single-factor causal ablation.

Protection checks the advanced state in ordered priority: low basin level; low hydraulic availability on makeup paths; sustained backpressure above the vacuum set-point; and technical minimum for makeup ride-down. The first applicable label is retained. The low-flow value $x_{fl}=0.05$ is a protection criterion, not a floor in the heat-transfer calculation. Technical-minimum detection uses the implemented 0.5 MW tracking tolerance. Vacuum dwell starts at the first detected above-threshold state and resets if pressure recovers; this discrete detection is resolved by step refinement, not by claiming exact continuous event localization.

At the first trip $t_*$, the recorded pre-trip reference power is preserved and the exported right limit is zero:

$$
P_{avail}(t_*^-)=P_r(t_*^-),\qquad P_{avail}(t_*^+)=0.
\tag{16}
$$

No post-trip plant recovery is simulated; zero capability is the grid boundary condition thereafter.

### 2.5 Integration and verification of the thermal surrogate

Tower, pump and optional wet-bulb states use exponential frozen-target updates,

$$
\xi^{+}=\xi^*+(\xi-\xi^*)e^{-\Delta t_s/\tau_\xi},\qquad
\xi\in\{T_{in},x,T_{wb}\}.
\tag{17}
$$

The condenser is not an additional fixed-target temperature lag. For frozen midpoint inlet $T_m$, coefficient $G_m$ and left-end steam duty $Q_0$, its interval solution is

$$
T_s^{+}=T_s+(1-e^{-z})(T_m-T_s)+\frac{Q_0\Delta t_s}{C_{eff}}\psi(z),\qquad
z=G_m\Delta t_s/C_{eff},\quad\psi(z)=\frac{1-e^{-z}}{z},\quad\psi(0)=1.
\tag{18}
$$

The corresponding interval-mean water heat is $\overline Q_{water}=G_m(T_s-T_m)\psi(z)+Q_0[1-\psi(z)]$. Thus

$$
C_{eff}(T_s^+-T_s)=\Delta t_s(Q_0-\overline Q_{water}).
\tag{19}
$$

This equality verifies the constant-input condenser interval, not exact integration of every coupled state. The actual implementation uses midpoint flow/weather holds, a lagged inlet midpoint, left-end steam duty and trapezoidal water loss for inventory. It splits steps at reporting, detection and horizon boundaries. A detection-time blowdown discontinuity is integrated with its left limit before switching the policy.

Verification includes healthy water-side closure, the original steady UA–LMTD limit, serial tower-to-pressure response, independence of the pre-trip physical trajectory from the protection set-point, correct initialization/time zero, both strategy ramps, zero-flow analytic heating, and an independent adaptive-ODE comparison. In the instantaneous-stop/constant-steam limit, independently calculated pressure-crossing times agree with the simulator within 0.051 s for three heat capacities. These are structural and numerical checks, not experimental calibration.

The current solver uses a common maximum step for the coupled plant equations, reduced for fast cases. It is not a heterogeneous-step multirate plant algorithm, and no computational-speedup claim is made. Separate grid snapshot clocks follow co-simulation principles [34–36] without introducing grid-to-plant feedback.

### 2.6 Separate DC adequacy and overload-propagation outlets

The propagation layer uses the local IEEE 39 reactance-only branch equivalents and case ratings [32], with $S_B=100$ MVA and explicit connected components after every topology change [50, 51]. Transformer branches use their stored series reactance without tap-ratio or phase-shift corrections; this is not an exact reproduction of every MATPOWER branch-model feature. Cold-end $P_\mathrm{avail}(t)$ is a generator **upper bound**, not a compulsory injection. Unmapped units retain case $P_\mathrm{max}$ ceilings. Initialize a lossless pre-contingency dispatch from case $P_g$, adjusting Bus 31 explicitly to 634.23 MW, within its 646 MW ceiling; then clip the mapped units to the specified capability bounds. Bus 31 does not supply unlimited post-fault balancing power. Equivalent-generator minima are zero; reserve ramp/delivery times and frequency dynamics are not calibrated.

For island $c$ at removal round $k$, let $D_c$ be inherited served demand, $G_c$ inherited actual generation, and $C_c$ the sum of available generator ceilings. Policy S uses no upward reserve; H allows all static headroom. Their balanced supply targets and proportional load update are

$$
q_c = \begin{cases}\min(D_c,G_c), & \mathrm{S},\\ \min(D_c,C_c), & \mathrm{H},\end{cases}\qquad d_i^{(k)}=d_i^{(k-1)}\frac{q_c}{D_c}\quad(i\in c,\ D_c>0). \tag{20}
$$

Zero inherited demand stays zero. Initial served demand is case demand; after every cut, each bus retains its previously served amount before Eq. (20) is applied. S follows the proportional shedding/curtailment baseline [50]. For available generator $g$ in $c$, bounded actual dispatch is

$$
p_g^{(k)}=\begin{cases}0,&q_c=0,\\ \dfrac{q_c}{G_c}p_g^{(k-1)},&0<q_c\le G_c,\\ p_g^{(k-1)}+(q_c-G_c)\dfrac{\bar p_g-p_g^{(k-1)}}{C_c-G_c},&G_c<q_c\le C_c\quad(\mathrm{H}).\end{cases} \tag{21}
$$

Here $\bar p_g$ is the capability ceiling. For initialization, $p_g^{(-1)}$ denotes the explicitly lossless base dispatch clipped to that ceiling. The second branch curtails surplus proportionally; the third allocates upward adjustment by remaining headroom. Studies motivate finite, policy-dependent generation/load adjustments [52–55], but the exact H participation rule is our transparent sensitivity assumption, not a reproduced governor controller. Neither policy optimizes congestion. A component with no available generation loses all served demand; intact de-energized branches are distinguished from overload-tripped branches.

With $P_i=\sum_{g\in i}p_g^{(k)}-d_i^{(k)}$, choose one angle reference $r_c$ per component and solve

$$
\begin{aligned}\sum_{j\in c\setminus\{r_c\}}\hat b_{ij}\theta_j&=\frac{P_i}{S_B}\quad(i\in c\setminus\{r_c\}),\qquad\theta_{r_c}=0,\qquad\sum_{i\in c}P_i=0,\\ \hat b_{ii}&=\sum_{j:\,ij\notin\mathcal L^{(k)}}\frac{1}{\hat x_{ij}},\quad\hat b_{ij}=-\frac{1}{\hat x_{ij}}\ (ij\notin\mathcal L^{(k)}).\end{aligned} \tag{22}
$$

Off-diagonal entries for absent branches are zero. Reference choice fixes only angle freedom, not supply. Verify KCL at **all** nodes, including references, to $10^{-7}$ MW. Singular/non-finite solutions or failed KCL produce an explicit solver-failed state, never substitute zero angles. Branch flows and the overload set are

$$
F_{ij}=S_B\frac{\theta_i-\theta_j}{\hat x_{ij}},\qquad\mathcal O^{(k)}=\{ij\notin\mathcal L^{(k)}:\ |F_{ij}|>\rho_{rate}\,\mathrm{rateA}_{ij}+\delta\},\qquad\delta=10^{-7}\ \mathrm{MW}. \tag{23}
$$

The harness sets rating multiplier $\rho_{rate}=0.9,1.0,1.1$; these are rating changes, not equal percentage changes in transfer margin. The removal update is

$$
\mathcal L^{(k+1)}=\mathcal L^{(k)}\cup\mathcal T^{(k)},\qquad\mathcal T^{(k)}=\begin{cases}\mathcal O^{(k)},&\text{simultaneous},\\ \{\operatorname*{arg\,max}_{ij\in\mathcal O^{(k)}}|F_{ij}|/(\rho_{rate}\,\mathrm{rateA}_{ij})\},&\text{sequential}.\end{cases} \tag{24}
$$

Ties in sequential selection use the largest local branch index. Re-detect components and apply Eqs. (20)–(23) after each cut, carrying actual generation, served demand and outages forward without load restoration. At most 30 removal rounds are permitted, followed by a final solve. Only a balanced, solved state without overload is labelled converged. Solver failure and iteration-limit termination are separately flagged and have no valid terminal shed-load scalar. Rounds are topological stages, not seconds of relay action.

The coupling is one-way. S/H are not severity bounds: the amount and location of balancing response can create or relieve overload. Generator count or absence of branch trips alone does not establish N−1 security. The independent adequacy outlet uses DC-OPF with finite physical generator ceilings and constraints on all 46 branches (including transformer elements) to integrate incremental unserved energy over 0–8 h; it is not called inside the propagation loop. Optimization does not inherently preclude cascades—models may allow overload slack or include subsequent outage processes [30, 53]—but that alternative is not implemented here. Terminal cascade shedding in MW and adequacy UAE in MWh are distinct outputs. Physical generation is mapped by bus identity (G30–G39), including the finite 646 MW Bus 31 source; virtual load-serving variables are excluded from reported generator dispatch. Incremental UAE is $\int_0^{8\,\mathrm h}\max[0,L_\mathrm{shed}(t)-L_\mathrm{shed,0}]\,\mathrm dt$, with the no-fault baseline evaluated at the same load. Exchange includes both left and right limits at protection instants. Trapezoids cover continuous intervals only; the same-time protection jump has zero duration and contributes no spurious triangular area. Reference-operation energy integration uses the same convention. Fifteen static capacity/load cases are independently checked against a DC linear program parsed from the original MATPOWER file, separately from the S/H cascade verification.

### 2.7 Deterministic stress protocol and evidence acceptance

The current thermal matrix varies $\tau_{cond,des}$ over 30, 60, 90, 180, 300 and 600 s and $\tau_{tower}$ over 30, 300 and 1800 s. These 18 settings are deliberate stress tests, not inferred physical intervals or a probability sample. Each setting is evaluated for makeup interruption, full pump loss and a 6 K wet-bulb rise. Four corner settings receive a fourfold finer step for each fault, giving 54 primary trajectories and 12 refinements. Acceptance requires the same mechanism/censoring, trip-time difference at most 5 s and reference-operation energy difference below 0.1%.

To evaluate the lag-omission component of RQ3 directly, a separate 34-setting exact-zero ablation protocol sets subsets of the three endogenous plant lags—condenser thermal storage ($\tau_{cond,des}: 90\to 0$ s), tower-basin thermal lag ($\tau_{tower}: 300\to 0$ s) and circulating-pump hydraulic lag ($\tau_{pump}: 10\to 0$ s)—strictly to zero across S1a, S2, S3a and S4 (binary code $CTP\in\{0,1\}^3$, where $1$ denotes omission), plus two S4 exogenous-forcing controls (W_only with $\tau_{wb}: 900\to 0$ s only and CTPW with all four lags zeroed). Relay dwell ($3$ s), blowdown-isolation detection ($0.25$ h) and load-following ramp limits ($0.02\,\mathrm{min}^{-1}$) are protection or operational rules rather than physical storage lags and are held fixed. Under full pump loss (S2), settings with $C=1$ and $P=1$ (101 and 111) impose zero condenser storage and zero cooling-water conductance ($G=0$) under positive steam duty ($Q_{steam}>0$); Eq. (8) has no finite algebraic solution, so the solver raises `NoQuasiStaticEquilibrium` and records these two controls as physically inadmissible rather than assigning a relay-dwell substitute. The remaining 32 admissible settings are refined by successive fourfold time-step reductions ($\Delta t_L = \Delta t_0/4^L$, with $\Delta t_0=1.0$ s for S1a/S3a/S4 and $0.01$ s for S2) and twofold reporting refinements until adjacent layers preserve the trip mechanism/censoring status, agree within $5$ s ($0.05$ s for S2) in trip time, and differ by less than $0.1\%$ in reference-operation energy. All bias metrics compare the accepted fine-grid ablation against the accepted fine-grid 000 reference of the same fault.

For the main adequacy comparison, each makeup trajectory is exchanged on one-minute nodes plus events. Let $L(c)$ denote the minimum DC shed load at G33 ceiling $c$, with other settings fixed. Uniform physical generation costs make the optimization equivalent to minimizing total shedding. Relaxing $c$ expands the feasible set, so neighboring solved capacities give

$$
L(c_b)\le L(c)\le L(c_a),\qquad c_a\le c\le c_b.
\tag{25}
$$

Independent DC-LP upper-bound multipliers give additional weak-duality planes,

$$
L(c)\ge L(c_j)+\lambda_j(c-c_j),\qquad\lambda_j\le0.
\tag{26}
$$

Taking their maximum with the monotone lower bound tightens the enclosure without pretending a fitted interpolation is an exact OPF solution. Numerical feasibility/duality checks and a small explicit numerical allowance are retained. Positive-weight trapezoids propagate these bounds to the specified exchange integral. They are not continuous-time plant or model-form error bounds.

A first monotone-only attempt exceeded its preregistered 2 MWh precision threshold after 96 additional unique capacity points. Its failure is retained. The separately documented dual-certificate refinement changed the verification algorithm, not that threshold, the thermal matrix or the unique-point budget. It used 12 independent LP solves at already existing capacity positions. Halving exchange intervals is checked on the same piecewise-linear plant output using these bounds.

Historical OAT, Morris, Sobol and Monte Carlo outputs are not carried over as evidence for the revised thermal equations. The general methods [37–42] remain relevant, but neither a finite deterministic grid nor two diagnostic sample replays re-estimates a distribution, a confidence interval, mechanism frequency or global sensitivity ranking. External transient evidence is accepted for calibration only when the forcing, geometry, observations and errors support a reproducible comparison; the present evidence does not meet that standard.

## 3. Archetype and experiment setup

### 3.1 Reference design and parameter meaning

The reference wet-bulb is 20 °C. Design approach and terminal temperature difference determine the tower and condenser steady coefficients; they are not fitted to a failure time. Table 1 gives the 500 MWe reference closure. Equivalent G33 scales area and circulating flow by $652/500$; its reference effective condenser heat capacity is 5903.638 MJ/K. This is computed from the 90 s design anchor, not measured inventory. Healthy equilibria are identical across the stress-test time constants, illustrating their lack of steady-state identifiability.

**Table 1. Reference design closure of the 500 MWe archetype.** All values are reference-template quantities, not site measurements. Small rounding differences do not define a new calibration.

| Quantity | Reference value |
|---|---|
| Rating | 500 MW |
| Net design efficiency | 0.38 |
| Condenser duty | 750.526 MW |
| Circulating flow | 15.770000 m³/s |
| Water inlet / outlet / saturation | 25.550 / 36.970 / 40.470 °C |
| Backpressure | 7.562342 kPa |
| Approach / TTD | 5.55 / 3.50 K |
| Evaporation / blowdown / drift | 0.253098 / 0.083577 / 0.000789 m³/s |
| Normal makeup | 0.337464 m³/s |
| Basin area / normal-trip levels | 1600 m² / 3.50–1.00 m |
| Usable inventory | 4000 m³ |
| Diagnostic hold-up | 3.292536 h |

A complete current parameter subset, fixed assumptions and stress-test values are separated in Appendix A. Broad registry limits are not relabelled as actual propagation intervals. The tank geometry is explicit; usable inventory divided by design makeup gives a diagnostic 3.29 h, not a prescribed contingency trip time.

### 3.2 Synthetic network and fixed-capability cascade probes

The MATPOWER-aligned IEEE 39-bus network [32,49] contains 39 buses, 10 generators, 46 branches and 6254.23 MW base demand on 21 buses. Total capacity is 7367 MW; G33 and G34 ceilings are 652 and 508 MW. The other eight are equivalent generators, not a claim about their real fuel types. The original MATPOWER tap-based classification is 34 lines/12 transformers; pandapower 3.5.6 represents the same 46 electrical constraints as 35 line and 11 transformer elements. These software categories must not imply that a branch is omitted.

Lossless S/H initialization uses G33/G34 dispatch of 632/508 MW and an explicit Bus 31 adjustment to 634.23 MW, below its finite 646 MW maximum. It does not adopt the original loss-inclusive case dispatch as a feasible lossless state. Base-demand cascade probes evaluate five capability states under policies $S$ and $H$, simultaneous and sequential removal rules, and $0.9/1.0/1.1$ branch-rating multipliers: (i) healthy ceilings (652/508 MW), (ii) single-unit G33 outage (G33=0), (iii) recoupled S3a dual 50% pump-loss derating (G33=615.715 MW, G34=479.729 MW at 8 h under v0.7.2), (iv) recoupled detuned makeup-interruption first trip (`M6_detuned_at_first_trip`, where a $0.85$ basin-area multiplier on G34 causes G34 to trip at $t_1=4.273889$ h while G33 remains at $351.663$ MW), and (v) dual-zero collapse (G33=0, G34=0, reached synchronously at $5.047222$ h in `M6_synchronous_G3` or as the second trip $t_2=5.047222$ h in `M6_detuned_at_second_trip`).

Re-deriving the thermal inputs under v0.7.2 and verifying against a fourfold finer thermal step ($\Delta t=0.25$ s, $15$ s reporting, where $t_1$ and $t_2$ are unchanged and G33 capability at $t_1$ differs by $0.0061$ MW, altering shed load by at most $0.0061$ MW and branch removals/stages by zero) restores the full 8-row minimal gate, the 60-row rule/rating and decorrelation matrix, and 12 additional rating-sensitivity checks for the detuned intermediate snapshot. Every snapshot is evaluated as an independent static cascade from the intact pre-contingency network; the study does not claim a continuous time-domain cascade in which post-$t_1$ islanded topology is carried forward into $t_2$.

### 3.3 Horizons, resolution and comparisons

Reference G33 makeup cases are S1a (ride-down, detection/isolation), S1b (ride-down, maintained blowdown) and C1 (fixed initial steam duty, no SOP cap, isolation), with an 8 h horizon and 1 s maximum step. S2 complete pump-capacity loss uses a 1 h horizon and 0.1 s reference maximum step. S3a/S3b lose 50%/30% pump capacity and S4 raises wet-bulb by 6 K; all use 8 h, with no simultaneous inventory drain. Weather moves toward its new target with a 900 s lag. Blowdown isolation is detected at 0.25 h; vacuum dwell is 3 s; the reference tower and pump lags are 300 and 10 s.

In the stress matrix, low-capacity fast cases use $\Delta t_{S2}=\min(0.1,0.1\tau_{cond,des}/90)$ s; other primary steps remain 1 s. Reporting is at 60 s for slow paths and 1 s for S2, including explicit initial and event states. A shorter internal step and a finer output/clock are different numerical choices.

The adequacy headline uses G33, 1.15 times demand, 8 h and one-minute event-aware exchange, matching the thermal-stress enclosure study. The previously computed 15 min reference value is retained only as a convergence comparator. Immediate loss and trip-aligned flat capability use only full and zero ceilings, so their integrals can also be checked analytically. Reference-operation energy is $E_r=\int P_{avail}dt_h$; it is not grid-served energy and does not assume the grid actually dispatches the plant at the ceiling.

## 4. Results

### 4.1 Makeup interruption produces an inventory-controlled capability path

For reference G33, S1a reaches `pump_level` at 5.047222 h; S1b reaches the same label at 3.855000 h, 71.53 min earlier. C1 reaches 4.296389 h. All are distinct from the 3.29 h diagnostic design-loss hold-up. Isolation and reference-operation runback change the water-loss path rather than imposing an arbitrary failure time.

**Table 2. Current reference G33 outcomes.** Capacity is 652 MW. Reference-operation energy is the integral of the exported ceiling, not actual dispatched or served energy. S2 has a 1 h observation horizon; the other rows use 8 h. A dash is right censoring, not an infinite lifetime.

| Case | Trip/censoring | Event time | End capability (MW) | Reference-operation energy (MWh) |
|---|---|---|---|---|
| S1a | pump_level | 5.047222 h | 0.000 | 2738.433 |
| S1b | pump_level | 3.855000 h | 0.000 | 2098.716 |
| C1 | pump_level | 4.296389 h | 0.000 | 2796.950 |
| S2 | backpressure_protection | 97.4 s | 0.000 | 17.385 |
| S3a | no_trip_within_horizon | — | 615.715 | 4928.499 |
| S3b | no_trip_within_horizon | — | 640.023 | 5120.811 |
| S4 | no_trip_within_horizon | — | 640.237 | 5126.377 |

Ride-down retains capability longer than C1, but its reference-operation energy is 2738.433 MWh versus 2796.950 MWh for C1. A later trip therefore need not maximize the time integral of available power. Fig. 2 pairs the capability and inventory paths. The comparison reflects both SOP and steam-duty conventions; it is not an isolated estimate of the causal effect of an actual operator action.

![Figure 2: Inventory depletion and capability depend on the operating and blowdown conventions.](figures/fig02.png){width=170mm}

**Figure 2. Inventory depletion and capability depend on the operating and blowdown conventions.** a, G33 capability for S1a (ride-down with blowdown isolation at detection), S1b (ride-down with maintained blowdown) and C1 (initial steam duty held, no SOP cap, blowdown isolation). b, Matching basin-level paths; the 2 m SOP-start line applies to the ride-down rule, not to C1, and 1 m is the low-level trip setting. Reported trajectories start at the healthy state. The exact event time and saved left-limit capability are inserted before a same-time drop to zero; zero post-trip capability is continued to 8 h, but basin dynamics are not extrapolated past the event. Events occur at 5.047222, 3.855000 and 4.296389 h, respectively; the corresponding reference-operation capability integrals are 2738.433, 2098.716 and 2796.950 MWh (Table 2). These are deterministic scenarios, not replicates, and the integral is not actual grid-served energy. Curves use all retained reporting nodes from the accepted JSON outputs; no uncertainty band or smoothing fit is applied.

### 4.2 Flow and ambient faults separate mechanism from precise timing

Reference full pump loss reaches backpressure protection at 97.4 s with the 0.1 s maximum step. Reducing the step to 0.025 s changes the event by 0.075 s and reference-operation energy by 0.07579%, satisfying the declared criterion. The earlier 1 s fast-case discretization did not meet the 0.1% short-interval energy criterion and is not used as the accepted S2 reference.

This result is conditional on the finite-storage and pump-rundown assumptions. Removing both storage and all circulating flow while positive duty remains does not yield a finite quasi-static comparison state. No finite control trip time or dynamic/quasi-static multiplier is reported.

S3a/S3b and S4 remain online within 8 h and end at 615.715, 640.023 and 640.237 MW, respectively. Their mechanism is absence of a detected trip within that window, not proof of indefinite stability. The present model excludes reverse water flow, dynamic air ingress, shell-side compressibility and post-trip bypass/recovery; fast transient magnitudes require external evidence beyond these checks.

### 4.3 Thermal stress tests preserve labels but not fast durations

Fig. 3 compares fast- and slow-event sensitivity. Across all 18 combinations, makeup interruption remains level-protection controlled and complete pump loss remains backpressure controlled. S4 is right censored at 8 h. Table 3 separates those stable labels from their different quantitative sensitivities.

**Table 3. Deterministic thermal-parameter stress results.** Condenser anchors are 30/60/90/180/300/600 s and tower lags 30/300/1800 s. Ranges summarize these discrete settings, not a probability distribution or validated physical interval.

| Case | Combinations | Observed time range | Outcome |
|---|---|---|---|
| S1a | 18 | 4.906944–5.064722 h | pump level |
| S2 | 18 | 42.43–572.50 s | backpressure |
| S4 | 18 | No trip within 8 h | right censored |

For S1a at a 30 s tower lag, increasing the condenser anchor from 30 to 600 s advances the level trip from 5.064722 to 4.906944 h. In this surrogate, release of previously stored heat after runback sustains water-side transfer and affects water consumption. Storage therefore need not improve every resilience metric. This is a mechanism within the specified model, not a general empirical rule for condensers.

All 12 corner step refinements retain the same labels/censoring; the largest event-time difference is 0.25 s and the largest energy difference is 0.039013%. Representative condenser interval-energy residuals are below $10^{-6}$ MJ. An independent tower-lag intervention also changes downstream backpressure, verifying that the serial causal path is active. These checks establish numerical consistency; they do not make the uncalibrated dynamic parameters identifiable.

![Figure 3: Stable mechanism labels do not imply stable fast-event times.](figures/fig03.png){width=170mm}

**Figure 3. Stable mechanism labels do not imply stable fast-event times.** a, Backpressure-protection time after complete pump-capacity loss. b, Low-level trip time after makeup interruption. Both panels retain all 18 combinations of six condenser design anchors (30, 60, 90, 180, 300, 600 s) and three tower lags (30, 300, 1800 s), with a logarithmic horizontal axis and separate seconds/hours vertical units. Line segments connect discrete tested settings as visual guides; they do not certify unsampled settings. Some tower-lag curves overlap at this scale. The S2 range is 42.43–572.50 s; the S1a range is 4.906944–5.064722 h. The additional 18 wet-bulb cases are all right-censored at 8 h and remain in the source-data table, not represented as infinite trip times. Settings are deterministic stress tests, not physical parameter-confidence intervals; there are no statistical replicates or error bars.

### 4.4 Recoupled single- and dual-unit grid consequences depend on balancing response

With nominal ratings and simultaneous removal, both healthy policies serve base demand (6254.23 MW) without a branch cut. Under the recoupled S3a dual 50% pump-loss derating (G33=615.715 MW, G34=479.729 MW, a combined ceiling reduction of 44.556 MW below the 632/508 MW lossless dispatch), policy S sheds 44.556 MW proportionally without branch overloads, whereas policy H absorbs the 44.556 MW deficit through surviving-generator headroom with 0.0 MW shed and 0 branch removals across all six rule/rating combinations. When G33 is completely unavailable (632 MW lost), S sheds 632.0 MW without overload removals, and setting both wet-unit ceilings to zero sheds 1140.0 MW without overload removals at nominal ratings. Under the recoupled detuned makeup-interruption first-trip snapshot (t_1=4.273889 h, G34=0 MW, G33=351.663 MW, a combined dispatch deficit of 788.337 MW), policy S sheds 788.337 MW with zero branch cuts across all rules and ratings.

**Table 4. Recoupled v0.7.2 capability snapshots at base demand (nominal ratings, simultaneous removal).** Values combine the 8-row minimal gate with the nominal simultaneous `M6_detuned_at_first_trip` snapshot. Removal rounds are topological stages, not relay seconds; each row is an independent cascade evaluation from the intact network.

| Capability state (G33 / G34 ceiling, MW) | Policy | Branches removed | Rounds | Terminal shed MW | Islands |
|---|---|---|---|---|---|
| Healthy (652.0 / 508.0) | S | 0 | 0 | 0.0 | 1 |
| Healthy (652.0 / 508.0) | H | 0 | 0 | 0.0 | 1 |
| S3a dual derate (615.715 / 479.729) | S | 0 | 0 | 44.556 | 1 |
| S3a dual derate (615.715 / 479.729) | H | 0 | 0 | 0.0 | 1 |
| G33 zero (0.0 / 508.0) | S | 0 | 0 | 632.0 | 1 |
| G33 zero (0.0 / 508.0) | H | 12 | 3 | 1753.2 | 8 |
| Detuned 1st trip at 4.274 h (351.663 / 0.0) | S | 0 | 0 | 788.337 | 1 |
| Detuned 1st trip at 4.274 h (351.663 / 0.0) | H | 11 | 3 | 1909.537 | 8 |
| Both zero (0.0 / 0.0, sync or 2nd trip at 5.047 h) | S | 0 | 0 | 1140.0 | 1 |
| Both zero (0.0 / 0.0, sync or 2nd trip at 5.047 h) | H | 3 | 1 | 1087.230 | 3 |

Fig. 4 compares the response-dependent outcomes and all 48 non-healthy rule/rating settings across the four contingency states. Upward headroom redistribution (H) changes both the location and the magnitude of branch flows. Under nominal simultaneous removal, moving from S3a dual derate (44.556 MW deficit) to G33 zero (632.0 MW deficit), detuned first trip (788.337 MW deficit) and dual-zero collapse (1140.0 MW deficit) produces terminal H shedding of 0.0, 1753.2, 1909.537 and 1087.230 MW, with 0, 12, 11 and 3 removed branches, respectively. Thus the asymmetric intermediate snapshot (G34=0, G33=351.663 MW) triggers heavier H load shedding than either single-unit outage or complete dual-unit loss, because redistributing 788.337 MW across the remaining generators while G33 is capped at 351.663 MW drives the same three-stage islanding pattern as G33 loss (8 islands) with an additional 156.337 MW generation deficit inside the surviving islands.

**Table 5. Rule and rating sensitivity across all 48 non-healthy recoupled capability combinations.** Entries are removed branches [rounds], ordered by rating multiplier 1.0 / 0.9 / 1.1 (terminal shed MW in parentheses where rating changes alter shedding). All 12 healthy control combinations have 0 [0] cuts and 0.0 MW shed.

| Capability state | Policy | Simultaneous: 1.0 / 0.9 / 1.1 | Sequential: 1.0 / 0.9 / 1.1 |
|---|---|---|---|
| S3a dual derate (615.715 / 479.729) | S | 0 [0] / 0 [0] / 0 [0] (44.6 MW all) | 0 [0] / 0 [0] / 0 [0] (44.6 MW all) |
| S3a dual derate (615.715 / 479.729) | H | 0 [0] / 0 [0] / 0 [0] (0.0 MW all) | 0 [0] / 0 [0] / 0 [0] (0.0 MW all) |
| G33 zero (0.0 / 508.0) | S | 0 [0] / 0 [0] / 0 [0] (632.0 MW all) | 0 [0] / 0 [0] / 0 [0] (632.0 MW all) |
| G33 zero (0.0 / 508.0) | H | 12 [3] / 11 [3] / 11 [3] (1753.2 MW all) | 3 [3] / 3 [3] / 3 [3] (1155.7 MW all) |
| Detuned 1st trip (351.663 / 0.0 at 4.274 h) | S | 0 [0] / 0 [0] / 0 [0] (788.3 MW all) | 0 [0] / 0 [0] / 0 [0] (788.3 MW all) |
| Detuned 1st trip (351.663 / 0.0 at 4.274 h) | H | 11 [3] / 14 [5] / 12 [3] (1909.5 / 3154.9 / 1909.5 MW) | 3 [3] / 3 [3] / 3 [3] (1312.1 MW all) |
| Both zero (0.0 / 0.0, sync or 2nd trip) | S | 0 [0] / 2 [1] / 0 [0] (1140.0 MW all) | 0 [0] / 1 [1] / 0 [0] (1140.0 MW all) |
| Both zero (0.0 / 0.0, sync or 2nd trip) | H | 3 [1] / 3 [1] / 3 [1] (1087.2 MW all) | 3 [3] / 7 [7] / 3 [3] (1670.2 / 3843.7 / 1670.2 MW) |

Sequential removal (1 branch per stage) and rating multipliers further reverse the apparent severity ranking between intermediate and dual-zero states. Under sequential H removal at nominal ratings, G33 loss, detuned first trip and dual-zero loss all remove 3 branches in 3 rounds, but shed 1155.730, 1312.067 and 1670.168 MW, respectively; at 0.9 ratings, simultaneous H makes the detuned first trip most severe (14 branches in 5 rounds, 3154.947 MW shed, 9 islands), whereas sequential H makes dual-zero loss most severe (7 branches in 7 rounds, 3843.685 MW shed). Every one of the 80 evaluated cascade runs (8 gate, 60 matrix, 12 detuned rating checks) satisfies exact per-island KCL and capacity bounds with maximum nodal residual $1.07	imes 10^{-11}$ MW.

![Figure 4: Recoupled capability consequences depend on balancing and branch-removal rules.](figures/fig04.png){width=170mm}

**Figure 4. Recoupled capability consequences depend on balancing and branch-removal rules.** a, At nominal ratings with simultaneous removal, terminal shed load across the four v0.7.2 recoupled non-healthy states—S3a dual 50% pump-loss derating (615.715/479.729 MW), G33 zero (0/508 MW), detuned makeup-interruption first trip at 4.273889 h (351.663/0 MW) and both wet units zero (0/0 MW at 5.047222 h)—increases monotonically from 44.556 to 632.0, 788.337 and 1140.0 MW under S, but varies non-monotonically from 0.0 to 1753.2, 1909.537 and 1087.230 MW under H. Connecting segments pair ordered capability states, not a continuous time-domain cascade. b, All 48 non-healthy combinations of capability state, S/H policy, simultaneous/sequential removal and rating multiplier (1.0, 0.9, 1.1); cells report removed branches [topological removal rounds]. Pale row bands group states and do not encode magnitude. Both panels use base demand (6254.23 MW); the 68-row source file (`fig04_all68_recoupled_electrical_probes.csv`) retains all healthy controls and duplicated baseline rows.

### 4.5 The adequacy contrast persists across the tested thermal settings

**Table 6. Main G33 adequacy comparison.** Demand is 1.15 times case load, horizon 8 h. Incremental UAE subtracts the healthy shed-load baseline at the same demand. Reference results use one-minute event-aware integration; the aligned flat trajectory has only full/zero states and is also checked analytically.

| Encoding | Incremental UAE (MWh) | Trip time (h) |
|---|---|---|
| Immediate loss | 4634.437 | 0 |
| Flat full capability until mechanism trip | 1710.558 | 5.047222 |
| Reference mechanism, 1 min | 2170.680 | 5.047222 |

Fig. 5 shows the matched input paths and incremental energy consequence. The one-minute reference mechanism value is 2170.680 MWh, 53.161947% below immediate loss. The 15 min comparator is 2170.255 MWh, or −0.019600% relative to the one-minute value; the text consistently uses the finer value rather than mixing percentage denominators or exchange resolutions.

![Figure 5: Outage encoding changes incremental unserved energy in the matched adequacy comparison.](figures/fig05.png){width=170mm}

**Figure 5. Outage encoding changes incremental unserved energy in the matched adequacy comparison.** a, The same reference mechanism is compared with immediate loss and with 652 MW held until the mechanism trip at 5.047222 h. All trip jumps retain their left and right limits. b, Incremental UAE is 4634.437 MWh for immediate loss, 1710.558 MWh for the trip-aligned control and 2170.680 MWh for the mechanism path, at demand multiplier 1.15 and an 8 h horizon. Continuous intervals use one-minute event-aware exchange; the full/zero controls are also checked analytically. The zero-duration jump is not integrated as a triangular area. The reference mechanism is 53.161947% below immediate loss. The path differences 2923.879171 and −460.122233 MWh are an algebraic reference-path decomposition, not unique causal contributions. UAE subtracts the matched healthy shed-load baseline; this figure addresses encoding within RQ3, not a validated omission-of-all-lags bias. Each bar is one deterministic calculation, with no confidence interval.

For the defined immediate → trip-aligned → mechanism path, the differences satisfy

$$
U_{instant}-U_{mech}=(U_{instant}-U_{aligned})+(U_{aligned}-U_{mech})
=2923.879171+(-460.122233)=2463.756938\quad\mathrm{MWh}.
\tag{27}
$$

The aligned trajectory has at least as much pre-trip capability as the mechanism trajectory, so monotonicity already constrains its UAE ordering and the negative shape term. This reference-path identity is not unique causal attribution, and no dominance percentage is treated as an independently estimated physical effect.

Fig. 6 retains every tested parameter pair. Across the 18 stress settings, dual/monotone bounds enclose the specified one-minute mechanism UAE between 2164.016 and 2223.358 MWh. Relative to immediate loss, the outer reduction envelope is 52.025–53.306%; the largest individual enclosure width is 1.382977 MWh. The reference 90/300 s point contains the independently evaluated one-minute value. Halving exchange intervals on the same piecewise-linear output yields a conservative relative-difference bound at most 0.063746% across all 18 paths, without another grid solve.

The electrical evidence uses 866 previously verified snapshots and 96 additional unique capacity positions. Twelve independent LP solves at existing positions supply the dual certificates; 785 other cached single-G33 points are checked against the resulting lower bound. The maximum certificate duality gap is approximately $4.61\times10^{-12}$ MW. None of these counts is a number of simulated cascades or experimental replicates. The original monotone-only precision failure remains in the evidence package.

To test whether this adequacy ordering persists across broader black-box encodings, demand levels and generator locations under the current v0.7.2 closure, Table 7 migrates the six-encoding benchmark set, the five-load expansion ($1.00$–$1.20\times$ base demand) and the mapped G34 unit ($508$ MW at Bus 34) at the 15 min event-aware exchange resolution (requiring 162 additional verified DC-OPF snapshots beyond the existing 962-point cache, all converged with zero branch overloads and nodal residuals below $10^{-5}$ MW). Across all five demand levels on G33, mechanistic ride-down reduces incremental UAE by $36.13\%$ (at $1.15\times$ demand, where the 3.293 h diagnostic hold-up proxy yields $2727.056$ MWh and the linear-to-minimum proxy yields $3261.018$ MWh) to $63.09\%$ (at $1.00\times$ demand, where ride-down capability remains above the zero-shedding threshold until the 5.047222 h trip and therefore matches the trip-aligned control at $361.042$ MWh against $978.175$ MWh for immediate loss). On G34 at $1.15\times$ demand, immediate loss, diagnostic hold-up, simplified level-band ($4.069167$ h backpressure trip), mechanistic ride-down, mechanistic hold-load and trip-aligned control yield $3560.317$, $2095.008$, $1887.063$, $1665.548$, $1650.919$ and $1314.103$ MWh, respectively—preserving the exact $-53.219\%$ ride-down reduction relative to immediate loss and the $-63.090\%$ trip-aligned reduction observed on G33.

**Table 7. Migrated v0.7.2 adequacy comparisons across six outage encodings, five demand levels (1.00–1.20×) and mapped units G33/G34 (15 min event-aware exchange, 8 h horizon).** Numbers in parentheses in Panel B denote percentage change relative to immediate loss at the same demand multiplier.

| Panel A: Six encodings & aligned control at $1.15\times$ demand | Trip mechanism | Trip time (h) | G33 $E_r$ (MWh) | G33 inc. UAE (MWh) | G34 $E_r$ (MWh) | G34 inc. UAE (MWh) |
|---|---|---|---|---|---|---|
| Immediate loss (`instant_trip`) | Assumed instant trip | 0.000000 | 0.000 | 4634.437 | 0.000 | 3560.317 |
| Linear ramp to min then trip (`linear_to_min_then_trip`) | Assumed linear derate | 3.292536 | 1502.713 | 3261.018 ($-29.64\%$) | 1170.826 | 2503.548 ($-29.68\%$) |
| Diagnostic hold-up (`fixed_holdup_trip`) | Assumed fixed hold-up | 3.292536 | 2146.733 | 2727.056 ($-41.16\%$) | 1672.608 | 2095.008 ($-41.16\%$) |
| Simplified level-band (`simplified_level_band`) | Backpressure protection | 4.069167 | 2431.245 | 2456.180 ($-47.00\%$) | 1894.283 | 1887.063 ($-47.00\%$) |
| Mechanistic ride-down (`mechanistic_ride_down`, 15 min) | Pump low-level trip | 5.047222 | 2738.433 | 2170.255 ($-53.17\%$) | 2133.626 | 1665.548 ($-53.22\%$) |
| Mechanistic hold-load (`mechanistic_hold_load`, C1) | Pump low-level trip | 4.296389 | 2796.950 | 2148.940 ($-53.63\%$) | 2179.219 | 1650.919 ($-53.63\%$) |
| Trip-aligned flat capability (`delayed_instant_trip`) | Aligned control | 5.047222 | 3290.789 | 1710.558 ($-63.09\%$) | 2563.989 | 1314.103 ($-63.09\%$) |
| **Panel B: G33 five-load expansion (0–8 h inc. UAE, MWh)** | **Baseline shed (MW)** | **Immediate loss (0 h)** | **Fixed hold-up (3.293 h)** | **Mech. ride-down (5.047 h)** | **Aligned flat (5.047 h)** | **Ride-down vs. hold-up** |
| Load scale $1.00\times$ ($6254.23$ MW) | 0.000 | 978.175 | 575.590 ($-41.16\%$) | 361.042 ($-63.09\%$) | 361.042 ($-63.09\%$) | $-214.549$ MWh ($-37.27\%$) |
| Load scale $1.05\times$ ($6566.94$ MW) | 0.000 | 2627.722 | 1546.238 ($-41.16\%$) | 1047.911 ($-60.12\%$) | 969.885 ($-63.09\%$) | $-498.327$ MWh ($-32.23\%$) |
| Load scale $1.10\times$ ($6879.65$ MW) | 56.609 | 4374.981 | 2574.383 ($-41.16\%$) | 2054.064 ($-53.05\%$) | 1614.793 ($-63.09\%$) | $-520.319$ MWh ($-20.21\%$) |
| Load scale $1.15\times$ ($7192.36$ MW) | 342.199 | 4634.437 | 2727.056 ($-41.16\%$) | 2170.255 ($-53.17\%$) | 1710.558 ($-63.09\%$) | $-556.801$ MWh ($-20.42\%$) |
| Load scale $1.20\times$ ($7505.08$ MW) | 649.190 | 4843.525 | 2850.090 ($-41.16\%$) | 2296.982 ($-52.58\%$) | 1787.732 ($-63.09\%$) | $-553.107$ MWh ($-19.41\%$) |

To address the second part of RQ3—how omitting second-to-minute plant lags biases the studied outcomes—Table 8 summarizes the 34-setting fault-specific exact-zero lag-ablation experiment (70 trajectory solves in total). An initial four-layer refinement cap ($\Delta t\ge 1/64$ s) passed 31 of 32 admissible settings and flagged S3a_111 as a precision failure (3.091% adjacent-layer energy difference); that first-pass failure record is retained, and extending the maximum refinement depth to seven layers without relaxing any threshold resolves S3a_111 at $\Delta t=1/4096$ s (0.0488% energy difference).

**Table 8. Fault-specific exact-zero lag-omission biases across the four contingency classes.** Binary code $CTP$ indicates whether condenser storage ($C: 90\to 0$ s), tower-basin lag ($T: 300\to 0$ s) and pump hydraulic lag ($P: 10\to 0$ s) are omitted ($1$) or retained ($0$); W_only and CTPW additionally omit the 900 s wet-bulb forcing lag in S4. Biases are defined as $(X_{CTP}-X_{000})$ at the accepted fine resolution of each fault. For S1a, one-minute event-aware incremental UAE biases use the same 797 cached single-G33 DC snapshots and 12 LP-dual certificates (0 new DC solves, maximum enclosure width $1.231816$ MWh).

| Fault & metric | Full-lag reference (000) | Condenser storage omitted (100) | Tower lag omitted (010) | Pump lag omitted (001) | Joint plant-lag omission (111) | Admissibility & dominant bias mechanism |
|---|---|---|---|---|---|---|
| **S1a** makeup interrupt (dt=0.25 s) | Trip 18170.0 s (5.047222 h), $E_r=2738.446$ MWh, UAE [2170.668, 2170.688] MWh | +93.0 s (+0.512%), +10.753 MWh (+0.393%), UAE bias [-9.911, -9.831] MWh | +0.5 s (+0.003%), +0.017 MWh (+0.0006%), UAE bias [-0.040, +1.212] MWh (unresolved sign) | 0.0 s (0.000%), -0.001 MWh (-0.0001%), UAE bias [-0.019, +0.026] MWh (unresolved sign) | +94.0 s (+0.517%), +10.867 MWh (+0.397%), UAE bias [-10.016, -9.893] MWh | All 8 admissible (`pump_level`). Algebraic condenser releases less heat to water during ride-down, slightly slowing evaporation. |
| **S2** full pump loss (dt=0.0025 s; 110 at 0.000625 s) | Trip 97.315 s, $E_r=17.370$ MWh (backpressure) | -87.253 s (-89.660%), -15.551 MWh (-89.526%), trip at 10.063 s | +1.495 s (+1.536%), +0.268 MWh (+1.544%), trip at 98.810 s | -11.618 s (-11.938%), -2.071 MWh (-11.922%), trip at 85.698 s (011 identical) | **Inadmissible** (101 & 111: `NoQuasiStaticEquilibrium` at $C=0, G=0, Q_{steam}>0$) | 110 trips at 9.768 s (-89.962%). Omitting $\tau_{cond}$ alone collapses survival time almost tenfold; omitting both $\tau_{cond}$ and $\tau_{pump}$ is undefined. |
| **S3a** 50% pump loss (dt=0.25 s; 111 at 1/4096 s) | No trip in 8 h (max pb=12.964 kPa), $E_r=4928.493$ MWh, end 615.715 MW | No trip (max pb=14.438 kPa), -1.843 MWh (-0.037%) | No trip (max pb=13.014 kPa), -0.228 MWh (-0.005%) | No trip (max pb=13.016 kPa), -0.102 MWh (-0.002%) | **Regime flip:** backpressure trip at 3.000488 s ($3\text{ s}+2\Delta t$), -4927.950 MWh (-99.989%) | Non-additive interaction: 101 (14.801 kPa) and 110 (14.840 kPa) stay below 15 kPa, but 111 jumps to 15.375 kPa at step 2 before ramp relief. |
| **S4** +6 K wet-bulb rise (dt=0.25 s) | No trip in 8 h, $E_r=5126.377$ MWh, end 640.237 MW | No trip, -0.383 MWh (-0.007%; 101 identical) | No trip, -0.980 MWh (-0.019%; 011 identical) | No trip, 0.000 MWh (0.000%) | No trip, -1.360 MWh (-0.027%; 110 identical) | All 10 admissible. W_only (-3.067 MWh, -0.060%) and CTPW (-4.386 MWh, -0.086%) show exogenous weather-ramp removal exceeds endogenous lag bias. |

The ablation matrix demonstrates that lag-omission bias is strongly fault-dependent and cannot be summarized by a single quasi-static multiplier. First, in S2 complete pump outage, joint omission of condenser storage and pump coastdown (101, 111) is mathematically undefined under positive steam load, whereas conditional omission of condenser storage while retaining the 10 s pump lag (100, 110) is admissible and reduces trip time from 97.315 s to 10.063 s and 9.768 s (-89.660% and -89.962%). Omitting the 10 s pump lag while retaining condenser storage (001, 011) reduces trip time to 85.698 s (-11.938%), and once flow drops to zero at $t=0^+$, tower-lag removal has no further effect (011 equals 001). Second, in S3a partial pump outage, lag omission exhibits a severe non-additive threshold flip: removing any one or two lags preserves 8 h ride-through (4926.569–4928.391 MWh) because either the 10 s flow decay, the 90 s condenser thermal buffer or the 300 s tower-basin lag keeps peak backpressure below 14.841 kPa until the $0.02\,\mathrm{min}^{-1}$ load-following ramp reduces steam duty; removing all three lags simultaneously (111) causes the coupled algebraic tower–condenser state to reach 15.375 kPa on the second time step ($t=2\Delta t$) and trip at $3\text{ s}+2\Delta t=3.000488$ s (0.543 MWh, -99.989%). Third, in S1a makeup interruption, hour-scale basin depletion dominates, but omitting condenser storage (100, 101, 110, 111) delays the low-level trip by 93.0–94.0 s (+0.512% to +0.517%) and lowers one-minute incremental UAE by 9.826–10.018 MWh (-0.453% to -0.461% of the fine-grid 000 enclosure [2170.668, 2170.688] MWh), whereas omitting tower or pump lags alone produces sub-second shifts whose UAE bias intervals ([-0.040, +1.212] and [-0.019, +0.026] MWh) straddle zero and are therefore reported as unresolved in sign at the current enclosure width. Note that the fine-grid S1a 000 reference (dt=0.25 s, report=30 s) is paired exclusively with the ablation controls and does not replace the dt=1.0 s, report=60 s headline UAE (2170.680 MWh) in Table 6.

![Figure 6: The adequacy contrast persists across the tested thermal settings.](figures/fig06.png){width=170mm}

**Figure 6. The adequacy contrast persists across the tested thermal settings.** Each horizontal segment is the verified lower/upper numerical enclosure of UAE reduction for one of all 18 condenser-anchor/tower-lag pairs, relative to the same immediate-loss UAE of 4634.436991647404 MWh. End caps mark bounds, not statistical error bars; no central estimate is added. The dashed line is the independently evaluated 90/300 s mechanism reference (53.161947%). The outer reduction envelope is 52.025–53.306%; the largest individual UAE enclosure width is 1.382977 MWh. Bounds apply to the specified one-minute event-aware exchange integral, not model-form error, continuous-time physical error, confidence intervals or all intermediate parameter values. The original monotone-only precision failure is retained; 12 independent LP certificate solves at existing positions tighten the bounds without exceeding the 96 additional unique-capacity-point budget. These numerical checks support, but do not replace, the original lag-omission question.

## 5. Discussion

### 5.1 Inventory control is the supported primary mechanism

The principal finding is the distinction between inventory-limited capability loss, rapid flow/pressure stress and no-trip derating within a finite horizon. In the studied makeup scenario, explicit volume and heat-based water loss create an hour-scale path that differs from immediate loss. Operator/blowdown conventions affect both its terminal event and the integral of available power. The observed UAE contrast remains under the tested thermal coefficients, so it is not confined to the original 90 s anchor.

The model does not introduce a new universally validated heat-transfer correlation. It makes the choices connecting known engineering maps, finite storage, control rules and grid ceilings inspectable. The evidence supports retaining that auditable pathway as the paper's main contribution while avoiding a site-specific interpretation of the reference geometry, time constants or protection settings.

### 5.2 Fast durations and external validation require stronger data

The pump-loss range is broad despite stable protection labels. This is not an uncertainty distribution: it is a deterministic demonstration that a precise fast trip time cannot be justified by a healthy steady-state match. A synchronized transient with known steam duty and cooling-flow evolution is needed to separate effective storage from forcing and sensor response.

The HPR1000 publication [47] was read through its public model, verification, assumptions and tables. Its pressure events are Apros predictions associated with pump-coastdown verification, turbine/bypass sequences and possible reverse water flow, not measurements of the present coal prototype. Eight public tabulated event values are recorded as simulation references only. Seguin et al. [56] report a more directly relevant loss/restart-cooling experiment, but the accessible material does not provide the complete input–geometry–response package used here. Its associated thesis catalogue [59] states confidentiality until March 2029; no restricted manuscript was obtained or bypassed. Alcock et al. [57] provide another reduced-pressure experimental route, but only abstract-level information was obtained in this review phase. No quantitative reproduction or transient calibration is claimed.

The reference G33 capacity corresponds dimensionally to about 1416.603 m³ of water, or 68.887 s of design flow. This equivalent-water diagnostic is not a measured tube inventory and must not be justified using basin volume. Independent geometry and a suitable transient could constrain a richer wall/water/steam storage model; until then the effective capacity is a transparent conditional anchor.

### 5.3 Capability, dispatch and grid-response assumptions must remain separate

Available power is a ceiling on grid injection, not a command. The current steam-duty path is based on the reference plant operation and does not receive feedback from actual network redispatch. The adequacy contrast therefore answers an open-loop screening question, not the outcome of a jointly optimized turbine/cooling/network controller.

S/H propagation and optimized DC adequacy answer different questions. The former inherits dispatch, served demand and cuts within each cascade and applies non-optimized response rules; the latter evaluates separate constrained snapshots and an incremental time integral. Static headroom is not calibrated reserve delivery, and no overload removals do not imply no unmet demand. Nor is a policy with more upward response guaranteed to cause fewer overloads [50–55].

Common cooling supplies or auxiliary power can motivate correlated capability states, and recoupling the S3a dual-derate and detuned makeup-interruption states under v0.7.2 shows why intermediate asymmetric capability ceilings cannot be interpolated from single- and dual-zero endpoints: at $t_1=4.273889$ h (G34=0, G33=351.663 MW), upward headroom redistribution (H) sheds 1909.537 MW under simultaneous removal (3154.947 MW at 0.9 ratings), whereas mild partial derating (S3a) is completely absorbed by H (0.0 MW shed vs 44.556 MW under S). Even so, each snapshot is evaluated from the intact pre-contingency network; a true chronological cascade study would require carrying post-$t_1$ islanded topology, generator thermal states and explicit dispatch/restoration timing forward into $t_2$.

### 5.4 Scope, superseded statistics and priority extensions

The tower is a simplified design-anchored surrogate without full humidity treatment [19–22]. The condenser uses one effective state, a fixed air partial pressure and an empirical saturation map rather than explicit vapour mass/volume dynamics. Flow is nonnegative and exponentially smoothed; reverse-flow transients are outside its domain. Basin depletion is not combined with pump/ambient faults, chemistry is not dynamically integrated after blowdown isolation, and the full tower/piping energy inventory is unresolved. Local reference-operation heat and electrical-power conventions are not a full steam-cycle balance.

The cascade outlet omits voltage/reactive power, frequency, calibrated reserve ramps, relay time and optimized remedial/restoration action. Its reactance-only transformer representation differs from the adequacy outlet's tap-aware case model. Rating multipliers are sensitivity settings, not identified emergency/seasonal ratings. No AC computation is part of this study.

Historical MC/Sobol statistics cannot be used after changing the dynamics. As a diagnostic, two previously identified backpressure samples were replayed: sample 40 changes from 2.963889 to 2.978333 h and sample 282 from a saved 10 s to 2.100000 h under the revised initialization/closure. Their new initial pressures are below their respective thresholds. These two replays do not preserve or re-estimate the former mechanism frequency, trip-time quantiles or sensitivity ranking. In particular, a spurious initially over-threshold trajectory is not evidence for an early fault-induced tail event. A new probabilistic study would first specify initial-state eligibility and establish sample-relevant integration accuracy; no such full campaign is claimed here [37–42].

The original RQ3 is now answered across both of its components—outage encoding (Tables 6–7, Fig. 5) and omission of second-to-minute plant lags (Table 8)—while keeping parameter robustness (Fig. 6) in its proper supporting role. Three methodological lessons emerge from the 34-setting ablation design. First, a lag-omission control must be checked for physical admissibility before any numerical ratio is formed: in complete pump loss, setting both condenser storage and pump coastdown to zero (S2_101, S2_111) eliminates heat removal under positive steam input and has no finite quasi-static state, whereas conditional single-channel ablations (S2_100, S2_001) are well-posed and quantify the separate buffering roles of condenser heat capacity (-89.660% trip-time bias when omitted) and pump coastdown (-11.938%). Second, lag-omission effects are non-additive near protection thresholds: in S3a, every single- and two-lag ablation rides through 8 h with less than 0.04% energy change, yet joint omission of all three plant lags (S3a_111) crosses the 15 kPa vacuum threshold before operator/governor ramping can reduce steam rejection, collapsing delivered energy by 99.989% and requiring $\Delta t=1/4096$ s to resolve the $3\text{ s}+2\Delta t$ serial-splitting transient within 0.1%. Third, in inventory-dominated makeup faults (S1a) and slow ambient rises (S4), omitting endogenous thermal/hydraulic lags shifts 8 h energy by less than 0.40% (+93 to +94 s trip shift and -9.83 to -10.02 MWh UAE bias in S1a), and in S4 the historical `quasi_static` flag conflated endogenous plant lags (-1.360 MWh for 111) with removal of the 900 s exogenous weather ramp (-3.067 MWh for W_only, -4.386 MWh for CTPW).

Priority work is an accessible independent transient benchmark and parameter-identification protocol, followed by any justified expansion of thermal scenarios, uncertainty or networks. The present finite grid supports its stated comparisons, not every continuously varying parameter or operational situation. Publishing readiness still requires author information, final page-layout proofing and any additional evidence needed to support broader claims.

## 6. Conclusions

A serial finite-storage cold-end surrogate preserves the existing steady heat-transfer map while distinguishing steam input, water-side transfer and retained heat. Together with explicit basin geometry and heat-based water losses, it produces inventory-controlled makeup-interruption paths rather than prescribing a hold-up trip. The reference G33 ride-down trip is 5.047 h with blowdown isolation and 3.855 h with maintained blowdown. A longer operating window does not necessarily increase the integral of available power.

Thermal-parameter stress tests preserve the three studied outcome classes but expose unequal timing robustness. Makeup trips span 4.907–5.065 h; full pump-loss trips span 42.43–572.50 s; wet-bulb probes remain online within 8 h. Fast durations remain uncalibrated. A zero-storage, zero-flow control with positive heat has no finite equilibrium and cannot define a meaningful trip-time multiplier.

At 1.15 times demand in the defined IEEE 39-bus adequacy problem, reference mechanism UAE is 2170.680 MWh against 4634.437 MWh for immediate loss. The 18-setting reduction envelope is 52.025–53.306%, with numerically verified snapshot enclosures, not empirical confidence bounds. The trip-aligned difference identity does not identify unique causal contributions.

Recoupled state-carrying cascade snapshots across mild dual derating (S3a), single-unit loss, detuned first-trip asymmetry (4.274 h) and dual-zero collapse (5.047 h) demonstrate that finite, conserving response assumptions and removal rules govern branch removals and terminal shedding; under H, the detuned intermediate state (1909.5 MW nominal simultaneous shed) is more severe than complete dual-unit loss (1087.2 MW), whereas S3a dual derating is fully absorbed (0.0 MW shed). Together these results address the original fault-pathway question (RQ1), the response-dependent single/dual-loss comparison (RQ2), and both the outage-encoding and lag-omission components of RQ3: black-box immediate-loss encoding overstates incremental UAE by 53.16% (robust across 52.025–53.306%), while exact-zero lag ablation shows that omitting short plant lags is undefined for joint zero-flow/zero-storage pump loss (S2_101, S2_111), compresses conditional S2 survival by 11.94–89.96%, triggers a spurious 3.0005 s backpressure trip under joint omission in 50% pump loss (S3a_111, -99.989% energy), and shifts makeup-interruption trip time by only +93 to +94 s (-9.83 to -10.02 MWh UAE). These findings support mechanism-aware and response-explicit screening. They do not validate plant-specific protection times, chronological blackout forecasts or a universal numerical effect size.

## Declarations

**Data and code availability.** Current candidate core is version 0.7.2.dev0. Current thermal evidence is under `manuscript/revisions/thermal_v072/outputs`; the deterministic matrix, enclosure certificates, original precision failure and external-source registry are under `manuscript/revisions/thermal_validation_v072`; the 34-setting fault-specific exact-zero lag-ablation gate, 70 compressed trajectories, first-pass precision failure record and S1a UAE ablation enclosures are under `manuscript/revisions/lag_ablation_v072`. The recoupled v0.7.2 electrical cascade gate (8 rows), full rule/rating and decorrelation matrix (60 rows), detuned first-trip rating sensitivity (12 rows), and migrated v0.7.2 six-encoding, five-load and G34 adequacy tables (`opf_six_encodings_v072.csv`, `opf_encoding_expand_v072.csv`, `OPF_EXPAND_V072_GATE.json`) are archived under `manuscript/revisions/rq2_recoupled_v072/outputs`, while the historical `code/examples/dc_minimal_validation_v07.csv` and `m2_cascade_robustness.csv` remain untouched. Old outputs elsewhere in `code/examples` are not blanket-declared current. No project artifact used here contains measured observations from a power plant. The eight external HPR1000 table values are explicitly published simulation references, not project calibration data.

**Reproducibility and verification.** The thermal/core standard-library implementation is separate from optional pandapower 3.5.6 DC adequacy and SciPy LP verification. No external release tag is asserted. Numerical/source checks, manuscript claim and equation audits, and the manuscript-to-Word conversion record accompany this candidate. Four unchanged tests require the author-reserved `RESEARCH_FRAMEWORK.md`; this document remains absent and those failures are not concealed. The historical v0.7.1 manuscript, images, invariants and delivery ZIP remain unchanged.

**Figure status.** Six newly rendered, source-linked figures accompany this illustrated candidate. A figure-source manifest, editable PDF/SVG files, PNG/TIFF previews and automated/visual QA records are supplied separately. No historical scientific image is reused. Structural and figure QA do not establish external physical validity or replace final manuscript page-layout proofing.

**CRediT authorship contribution statement.** **[Author 1]:** Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Data curation, Visualization, Writing – original draft, Writing – review & editing. **[Author 2]:** Methodology, Validation, Investigation, Writing – review & editing, Supervision. **[Author 3]:** Conceptualization, Resources, Writing – review & editing, Project administration, Funding acquisition. *(Placeholder roles for author verification prior to submission; no authorship is assumed by the research assistant.)*

**Declaration of competing interest.** The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper. *(To be confirmed by the authors at submission.)*

**Funding.** This work was supported by `[Funding Agency Name, Grant/Award Number(s)]`. *(To be completed by the authors prior to submission.)*

**Reference status.** All 59 numbered references include full article/standard titles, standardized author names and journal abbreviations, volume/page or article numbers, and verified DOIs or URLs while preserving the exact in-text citation numbering [1–59]. Source access levels for the transient benchmark review ([47,56–59]) are stated explicitly; retaining a historical citation does not claim that all historical full texts were re-reviewed in this revision.

## References

1. Wang Y, Zhou Z, Betrie G, Zhang K, Yan E. Power generation-cooling water Nexus: Impacts of cooling water shortage on power system operation - a simulation case study in Illinois, U.S. Appl Energy 2025;377:124440. https://doi.org/10.1016/j.apenergy.2024.124440
2. Byers EA, Coxon G, Freer J, Hall JW. Drought and climate change impacts on cooling water shortages and electricity prices in Great Britain. Nat Commun 2020;11:2239. https://doi.org/10.1038/s41467-020-16012-2
3. van Vliet MTH, Yearsley JR, Ludwig F, Vögele S, Lettenmaier DP, Kabat P. Vulnerability of US and European electricity supply to climate change. Nat Clim Chang 2012;2:676–81. https://doi.org/10.1038/nclimate1546
4. DeNooyer TA, Peschel JM, Zhang Z, Stillwell AS. Integrating water resources and power generation: The energy–water nexus in Illinois. Appl Energy 2016;162:363–71. https://doi.org/10.1016/j.apenergy.2015.10.071
5. Shuai H, Li F, Zhu J, Tingen WJ II, Mukherjee S. Modeling the impact of extreme summer drought on conventional and renewable generation capacity: Methods and a case study on the Eastern U.S. power system. Appl Energy 2024;363:122977. https://doi.org/10.1016/j.apenergy.2024.122977
6. Macknick J, Newmark R, Heath G, Hallett KC. Operational water consumption and withdrawal factors for electricity generating technologies: a review of existing literature. Environ Res Lett 2012;7:045802. https://doi.org/10.1088/1748-9326/7/4/045802
7. Meldrum J, Nettles-Anderson S, Heath G, Macknick J. Life cycle water use for electricity generation: a review and harmonization of literature estimates. Environ Res Lett 2013;8:015031. https://doi.org/10.1088/1748-9326/8/1/015031
8. van Vliet MTH, Wiberg D, Leduc S, Riahi K. Power-generation system vulnerability and adaptation to changes in climate and water resources. Nat Clim Chang 2016;6:375–80. https://doi.org/10.1038/nclimate2903
9. Miara A, Macknick JE, Vörösmarty CJ, Tidwell VC, Newmark R, Fekete B. Climate and water resource change impacts and adaptation potential for US power supply. Nat Clim Chang 2017;7:793–8. https://doi.org/10.1038/nclimate3417
10. Peer RAM, Sanders KT. Characterizing cooling water source and usage patterns across US thermoelectric power plants: a comprehensive assessment of self-reported cooling water data. Environ Res Lett 2016;11:124030. https://doi.org/10.1088/1748-9326/aa51d8
11. Förster H, Lilliestam J. Modeling thermoelectric power generation in view of climate change. Reg Environ Chang 2010;10:327–38. https://doi.org/10.1007/s10113-009-0104-x
12. van Vliet MTH, Vögele S, Rübbelke D. Water constraints on European power supply under climate change: impacts on electricity prices. Environ Res Lett 2013;8:035010. https://doi.org/10.1088/1748-9326/8/3/035010
13. Liu L, Hejazi M, Li H, Forman B, Zhang X. Vulnerability of US thermoelectric power generation to climate change when incorporating state-level environmental regulations. Nat Energy 2017;2:17133. https://doi.org/10.1038/nenergy.2017.109
14. Bartos MD, Chester MV. Impacts of climate change on electric power supply in the Western United States. Nat Clim Chang 2015;5:748–52. https://doi.org/10.1038/nclimate2648
15. Burillo D, Chester MV, Ruddell B, Johnson N. Electricity demand planning forecasts should consider climate non-stationarity to maintain reserve margins during heat waves. Appl Energy 2017;206:267–77. https://doi.org/10.1016/j.apenergy.2017.08.141
16. Pan S-Y, Snyder SW, Packman AI, Lin YJ, Chiang P-C. Cooling water use in thermoelectric power generation and its associated challenges for addressing water-energy nexus. Water-Energy Nexus 2018;1:26–41. https://doi.org/10.1016/j.wen.2018.04.002
17. Stillwell AS, King CW, Webber ME. Desalination and Long-Haul Water Transfer as a Water Supply for Dallas, Texas: A Case Study of the Energy-Water Nexus in Texas. Tex Water J 2010;1:33–41. https://doi.org/10.21423/twj.v1i1.1042
18. Heat Exchange Institute (HEI). Standards for Steam Surface Condensers. 12th ed. Cleveland, OH: Heat Exchange Institute; 2017.
19. Jaber H, Webb RL. Design of Cooling Towers by the Effectiveness-NTU Method. J Heat Transfer 1989;111:837–43. https://doi.org/10.1115/1.3250794
20. Kloppers JC, Kröger DG. Cooling Tower Performance Evaluation: Merkel, Poppe, and e-NTU Methods of Analysis. J Eng Gas Turbines Power 2005;127:1–7. https://doi.org/10.1115/1.1787504
21. Kloppers JC, Kröger DG. A critical investigation into the heat and mass transfer analysis of counterflow wet-cooling towers. Int J Heat Mass Transf 2005;48:765–77. https://doi.org/10.1016/j.ijheatmasstransfer.2004.09.004
22. Kloppers JC, Kröger DG. Influence of temperature inversions on wet-cooling tower performance. Appl Therm Eng 2005;25:1325–36. https://doi.org/10.1016/j.applthermaleng.2004.09.003
23. Wang C, Liu M, Zhao Y, Qiao Y, Chong D, Yan J. Dynamic modeling and operation optimization for the cold end system of thermal power plants during transient processes. Energy 2018;145:734–46. https://doi.org/10.1016/j.energy.2017.12.146
24. Wu T, Ge Z, Yang L, Du X. Transient behavior of the cold end system in an indirect dry cooling thermal power plant under varying operating conditions. Energy 2019;181:1202–12. https://doi.org/10.1016/j.energy.2019.06.030
25. Arastou A, Ahmadi P, Karrari M. Modeling and Parameter Estimation of a Steam Power Plant Including Condenser Back-Pressure Uncertainty Using Operational Data. IEEE Syst J 2022;16:2979–88. https://doi.org/10.1109/jsyst.2021.3122228
26. Anozie AN, Odejobi OJ. The search for optimum condenser cooling water flow rate in a thermal power plant. Appl Therm Eng 2011;31:4083–90. https://doi.org/10.1016/j.applthermaleng.2011.08.014
27. Zeng H, Meng J, Li Z. Numerical study of a power plant condenser tube arrangement. Appl Therm Eng 2012;40:294–303. https://doi.org/10.1016/j.applthermaleng.2012.02.028
28. Ministry of Housing and Urban-Rural Development of the People's Republic of China. GB/T 50102-2014: Code for design of industrial recirculating water cooling. Beijing: China Planning Press; 2014.
29. Hydraulic Institute. ANSI/HI 9.6.1-2017: Rotodynamic Pumps—Guideline for NPSH Margin. Parsippany, NJ: Hydraulic Institute; 2017.
30. Dobson I, Carreras BA, Lynch VE, Newman DE. Complex systems analysis of series of blackouts: Cascading failure, critical points, and self-organization. Chaos 2007;17:026103. https://doi.org/10.1063/1.2737822
31. Vaiman M, Bell K, Chen Y, Chowdhury B, Dobson I, Hines P, Papic M, Miller S, Zhang P. Risk Assessment of Cascading Outages: Methodologies and Challenges. IEEE Trans Power Syst 2012;27:631–41. https://doi.org/10.1109/TPWRS.2011.2177868
32. Zimmerman RD, Murillo-Sánchez CE, Thomas RJ. MATPOWER: Steady-State Operations, Planning, and Analysis Tools for Power Systems Research and Education. IEEE Trans Power Syst 2011;26:12–19. https://doi.org/10.1109/TPWRS.2010.2051168
33. Kundur P, Paserba J, Ajjarapu V, Andersson G, Bose A, Canizares C, Hatziargyriou N, Hill D, Stankovic A, Taylor C, Van Cutsem T, Vittal V. Definition and Classification of Power System Stability IEEE/CIGRE Joint Task Force on Stability Terms and Definitions. IEEE Trans Power Syst 2004;19:1387–401. https://doi.org/10.1109/TPWRS.2004.825981
34. Palensky P, Van Der Meer AA, Lopez CD, Joseph A, Pan K. Cosimulation of Intelligent Power Systems: Fundamentals, Software Architecture, Numerics, and Coupling. IEEE Ind Electron Mag 2017;11(1):34–50. https://doi.org/10.1109/MIE.2016.2639825
35. Palensky P, van der Meer AA, Lopez CD, Joseph A, Pan K. Applied Cosimulation of Intelligent Power Systems: Implementing Hybrid Simulators for Complex Power Systems. IEEE Ind Electron Mag 2017;11(2):6–21. https://doi.org/10.1109/MIE.2017.2671198
36. Barbierato L, Pons E, Bompard EF, Rajkumar VS, Palensky P, Bottaccioli L, Patti E. Exploring Stability and Accuracy Limits of Distributed Real-Time Power System Simulations via System-of-Systems Cosimulation. IEEE Syst J 2023;17:3354–65. https://doi.org/10.1109/JSYST.2022.3230092
37. Morris MD. Factorial Sampling Plans for Preliminary Computational Experiments. Technometrics 1991;33:161–74. https://doi.org/10.1080/00401706.1991.10484804
38. Campolongo F, Cariboni J, Saltelli A. An effective screening design for sensitivity analysis of large models. Environ Model Softw 2007;22:1509–18. https://doi.org/10.1016/j.envsoft.2006.10.004
39. Pianosi F, Beven K, Freer J, Hall JW, Rougier J, Stephenson DB, Wagener T. Sensitivity analysis of environmental models: A systematic review with practical workflow. Environ Model Softw 2016;79:214–32. https://doi.org/10.1016/j.envsoft.2016.02.008
40. Sarrazin F, Pianosi F, Wagener T. Global Sensitivity Analysis of environmental models: Convergence and validation. Environ Model Softw 2016;79:135–52. https://doi.org/10.1016/j.envsoft.2016.02.005
41. Saltelli A, Sobol’ IM. About the use of rank transformation in sensitivity analysis of model output. Reliab Eng Syst Saf 1995;50:225–39. https://doi.org/10.1016/0951-8320(95)00099-2
42. Refsgaard JC, van der Sluijs JP, Højberg AL, Vanrolleghem PA. Uncertainty in the environmental modelling process – A framework and guidance. Environ Model Softw 2007;22:1543–56. https://doi.org/10.1016/j.envsoft.2007.02.004
43. Lubega WN, Stillwell AS. Maintaining electric grid reliability under hydrologic drought and heat wave conditions. Appl Energy 2018;210:538–49. https://doi.org/10.1016/j.apenergy.2017.06.091
44. Gjorgiev B, Sansavini G. Electrical power generation under policy constrained water-energy nexus. Appl Energy 2018;210:568–79. https://doi.org/10.1016/j.apenergy.2017.09.011
45. Behrens P, van Vliet MTH, Nanninga T, Walsh B, Rodrigues JFD. Climate change and the vulnerability of electricity generation to water stress in the European Union. Nat Energy 2017;2:17114. https://doi.org/10.1038/nenergy.2017.114
46. Kumar Y, Hoesly R, Venkatesh A, Shuster E, Iyengar A. Effects of Short-Term Water Constraints on Electricity Dispatch: A Case Study of ERCOT and SPP Regions. ACS ES&T Water 2022;2:749–58. https://doi.org/10.1021/acsestwater.1c00450
47. Lu C, Yang J, Zhang Q. Pressure Transient Analysis on the Condenser of the HPR1000 Nuclear Power Unit. Energies 2024;17:1210. https://doi.org/10.3390/en17051210
48. Schäfer B, Witthaut D, Timme M, Latora V. Dynamically induced cascading failures in power grids. Nat Commun 2018;9:1975. https://doi.org/10.1038/s41467-018-04287-5
49. Illinois Center for a Smarter Electric Grid (ICSEG), University of Illinois Urbana-Champaign. IEEE 39-Bus System. https://icseg.iti.illinois.edu/ieee-39-bus-system/; 2026 [accessed 15 October 2026].
50. Cetinay H, Soltan S, Kuipers FA, Zussman G, Van Mieghem P. Comparing the effects of failures in power grids under the AC and DC power flow models. IEEE Trans Netw Sci Eng 2018;5(4):301–12. https://doi.org/10.1109/TNSE.2017.2763746
51. Koç Y, Verma T, Araujo NAM, Warnier M. MATCASC: A tool to analyse cascading line outages in power grids. In: 2013 IEEE International Workshop on Intelligent Energy Systems (IWIES); 2013. p. 143–8. https://doi.org/10.1109/IWIES.2013.6698576
52. Fitzmaurice R, Cotilla-Sanchez E, Hines P. Evaluating the impact of modeling assumptions for cascading failure simulation. In: 2012 IEEE Power and Energy Society General Meeting; 2012. p. 1–8. https://doi.org/10.1109/PESGM.2012.6345378
53. Korkali M, Veneman JG, Tivnan BF, Bagrow JP, Hines PDH. Reducing cascading failure risk by increasing infrastructure network interdependence. Sci Rep 2017;7:44499. https://doi.org/10.1038/srep44499
54. Baldwin TL, Tawfik MS, McQueen M. Contingency analysis of cascading line outage events. In: Clemson University Power Systems Conference; 2011. Report INL/CON-11-21104. https://www.osti.gov/biblio/1027903
55. Rezaei P, Hines PDH, Eppstein MJ. Estimating cascading failure risk with random chemistry. IEEE Trans Power Syst 2015;30(5):2726–35. https://doi.org/10.1109/TPWRS.2014.2361735
56. Seguin M-O, Thuaud D, Couton D, Fenot M, Melot V, Plourde F. Experimental and numerical study of pressure increase in a condenser during loss of cooling. Nucl Eng Des 2025;432:113753. https://doi.org/10.1016/j.nucengdes.2024.113753
57. Alcock J-L, Webb DR, Botsch TW, Stephan K. An experimental investigation of the dynamic behaviour of a shell-and-tube condenser. Int J Heat Mass Transf 1997;40(17):4129–35. https://doi.org/10.1016/S0017-9310(97)00018-5
58. Botsch TW, Stephan K, Alcock J-L, Webb DR. Modelling and simulation of the dynamic behaviour of a shell-and-tube condenser. Int J Heat Mass Transf 1997;40(17):4137–49. https://doi.org/10.1016/S0017-9310(97)00019-7
59. Seguin M-O. Étude numérique et expérimentale de la dynamique des phénomènes de convection naturelle au sein de condenseur. Doctoral thesis, ENSMA, 2024. National catalogue https://theses.fr/2024ESMA0005 [accessed 17 October 2026; catalogue/abstract only; manuscript listed confidential until 19 March 2029].

## Appendix A. Current reference assumptions and stress settings

**Table A1. Parameter roles are separated from evidence of numerical performance.** Values are for the 500 MWe archetype unless stated. Stress-test settings are not physical-confidence intervals; fixed coefficients are not silently sampled. G33 scales design flow and basin area by 1.304.

| Parameter group | Reference or tested values | Evidence/use |
|---|---|---|
| Net efficiency / heat-rate penalty | 0.38 / 0.25 | Fixed reference, not site estimate |
| Condenser waste-heat fraction | 0.92 | Fixed heat-duty convention |
| Design approach / TTD | 5.55 / 3.50 K | Steady design inversion |
| Tower multiplier / exponent | 1.0 / 0.45 | Fixed base equipment surrogate |
| Cleanliness / UA flow exponent | 1.0 / 0.80 | Fixed base equipment surrogate |
| Fixed air partial pressure | 0 kPa | No dynamic gas inventory |
| Evaporative fraction / CoC | 0.82 / 4 | Heat-water / design salt rule |
| Drift fraction | $5\times10^{-5}$ | Fixed design loss |
| Basin area / levels | 1600 m² / 3.50, 2.00, 1.00 m | Normal, SOP, trip; scales in area |
| Design NPSH / margin | 8 / 1 m | Pump availability template |
| Head / static lift | 22 / 10 m | Pump/system-head template |
| Backpressure sensitivity / break | 0.007, 0.014 kPa⁻¹ / 5 kPa | Piecewise assumed turbine map |
| Low-pressure bonus / cap | 0.002 kPa⁻¹ / 0.02 | Clamped capability bonus |
| Ramp / technical minimum | 0.02 min⁻¹ / 0.40 | Both strategies / SOP |
| Vacuum set-point / dwell | 15 kPa / 3 s | Protection only |
| Blowdown detection | 900 s | Isolation switches after detection |
| Pump / weather lag | 10 / 900 s | Fixed reference dynamics |
| Condenser anchor | 90 s; stress 30, 60, 90, 180, 300, 600 s | Unidentified; deterministic grid |
| Tower lag | 300 s; stress 30, 300, 1800 s | Unidentified; deterministic grid |

The effective heat capacity has units MJ/K and scales with the design exchange coefficient. Band/equipment multipliers in software are not independently propagated in the current matrix. Protection thresholds do not appear in the finite-storage process target. The low-flow protection criterion does not impose an exchange floor. Reaching protection sets the grid ceiling to zero; it does not supply a resolved plant shutdown trajectory.

## Appendix B. Numerical implementation and evidence ledger

A step begins with current reference duty and water-loss rates. The pump target is calculated from the old level/inlet; midpoint and endpoint flow follow the exponential response. Midpoint weather and flow determine water-side load for the tower target; inlet midpoint and endpoint follow the tower response. The condenser interval uses the inlet midpoint, midpoint conductance and left-end steam duty with its exact frozen-input energy integral. Weather advances, then the basin loss is integrated by endpoint trapezoids, treating blowdown isolation with the left-limit loss on the preceding interval. Backpressure, control caps, both-strategy ramp and ordered protection checks follow. The event's left reference power is saved before recording zero right-limit capability. This is the implemented splitting, not an exact simultaneous solution of all differential/algebraic relations.

**Table B1. Verification and scope ledger.** The accompanying machine-readable claims and source hashes identify the underlying rows; tests are not an empirical validation sample.

| Check | Evidence | Interpretation |
|---|---|---|
| Reference healthy/UA and thermal contracts | 19 dedicated tests | Structural/numerical, not experimental |
| Thermal stress and corner refinement | 54 primary + 12 refined trajectories | 18 discrete settings; not global uncertainty |
| Phase identifiability/source checks | 12 tests | Includes synthetic/analytic tests, not measured traces |
| Current full code suite | 153 pass; 4 reserved document failures | No hidden all-green claim |
| Independent static electrical & recoupled v0.7.2 RQ2 cascade checks | 15 static checks + 8 gate + 60 matrix + 12 detuned-rating runs | Max nodal KCL residual $1.07\times 10^{-11}$ MW; historical v0.7 files untouched |
| Thermal-stress extra electrical work | 96 unique DC points + 12 LP certificates | Original monotone precision failure retained |
| All 18 exchange refinements | Relative bound at most 0.063746% | Same piecewise-linear output; 0 extra grid solves |
| Fault-specific exact-zero lag ablation (RQ3) | 34 settings (32 accepted, 2 inadmissible; 70 solves) + 8 S1a UAE enclosures | First 4-layer failure on S3a_111 retained; 0 new DC solves |
| Migrated v0.7.2 six-encoding, five-load & G34 adequacy expansion | 14 six-encoding/unit rows + 24 load-expansion rows (162 new DC solves) | Confirms 36.13–63.09% ride-down UAE reduction across 1.00–1.20× load and G34 |
| External transient benchmark | Not established; measured calibration traces used = 0 | Data/transferability gap retained |

The thermal stress and LP enclosure commands are reproducible from the prior evidence folders. The monotone-only command intentionally retains a precision-failure exit; the revised dual-certificate gate passes separately. Numerical PASS and external validation `NOT_ESTABLISHED_DATA_GAP` are separate statuses. The RQ3 lag-ablation suite adds 70 deterministic plant trajectory solves using the unchanged cooling core and 0 new DC power-flow solves; no AC run and no full uncertainty campaign are added.

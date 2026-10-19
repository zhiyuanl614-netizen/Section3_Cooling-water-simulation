"""Assemble the RQ1+RQ2+RQ3 complete illustrated manuscript in rq2_recoupled_v072 without modifying frozen files."""
from pathlib import Path
import json,hashlib,re
R=Path(__file__).resolve().parents[3];D=Path(__file__).parent;L=R/'manuscript/revisions/lag_ablation_v072';I=R/'manuscript/revisions/illustrated_v072'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
frozen=json.loads((D/'PRE_EDIT_STATE.json').read_text())['files']
assert len(frozen)==242 and all(sha(R/n)==h for n,h in frozen.items()),'frozen artifact modified'

s=(L/'Full_manuscript_rq3_complete_v072.md').read_text()

# 1. Abstract update: incorporate recoupled RQ2 partial-derate and detuned intermediate snapshot findings.
old_abs='Separately, fixed-capability cascade probes show that load loss and branch removals depend on island-balancing assumptions and need not increase with the number of unavailable units.'
new_abs='Separately, recoupled state-carrying DC cascade snapshots across single-unit loss, dual 50% pump-loss derating (`615.715/479.729 MW`), detuned makeup-interruption first trip (`G34=0`, `G33=351.663 MW` at `4.274 h`) and dual-zero ceilings show that load loss and branch removals depend on island-balancing and branch-removal rules and are non-monotonic in unavailable capacity: under nominal simultaneous headroom redistribution (`H`), the detuned intermediate state removes 11 branches and sheds `1909.5 MW` (and 14 branches / `3154.9 MW` at 0.9 ratings), exceeding both single-unit (`1753.2 MW`) and dual-zero (`1087.2 MW`) outcomes.'
assert old_abs in s
s=s.replace(old_abs,new_abs,1)

# 2. Introduction §1 update: update RQ2 scope sentence.
old_intro='Fixed-ceiling cascade probes address response dependence within RQ2, not a continuously recoupled two-unit thermal chronology.'
new_intro='Recoupled v0.7.2 single-unit, dual-derate and detuned two-unit capability snapshots address response, rule and rating dependence across all 8 minimal-gate and 60 robustness/decorrelation settings within RQ2 while keeping independent state snapshots distinct from a continuous topology-carrying time-domain cascade.'
assert old_intro in s
s=s.replace(old_intro,new_intro,1)

# 3. Section 3.2 update: replace the exclusion paragraph with the v0.7.2 recoupling protocol.
old_s32='''Base-demand cascade probes prescribe healthy ceilings, G33 zero, or both mapped ceilings zero. These inputs are unchanged by the thermal revision. Corresponding simultaneous/sequential rules and 0.9/1.0/1.1 rating multipliers are retained as electrical response tests, not predictions of when plant events occur.

Previously generated partial-capability and detuned thermal-to-cascade snapshots are excluded from current inference because their input trajectories have changed and were not recoupled. Their source files remain available as historical artifacts. The current paper does not infer a continuous two-unit fault chronology from independent zero-capability snapshots.'''
new_s32='''Base-demand cascade probes evaluate five capability states under policies $S$ and $H$, simultaneous and sequential removal rules, and $0.9/1.0/1.1$ branch-rating multipliers: (i) healthy ceilings (`652/508 MW`), (ii) single-unit `G33` outage (`G33=0`), (iii) recoupled `S3a` dual 50% pump-loss derating (`G33=615.715 MW`, `G34=479.729 MW` at 8 h under v0.7.2), (iv) recoupled detuned makeup-interruption first trip (`M6_detuned_at_first_trip`, where a $0.85$ basin-area multiplier on `G34` causes `G34` to trip at $t_1=4.273889$ h while `G33` remains at $351.663$ MW), and (v) dual-zero collapse (`G33=0`, `G34=0`, reached synchronously at $5.047222$ h in `M6_synchronous_G3` or as the second trip $t_2=5.047222$ h in `M6_detuned_at_second_trip`).

Re-deriving the thermal inputs under v0.7.2 and verifying against a fourfold finer thermal step ($\\Delta t=0.25$ s, $15$ s reporting, where $t_1$ and $t_2$ are unchanged and `G33` capability at $t_1$ differs by $0.0061$ MW, altering shed load by at most $0.0061$ MW and branch removals/stages by zero) restores the full 8-row minimal gate, the 60-row rule/rating and decorrelation matrix, and 12 additional rating-sensitivity checks for the detuned intermediate snapshot. Every snapshot is evaluated as an independent static cascade from the intact pre-contingency network; the study does not claim a continuous time-domain cascade in which post-$t_1$ islanded topology is carried forward into $t_2$.'''
assert old_s32 in s
s=s.replace(old_s32,new_s32,1)

# 4. Section 4.4 update: update Tables 4 & 5, text, and Figure 4 caption with the recoupled 68-row v0.7.2 evidence.
old_s44=s[s.index('### 4.4 Fixed-capability'):s.index('### 4.5 The adequacy')]
new_s44='''### 4.4 Recoupled single- and dual-unit grid consequences depend on balancing response

With nominal ratings and simultaneous removal, both healthy policies serve base demand (`6254.23 MW`) without a branch cut. Under the recoupled `S3a` dual 50% pump-loss derating (`G33=615.715 MW`, `G34=479.729 MW`, a combined ceiling reduction of `44.556 MW` below the `632/508 MW` lossless dispatch), policy `S` sheds `44.556 MW` proportionally without branch overloads, whereas policy `H` absorbs the `44.556 MW` deficit through surviving-generator headroom with `0.0 MW` shed and `0` branch removals across all six rule/rating combinations. When `G33` is completely unavailable (`632 MW` lost), `S` sheds `632.0 MW` without overload removals, and setting both wet-unit ceilings to zero sheds `1140.0 MW` without overload removals at nominal ratings. Under the recoupled detuned makeup-interruption first-trip snapshot (`t_1=4.273889 h`, `G34=0 MW`, `G33=351.663 MW`, a combined dispatch deficit of `788.337 MW`), policy `S` sheds `788.337 MW` with zero branch cuts across all rules and ratings.

**Table 4. Recoupled v0.7.2 capability snapshots at base demand (nominal ratings, simultaneous removal).** Values combine the 8-row minimal gate with the nominal simultaneous `M6_detuned_at_first_trip` snapshot. Removal rounds are topological stages, not relay seconds; each row is an independent cascade evaluation from the intact network.

| Capability state (`G33 / G34` ceiling, MW) | Policy | Branches removed | Rounds | Terminal shed MW | Islands |
|---|---|---|---|---|---|
| Healthy (`652.0 / 508.0`) | S | 0 | 0 | 0.0 | 1 |
| Healthy (`652.0 / 508.0`) | H | 0 | 0 | 0.0 | 1 |
| `S3a` dual derate (`615.715 / 479.729`) | S | 0 | 0 | 44.556 | 1 |
| `S3a` dual derate (`615.715 / 479.729`) | H | 0 | 0 | 0.0 | 1 |
| `G33` zero (`0.0 / 508.0`) | S | 0 | 0 | 632.0 | 1 |
| `G33` zero (`0.0 / 508.0`) | H | 12 | 3 | 1753.2 | 8 |
| Detuned 1st trip at `4.274 h` (`351.663 / 0.0`) | S | 0 | 0 | 788.337 | 1 |
| Detuned 1st trip at `4.274 h` (`351.663 / 0.0`) | H | 11 | 3 | 1909.537 | 8 |
| Both zero (`0.0 / 0.0`, sync or 2nd trip at `5.047 h`) | S | 0 | 0 | 1140.0 | 1 |
| Both zero (`0.0 / 0.0`, sync or 2nd trip at `5.047 h`) | H | 3 | 1 | 1087.230 | 3 |

Fig. 4 compares the response-dependent outcomes and all 48 non-healthy rule/rating settings across the four contingency states. Upward headroom redistribution (`H`) changes both the location and the magnitude of branch flows. Under nominal simultaneous removal, moving from `S3a` dual derate (`44.556 MW` deficit) to `G33` zero (`632.0 MW` deficit), detuned first trip (`788.337 MW` deficit) and dual-zero collapse (`1140.0 MW` deficit) produces terminal `H` shedding of `0.0`, `1753.2`, `1909.537` and `1087.230 MW`, with `0`, `12`, `11` and `3` removed branches, respectively. Thus the asymmetric intermediate snapshot (`G34=0`, `G33=351.663 MW`) triggers heavier `H` load shedding than either single-unit outage or complete dual-unit loss, because redistributing `788.337 MW` across the remaining generators while `G33` is capped at `351.663 MW` drives the same three-stage islanding pattern as `G33` loss (`8` islands) with an additional `156.337 MW` generation deficit inside the surviving islands.

**Table 5. Rule and rating sensitivity across all 48 non-healthy recoupled capability combinations.** Entries are removed branches [rounds], ordered by rating multiplier `1.0 / 0.9 / 1.1` (terminal shed MW in parentheses where rating changes alter shedding). All 12 healthy control combinations have `0 [0]` cuts and `0.0 MW` shed.

| Capability state | Policy | Simultaneous: `1.0 / 0.9 / 1.1` | Sequential: `1.0 / 0.9 / 1.1` |
|---|---|---|---|
| `S3a` dual derate (`615.715 / 479.729`) | S | `0 [0] / 0 [0] / 0 [0]` (`44.6 MW` all) | `0 [0] / 0 [0] / 0 [0]` (`44.6 MW` all) |
| `S3a` dual derate (`615.715 / 479.729`) | H | `0 [0] / 0 [0] / 0 [0]` (`0.0 MW` all) | `0 [0] / 0 [0] / 0 [0]` (`0.0 MW` all) |
| `G33` zero (`0.0 / 508.0`) | S | `0 [0] / 0 [0] / 0 [0]` (`632.0 MW` all) | `0 [0] / 0 [0] / 0 [0]` (`632.0 MW` all) |
| `G33` zero (`0.0 / 508.0`) | H | `12 [3] / 11 [3] / 11 [3]` (`1753.2 MW` all) | `3 [3] / 3 [3] / 3 [3]` (`1155.7 MW` all) |
| Detuned 1st trip (`351.663 / 0.0` at `4.274 h`) | S | `0 [0] / 0 [0] / 0 [0]` (`788.3 MW` all) | `0 [0] / 0 [0] / 0 [0]` (`788.3 MW` all) |
| Detuned 1st trip (`351.663 / 0.0` at `4.274 h`) | H | `11 [3] / 14 [5] / 12 [3]` (`1909.5 / 3154.9 / 1909.5 MW`) | `3 [3] / 3 [3] / 3 [3]` (`1312.1 MW` all) |
| Both zero (`0.0 / 0.0`, sync or 2nd trip) | S | `0 [0] / 2 [1] / 0 [0]` (`1140.0 MW` all) | `0 [0] / 1 [1] / 0 [0]` (`1140.0 MW` all) |
| Both zero (`0.0 / 0.0`, sync or 2nd trip) | H | `3 [1] / 3 [1] / 3 [1]` (`1087.2 MW` all) | `3 [3] / 7 [7] / 3 [3]` (`1670.2 / 3843.7 / 1670.2 MW`) |

Sequential removal (`1` branch per stage) and rating multipliers further reverse the apparent severity ranking between intermediate and dual-zero states. Under sequential `H` removal at nominal ratings, `G33` loss, detuned first trip and dual-zero loss all remove `3` branches in `3` rounds, but shed `1155.730`, `1312.067` and `1670.168 MW`, respectively; at `0.9` ratings, simultaneous `H` makes the detuned first trip most severe (`14` branches in `5` rounds, `3154.947 MW` shed, `9` islands), whereas sequential `H` makes dual-zero loss most severe (`7` branches in `7` rounds, `3843.685 MW` shed). Every one of the 80 evaluated cascade runs (8 gate, 60 matrix, 12 detuned rating checks) satisfies exact per-island KCL and capacity bounds with maximum nodal residual $1.07\times 10^{-11}$ MW.

![Figure 4: Recoupled capability consequences depend on balancing and branch-removal rules.](figures/fig04.png){width=170mm}

**Figure 4. Recoupled capability consequences depend on balancing and branch-removal rules.** a, At nominal ratings with simultaneous removal, terminal shed load across the four v0.7.2 recoupled non-healthy states—`S3a` dual 50% pump-loss derating (`615.715/479.729 MW`), `G33` zero (`0/508 MW`), detuned makeup-interruption first trip at `4.273889 h` (`351.663/0 MW`) and both wet units zero (`0/0 MW` at `5.047222 h`)—increases monotonically from `44.556` to `632.0`, `788.337` and `1140.0 MW` under `S`, but varies non-monotonically from `0.0` to `1753.2`, `1909.537` and `1087.230 MW` under `H`. Connecting segments pair ordered capability states, not a continuous time-domain cascade. b, All 48 non-healthy combinations of capability state, `S/H` policy, simultaneous/sequential removal and rating multiplier (`1.0, 0.9, 1.1`); cells report removed branches [topological removal rounds]. Pale row bands group states and do not encode magnitude. Both panels use base demand (`6254.23 MW`); the 68-row source file (`fig04_all68_recoupled_electrical_probes.csv`) retains all healthy controls and duplicated baseline rows.

'''
s=s.replace(old_s44,new_s44,1)

# 5. Section 5.3 update: update paragraph on partial/detuned states.
old_s53='Common cooling supplies or auxiliary power can motivate correlated capability states, but the retained electrical probes prescribe those states. A common final zero-ceiling input does not show that distinct initiating faults or prior network histories are interchangeable. Partial-capability and detuned chronology claims require rederived thermal inputs and, for a true chronological study, persistent grid states and explicit dispatch/restoration timing.'
new_s53='Common cooling supplies or auxiliary power can motivate correlated capability states, and recoupling the `S3a` dual-derate and detuned makeup-interruption states under v0.7.2 shows why intermediate asymmetric capability ceilings cannot be interpolated from single- and dual-zero endpoints: at $t_1=4.273889$ h (`G34=0`, `G33=351.663 MW`), upward headroom redistribution (`H`) sheds `1909.537 MW` under simultaneous removal (`3154.947 MW` at 0.9 ratings), whereas mild partial derating (`S3a`) is completely absorbed by `H` (`0.0 MW` shed vs `44.556 MW` under `S`). Even so, each snapshot is evaluated from the intact pre-contingency network; a true chronological cascade study would require carrying post-$t_1$ islanded topology, generator thermal states and explicit dispatch/restoration timing forward into $t_2$.'
assert old_s53 in s
s=s.replace(old_s53,new_s53,1)

# 6. Section 6 Conclusions update: include recoupled RQ2 findings.
old_c6='Fixed-ceiling cascade probes separately demonstrate that finite, conserving response assumptions affect branch removals and terminal shedding; the number of unavailable wet units alone does not order either metric.'
new_c6='Recoupled state-carrying cascade snapshots across mild dual derating (`S3a`), single-unit loss, detuned first-trip asymmetry (`4.274 h`) and dual-zero collapse (`5.047 h`) demonstrate that finite, conserving response assumptions and removal rules govern branch removals and terminal shedding; under `H`, the detuned intermediate state (`1909.5 MW` nominal simultaneous shed) is more severe than complete dual-unit loss (`1087.2 MW`), whereas `S3a` dual derating is fully absorbed (`0.0 MW` shed).'
assert old_c6 in s
s=s.replace(old_c6,new_c6,1)

# 7. Declarations & Appendix Table B1 update: record rq2_recoupled_v072.
old_decl='The fixed-input electrical subset is reproducibly extracted from the unchanged `code/examples/dc_minimal_validation_v07.csv` and `m2_cascade_robustness.csv`; the manifest accompanying this draft records the exact selection.'
new_decl='The recoupled v0.7.2 electrical cascade gate (8 rows), full rule/rating and decorrelation matrix (60 rows), and detuned first-trip rating sensitivity (12 rows) are archived under `manuscript/revisions/rq2_recoupled_v072/outputs`, while the historical `code/examples/dc_minimal_validation_v07.csv` and `m2_cascade_robustness.csv` remain untouched.'
assert old_decl in s
s=s.replace(old_decl,new_decl,1)

old_tb1='| Previous independent static electrical checks | 15 cases | Electrical source unchanged |'
new_tb1='| Independent static electrical & recoupled v0.7.2 RQ2 cascade checks | 15 static checks + 8 gate + 60 matrix + 12 detuned-rating runs | Max nodal KCL residual $1.07\\times 10^{-11}$ MW; historical v0.7 files untouched |'
assert old_tb1 in s
s=s.replace(old_tb1,new_tb1,1)

(D/'Full_manuscript_rq2_rq3_complete_v072.md').write_text(s)
rq=json.loads((L/'RQ_CONTRACT.json').read_text())
rq['RQ2']='single/dual loss, island balance, reserves and branch rules; answered via recoupled v0.7.2 8-row gate + 60-row matrix + 12 detuned rating checks (independent static state snapshots, not a continuous topology-carrying cascade)'
(D/'RQ_CONTRACT.json').write_text(json.dumps(rq,ensure_ascii=False,indent=2)+'\n')

caps=json.loads((I/'FIGURE_CAPTIONS.json').read_text())
for item in caps:
 if item['figure']==4:
  item['title']='Recoupled capability consequences depend on balancing and branch-removal rules.'
  item['caption']='a, At nominal ratings with simultaneous removal, terminal shed load across the four v0.7.2 recoupled non-healthy states—S3a dual 50% pump-loss derating (615.715/479.729 MW), G33 zero (0/508 MW), detuned makeup-interruption first trip at 4.273889 h (351.663/0 MW) and both wet units zero (0/0 MW at 5.047222 h)—increases monotonically from 44.556 to 632.0, 788.337 and 1140.0 MW under S, but varies non-monotonically from 0.0 to 1753.2, 1909.537 and 1087.230 MW under H. Connecting segments pair ordered capability states, not a continuous time-domain cascade. b, All 48 non-healthy combinations of capability state, S/H policy, simultaneous/sequential removal and rating multiplier (1.0, 0.9, 1.1); cells report removed branches [topological removal rounds]. Pale row bands group states and do not encode magnitude. Both panels use base demand (6254.23 MW); the 68-row source file (fig04_all68_recoupled_electrical_probes.csv) retains all healthy controls and duplicated baseline rows.'
(D/'FIGURE_CAPTIONS.json').write_text(json.dumps(caps,ensure_ascii=False,indent=2)+'\n')

assert all(sha(R/n)==h for n,h in frozen.items())
print('Wrote Full_manuscript_rq2_rq3_complete_v072.md; words:',len(s.split()),'chars:',len(s))

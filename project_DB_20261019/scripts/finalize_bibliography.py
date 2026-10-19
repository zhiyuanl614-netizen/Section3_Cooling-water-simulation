"""Update Full_manuscript_rq2_rq3_complete_v072.md with complete 59-entry bibliography, v0.7.2 six-encoding/five-load/G34 adequacy migration (Table 7), and editorial/typography optimizations."""
from pathlib import Path
import json,hashlib,re
R=Path(__file__).resolve().parents[3];D=Path(__file__).parent;L=R/'manuscript/revisions/lag_ablation_v072'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
frozen=json.loads((D/'PRE_EDIT_STATE.json').read_text())['files']
assert len(frozen)==242 and all(sha(R/n)==h for n,h in frozen.items()),'frozen artifact modified'

# Run the base RQ2+RQ3 update first from lag_ablation_v072
import update_manuscript

s=(D/'Full_manuscript_rq2_rq3_complete_v072.md').read_text()
meta=json.loads((D/'CROSSREF_FULL_METADATA.json').read_text())

# 1. Update frontmatter banner to include structured author/correspondence placeholders and updated 11-table count
old_banner='> **Illustrated research candidate, v0.7.2 — 17 October 2026.** The three research questions are retained verbatim from the historical manuscript. Six new figures are derived from the revised evidence and the full-text-first figure contract. This is an internal-review candidate, not a submission-ready or externally calibrated plant model. Historical manuscripts and figures remain unchanged.'
new_banner='''**[Author Name 1]^a,*, [Author Name 2]^a,b, [Author Name 3]^b**

^a *[Department / Institute, University / Organization, City, Postal Code, Country]*  
^b *[School / Key Laboratory, University / Organization, City, Postal Code, Country]*  
*\\* Corresponding author. E-mail address: `[corresponding.author@institution.edu]`*

> **Submission-formatted illustrated candidate, v0.7.2 — 17 October 2026.** The three original research questions are retained verbatim from the historical manuscript, with RQ1–RQ3 evidence (including the migrated v0.7.2 six-encoding, five-load and G34 adequacy comparisons), six newly rendered 170 mm figures, 11 tables, 27 editable display equations and all 59 full-title bibliographic entries verified. Author names, affiliations and funding numbers above and in the Declarations section are structured placeholders to be filled in by the authors prior to journal upload; external plant transient calibration remains an explicit future-work boundary (`NOT_ESTABLISHED_DATA_GAP`).'''
assert old_banner in s
s=s.replace(old_banner,new_banner,1)

# 2. Optimize Highlight #5 to strictly satisfy Elsevier <= 85 character limit (82 chars)
old_hl5='5. Inadmissible lag-omission controls are excluded rather than assigned finite bias factors.'
new_hl5='5. Inadmissible zero-lag controls are excluded rather than given finite bias factors.'
assert old_hl5 in s and len(new_hl5)<=85
s=s.replace(old_hl5,new_hl5,1)

# 3. Tighten Abstract to <= 300 words (~265 words) while retaining all exact RQ1, RQ2, and RQ3 headline numbers
old_abs_block=s.split('## Abstract\n\n')[1].split('\n\n**Keywords:**')[0]
new_abs_block=(
 "Cooling emergencies are often represented as prescribed derating or immediate generator loss, although wet-recirculating plants lose capability through distinct inventory, hydraulic and pressure pathways. "
 "We formulate a reference-anchored, finite-storage cold-end surrogate and pass its available-power trajectory as a ceiling to separate DC adequacy and overload-propagation models without fitting site transient data. "
 "For a 652 MW equivalent unit, makeup interruption reaches low-level protection at 5.047 h with blowdown isolation versus 3.855 h with maintained blowdown, whereas holding initial steam duty trips at 4.296 h (2796.950 versus 2738.433 MWh reference energy). "
 "Across an 18-setting thermal stress matrix, makeup trips remain inventory-controlled at 4.907–5.065 h, while full pump-loss trips span 42.43–572.50 s. "
 "At 1.15 times demand on the IEEE 39-bus network, one-minute event-aware DC adequacy integration gives 2170.680 MWh incremental unserved energy for reference ride-down versus 4634.437 MWh for immediate loss (−53.16%; 18-setting LP-dual/monotone bounds: 52.025–53.306%); migrating all six benchmark encodings, five demand levels (1.00–1.20) and unit G34 confirms this ordering across 36.13–63.09% reduction. "
 "Recoupled state-carrying DC cascade snapshots across dual 50% pump-loss derating (615.715/479.729 MW), single-unit loss, detuned makeup first trip (G34 = 0, G33 = 351.663 MW at 4.274 h) and dual-zero ceilings show non-monotonic rule dependence: under nominal simultaneous headroom redistribution (H), the detuned intermediate state removes 11 branches and sheds 1909.5 MW (14 branches and 3154.9 MW at 0.9 ratings), exceeding single-unit (1753.2 MW) and dual-zero (1087.2 MW) outcomes. "
 "A 34-setting exact-zero lag ablation separates inadmissible zero-storage/zero-flow pump-loss controls from valid conditional and joint ablations: omitting condenser storage in full pump loss understates trip time by 89.660% (10.063 versus 97.315 s), omitting all three lags in 50% pump loss causes a spurious 3.0005 s trip (−99.989% energy), and omitting condenser storage in makeup interruption shifts trip time by +93.0 to +94.0 s (−9.826 to −10.018 MWh unserved energy)."
)
assert len(new_abs_block.split())<=300,f"Abstract words: {len(new_abs_block.split())}"
s=s.replace(old_abs_block,new_abs_block,1)

# 4. Replace the unmigrated disclaimer in Section 4.5 with the migrated v0.7.2 six-encoding, five-load and G34 adequacy comparison (Table 7), and renumber the lag-ablation table to Table 8
old_unmig='This result supports a conditional adequacy contrast over the tested settings. It does not establish conservatism of every black-box outage encoding, all loads or other network locations. Historical six-encoding, five-load and G34 thermal comparisons have not been migrated to the current closure and are not reported as current results.'
new_mig='''To test whether this adequacy ordering persists across broader black-box encodings, demand levels and generator locations under the current v0.7.2 closure, Table 7 migrates the six-encoding benchmark set, the five-load expansion ($1.00$–$1.20\\times$ base demand) and the mapped G34 unit ($508$ MW at Bus 34) at the 15 min event-aware exchange resolution (requiring 162 additional verified DC-OPF snapshots beyond the existing 962-point cache, all converged with zero branch overloads and nodal residuals below $10^{-5}$ MW). Across all five demand levels on G33, mechanistic ride-down reduces incremental UAE by $36.13\\%$ (at $1.15\\times$ demand, where the 3.293 h diagnostic hold-up proxy yields $2727.056$ MWh and the linear-to-minimum proxy yields $3261.018$ MWh) to $63.09\\%$ (at $1.00\\times$ demand, where ride-down capability remains above the zero-shedding threshold until the 5.047222 h trip and therefore matches the trip-aligned control at $361.042$ MWh against $978.175$ MWh for immediate loss). On G34 at $1.15\\times$ demand, immediate loss, diagnostic hold-up, simplified level-band ($4.069167$ h backpressure trip), mechanistic ride-down, mechanistic hold-load and trip-aligned control yield $3560.317$, $2095.008$, $1887.063$, $1665.548$, $1650.919$ and $1314.103$ MWh, respectively—preserving the exact $-53.219\\%$ ride-down reduction relative to immediate loss and the $-63.090\\%$ trip-aligned reduction observed on G33.

**Table 7. Migrated v0.7.2 adequacy comparisons across six outage encodings, five demand levels (1.00–1.20×) and mapped units G33/G34 (15 min event-aware exchange, 8 h horizon).** Numbers in parentheses in Panel B denote percentage change relative to immediate loss at the same demand multiplier.

| Panel A: Six encodings & aligned control at $1.15\\times$ demand | Trip mechanism | Trip time (h) | G33 $E_r$ (MWh) | G33 inc. UAE (MWh) | G34 $E_r$ (MWh) | G34 inc. UAE (MWh) |
|---|---|---|---|---|---|---|
| Immediate loss (`instant_trip`) | Assumed instant trip | 0.000000 | 0.000 | 4634.437 | 0.000 | 3560.317 |
| Linear ramp to min then trip (`linear_to_min_then_trip`) | Assumed linear derate | 3.292536 | 1502.713 | 3261.018 ($-29.64\\%$) | 1170.826 | 2503.548 ($-29.68\\%$) |
| Diagnostic hold-up (`fixed_holdup_trip`) | Assumed fixed hold-up | 3.292536 | 2146.733 | 2727.056 ($-41.16\\%$) | 1672.608 | 2095.008 ($-41.16\\%$) |
| Simplified level-band (`simplified_level_band`) | Backpressure protection | 4.069167 | 2431.245 | 2456.180 ($-47.00\\%$) | 1894.283 | 1887.063 ($-47.00\\%$) |
| Mechanistic ride-down (`mechanistic_ride_down`, 15 min) | Pump low-level trip | 5.047222 | 2738.433 | 2170.255 ($-53.17\\%$) | 2133.626 | 1665.548 ($-53.22\\%$) |
| Mechanistic hold-load (`mechanistic_hold_load`, C1) | Pump low-level trip | 4.296389 | 2796.950 | 2148.940 ($-53.63\\%$) | 2179.219 | 1650.919 ($-53.63\\%$) |
| Trip-aligned flat capability (`delayed_instant_trip`) | Aligned control | 5.047222 | 3290.789 | 1710.558 ($-63.09\\%$) | 2563.989 | 1314.103 ($-63.09\\%$) |
| **Panel B: G33 five-load expansion (0–8 h inc. UAE, MWh)** | **Baseline shed (MW)** | **Immediate loss (`0 h`)** | **Fixed hold-up (`3.293 h`)** | **Mech. ride-down (`5.047 h`)** | **Aligned flat (`5.047 h`)** | **Ride-down vs. hold-up** |
| Load scale $1.00\\times$ ($6254.23$ MW) | 0.000 | 978.175 | 575.590 ($-41.16\\%$) | 361.042 ($-63.09\\%$) | 361.042 ($-63.09\\%$) | $-214.549$ MWh ($-37.27\\%$) |
| Load scale $1.05\\times$ ($6566.94$ MW) | 0.000 | 2627.722 | 1546.238 ($-41.16\\%$) | 1047.911 ($-60.12\\%$) | 969.885 ($-63.09\\%$) | $-498.327$ MWh ($-32.23\\%$) |
| Load scale $1.10\\times$ ($6879.65$ MW) | 56.609 | 4374.981 | 2574.383 ($-41.16\\%$) | 2054.064 ($-53.05\\%$) | 1614.793 ($-63.09\\%$) | $-520.319$ MWh ($-20.21\\%$) |
| Load scale $1.15\\times$ ($7192.36$ MW) | 342.199 | 4634.437 | 2727.056 ($-41.16\\%$) | 2170.255 ($-53.17\\%$) | 1710.558 ($-63.09\\%$) | $-556.801$ MWh ($-20.42\\%$) |
| Load scale $1.20\\times$ ($7505.08$ MW) | 649.190 | 4843.525 | 2850.090 ($-41.16\\%$) | 2296.982 ($-52.58\\%$) | 1787.732 ($-63.09\\%$) | $-553.107$ MWh ($-19.41\\%$) |'''
assert old_unmig in s
s=s.replace(old_unmig,new_mig,1)

# Renumber the lag-ablation table from Table 7 to Table 8 in prose and caption
s=s.replace('To address the second part of RQ3—how omitting second-to-minute plant lags biases the studied outcomes—Table 7 summarizes','To address the second part of RQ3—how omitting second-to-minute plant lags biases the studied outcomes—Table 8 summarizes',1)
s=s.replace('**Table 7. Fault-specific exact-zero lag-omission biases across the four contingency classes.**','**Table 8. Fault-specific exact-zero lag-omission biases across the four contingency classes.**',1)
s=s.replace('outage encoding (Table 6, Fig. 5) and omission of second-to-minute plant lags (Table 7)','outage encoding (Tables 6–7, Fig. 5) and omission of second-to-minute plant lags (Table 8)',1)

# 5. Clean up spacing typos in Figure 2, Table 6, Figure 5, Figure 6, Table A1, and Table B1
spacing_fixes=[
 ('Events occur at 5.047222,3.855000 and 4.296389 h','Events occur at 5.047222, 3.855000 and 4.296389 h'),
 ('| Reference mechanism,1 min |','| Reference mechanism, 1 min |'),
 ('for immediate loss,1710.558 MWh','for immediate loss, 1710.558 MWh'),
 ('and−460.122233 MWh','and −460.122233 MWh'),
 ('failure is retained;12 independent LP','failure is retained; 12 independent LP'),
 ('| 1600 m² /3.50,2.00,1.00 m | Normal,SOP,trip; scales in area |','| 1600 m² / 3.50, 2.00, 1.00 m | Normal, SOP, trip; scales in area |'),
 ('| 0.007,0.014 kPa⁻¹ /5 kPa |','| 0.007, 0.014 kPa⁻¹ / 5 kPa |'),
 ('| 0.002 kPa⁻¹ /0.02 |','| 0.002 kPa⁻¹ / 0.02 |'),
 ('| 0.02 min⁻¹ /0.40 | Both strategies /SOP |','| 0.02 min⁻¹ / 0.40 | Both strategies / SOP |'),
 ('| 15 kPa /3 s |','| 15 kPa / 3 s |'),
 ('| 10 /900 s |','| 10 / 900 s |'),
 ('| 90 s; stress30,60,90,180,300,600 s |','| 90 s; stress 30, 60, 90, 180, 300, 600 s |'),
 ('| 300 s; stress30,300,1800 s |','| 300 s; stress 30, 300, 1800 s |'),
 ('| 54 primary +12 refined trajectories |','| 54 primary + 12 refined trajectories |'),
 ('| 153 pass;4 reserved document failures |','| 153 pass; 4 reserved document failures |'),
 ('| 96 unique DC points +12 LP certificates |','| 96 unique DC points + 12 LP certificates |'),
 ('| All18 exchange refinements | Relative bound at most0.063746% | Same piecewise-linear output;0 extra grid solves |',
  '| All 18 exchange refinements | Relative bound at most 0.063746% | Same piecewise-linear output; 0 extra grid solves |'),
 ('| Not established;measured calibration traces used=0 |','| Not established; measured calibration traces used = 0 |'),
]
for old_t,new_t in spacing_fixes:
 assert old_t in s,f"missing spacing target: {old_t}"
 s=s.replace(old_t,new_t,1)

# Add the migrated v0.7.2 adequacy expansion row to Table B1 and Declarations
old_tb1_tail='| Fault-specific exact-zero lag ablation (RQ3) | 34 settings (32 accepted, 2 inadmissible; 70 solves) + 8 S1a UAE enclosures | First 4-layer failure on `S3a_111` retained; 0 new DC solves |'
new_tb1_tail=old_tb1_tail+'\n| Migrated v0.7.2 six-encoding, five-load & G34 adequacy expansion | 14 six-encoding/unit rows + 24 load-expansion rows (162 new DC solves) | Confirms 36.13–63.09% ride-down UAE reduction across 1.00–1.20× load and G34 |'
assert old_tb1_tail in s
s=s.replace(old_tb1_tail,new_tb1_tail,1)

old_decl_out='and detuned first-trip rating sensitivity (12 rows) are archived under `manuscript/revisions/rq2_recoupled_v072/outputs`, while the historical `code/examples/dc_minimal_validation_v07.csv` and `m2_cascade_robustness.csv` remain untouched.'
new_decl_out='detuned first-trip rating sensitivity (12 rows), and migrated v0.7.2 six-encoding, five-load and G34 adequacy tables (`opf_six_encodings_v072.csv`, `opf_encoding_expand_v072.csv`, `OPF_EXPAND_V072_GATE.json`) are archived under `manuscript/revisions/rq2_recoupled_v072/outputs`, while the historical `code/examples/dc_minimal_validation_v07.csv` and `m2_cascade_robustness.csv` remain untouched.'
assert old_decl_out in s
s=s.replace(old_decl_out,new_decl_out,1)

# 6. Build complete 59-entry References block with verified full titles and normalized author names
old_ref_block=s.split('## References\n\n')[1].split('\n\n## Appendix A.')[0]
old_lines=old_ref_block.strip().splitlines()
assert len(old_lines)==59

author_overrides={
 10: 'Peer RAM, Sanders KT',
 17: 'Stillwell AS, King CW, Webber ME',
 20: 'Kloppers JC, Kröger DG',
 27: 'Zeng H, Meng J, Li Z',
 31: 'Vaiman M, Bell K, Chen Y, Chowdhury B, Dobson I, Hines P, Papic M, Miller S, Zhang P',
 33: 'Kundur P, Paserba J, Ajjarapu V, Andersson G, Bose A, Canizares C, Hatziargyriou N, Hill D, Stankovic A, Taylor C, Van Cutsem T, Vittal V',
 36: 'Barbierato L, Pons E, Bompard EF, Rajkumar VS, Palensky P, Bottaccioli L, Patti E',
 39: 'Pianosi F, Beven K, Freer J, Hall JW, Rougier J, Stephenson DB, Wagener T',
}

new_lines=[]
for line in old_lines:
 m=re.match(r'^(\d+)\.\s+(.*)$',line)
 idx=int(m.group(1));rest=m.group(2)
 if idx<=48 and str(idx) in meta:
  d=meta[str(idx)]
  m2=re.match(r'^(.*?)\.\s+([A-Za-z0-9\s&/-]+?\s+\d{4};.*?\s+https://doi\.org/\S+)$',rest)
  assert m2,f"parse failed on {idx}: {rest}"
  orig_auth,jour_part=m2.group(1),m2.group(2)
  orig_auth=author_overrides.get(idx,orig_auth).rstrip('.')
  jour_part=jour_part.replace('Reg Environ Change','Reg Environ Chang').replace('Int J Heat Mass Transfer','Int J Heat Mass Transf').replace('ACS ES&T Water','ACS ES&T Water')
  title=d['title'].rstrip('.')
  new_lines.append(f"{idx}. {orig_auth}. {title}. {jour_part}")
 elif idx==18:
  new_lines.append("18. Heat Exchange Institute (HEI). Standards for Steam Surface Condensers. 12th ed. Cleveland, OH: Heat Exchange Institute; 2017.")
 elif idx==28:
  new_lines.append("28. Ministry of Housing and Urban-Rural Development of the People's Republic of China. GB/T 50102-2014: Code for design of industrial recirculating water cooling. Beijing: China Planning Press; 2014.")
 elif idx==29:
  new_lines.append("29. Hydraulic Institute. ANSI/HI 9.6.1-2017: Rotodynamic Pumps—Guideline for NPSH Margin. Parsippany, NJ: Hydraulic Institute; 2017.")
 elif idx==49:
  new_lines.append("49. Illinois Center for a Smarter Electric Grid (ICSEG), University of Illinois Urbana-Champaign. IEEE 39-Bus System. https://icseg.iti.illinois.edu/ieee-39-bus-system/; 2026 [accessed 15 October 2026].")
 elif idx==50:
  new_lines.append("50. Cetinay H, Soltan S, Kuipers FA, Zussman G, Van Mieghem P. Comparing the effects of failures in power grids under the AC and DC power flow models. IEEE Trans Netw Sci Eng 2018;5(4):301–12. https://doi.org/10.1109/TNSE.2017.2763746")
 elif idx==51:
  new_lines.append("51. Koç Y, Verma T, Araujo NAM, Warnier M. MATCASC: A tool to analyse cascading line outages in power grids. In: 2013 IEEE International Workshop on Intelligent Energy Systems (IWIES); 2013. p. 143–8. https://doi.org/10.1109/IWIES.2013.6698576")
 elif idx==52:
  new_lines.append("52. Fitzmaurice R, Cotilla-Sanchez E, Hines P. Evaluating the impact of modeling assumptions for cascading failure simulation. In: 2012 IEEE Power and Energy Society General Meeting; 2012. p. 1–8. https://doi.org/10.1109/PESGM.2012.6345378")
 elif idx==53:
  new_lines.append("53. Korkali M, Veneman JG, Tivnan BF, Bagrow JP, Hines PDH. Reducing cascading failure risk by increasing infrastructure network interdependence. Sci Rep 2017;7:44499. https://doi.org/10.1038/srep44499")
 elif idx==54:
  new_lines.append("54. Baldwin TL, Tawfik MS, McQueen M. Contingency analysis of cascading line outage events. In: Clemson University Power Systems Conference; 2011. Report INL/CON-11-21104. https://www.osti.gov/biblio/1027903")
 elif idx==55:
  new_lines.append("55. Rezaei P, Hines PDH, Eppstein MJ. Estimating cascading failure risk with random chemistry. IEEE Trans Power Syst 2015;30(5):2726–35. https://doi.org/10.1109/TPWRS.2014.2361735")
 elif idx==56:
  new_lines.append("56. Seguin M-O, Thuaud D, Couton D, Fenot M, Melot V, Plourde F. Experimental and numerical study of pressure increase in a condenser during loss of cooling. Nucl Eng Des 2025;432:113753. https://doi.org/10.1016/j.nucengdes.2024.113753")
 elif idx==57:
  new_lines.append("57. Alcock J-L, Webb DR, Botsch TW, Stephan K. An experimental investigation of the dynamic behaviour of a shell-and-tube condenser. Int J Heat Mass Transf 1997;40(17):4129–35. https://doi.org/10.1016/S0017-9310(97)00018-5")
 elif idx==58:
  new_lines.append("58. Botsch TW, Stephan K, Alcock J-L, Webb DR. Modelling and simulation of the dynamic behaviour of a shell-and-tube condenser. Int J Heat Mass Transf 1997;40(17):4137–49. https://doi.org/10.1016/S0017-9310(97)00019-7")
 elif idx==59:
  new_lines.append(line)
 else:
  raise AssertionError(f"unhandled ref {idx}")

assert len(new_lines)==59
assert not any('..' in l or 'Kro¨ger' in l for l in new_lines)
s=s.replace(old_ref_block,'\n'.join(new_lines),1)

# 7. Update Declarations section with complete structured CRediT / Funding / Competing interests templates and updated reference status
old_decl_tail='''**Competing interests, CRediT and other author declarations.** To be completed by the authors; no authorship, funding or conflict statement is inferred by the research assistant.

**Reference status.** The original numbering is retained and new relevant sources are appended. Standards editions, bibliographic titles and journal formatting still require author-level completion/checking. Source access levels for the transient benchmark review are stated explicitly; retaining a citation does not claim that all historical full texts were re-reviewed in this revision.'''

new_decl_tail='''**CRediT authorship contribution statement.** **[Author 1]:** Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Data curation, Visualization, Writing – original draft, Writing – review & editing. **[Author 2]:** Methodology, Validation, Investigation, Writing – review & editing, Supervision. **[Author 3]:** Conceptualization, Resources, Writing – review & editing, Project administration, Funding acquisition. *(Placeholder roles for author verification prior to submission; no authorship is assumed by the research assistant.)*

**Declaration of competing interest.** The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper. *(To be confirmed by the authors at submission.)*

**Funding.** This work was supported by `[Funding Agency Name, Grant/Award Number(s)]`. *(To be completed by the authors prior to submission.)*

**Reference status.** All 59 numbered references include full article/standard titles, standardized author names and journal abbreviations, volume/page or article numbers, and verified DOIs or URLs while preserving the exact in-text citation numbering [1–59]. Source access levels for the transient benchmark review ([47,56–59]) are stated explicitly; retaining a historical citation does not claim that all historical full texts were re-reviewed in this revision.'''

assert old_decl_tail in s
s=s.replace(old_decl_tail,new_decl_tail,1)

# 8. Clean up excessive inline code backticks (`...`) around numeric values, unit labels, and scenario names in main prose/tables, while keeping genuine code/file/identifier spans intact
keep_code_patterns=[
 r'^\[corresponding\.author@institution\.edu\]$',
 r'^NOT_ESTABLISHED_DATA_GAP$',
 r'^reference_template_not_site_measured$',
 r'^cooling/.*$',
 r'^manuscript/.*$',
 r'^code/.*$',
 r'.*\.(py|csv|json|md|docx|zip)$',
 r'^RESEARCH_FRAMEWORK\.md$',
 r'^NoQuasiStaticEquilibrium$',
 r'^pump_level$',
 r'^backpressure_protection$',
 r'^no_trip_within_horizon$',
 r'^instant_trip$',
 r'^linear_to_min_then_trip$',
 r'^fixed_holdup_trip$',
 r'^simplified_level_band$',
 r'^mechanistic_ride_down$',
 r'^mechanistic_hold_load$',
 r'^delayed_instant_trip$',
 r'^M6_detuned_at_first_trip$',
 r'^M6_synchronous_G3$',
 r'^M6_detuned_at_second_trip$',
 r'^quasi_static$',
 r'^\[Funding Agency Name, Grant/Award Number\(s\)\]$',
]
def clean_backtick(m):
 val=m.group(1)
 if any(re.match(p,val) for p in keep_code_patterns):
  return f"`{val}`"
 return val

s=re.sub(r'`([^`\n]+)`',clean_backtick,s)

(D/'Full_manuscript_rq2_rq3_complete_v072.md').write_text(s)
assert all(sha(R/n)==h for n,h in frozen.items())
print('Updated Full_manuscript_rq2_rq3_complete_v072.md; total words:',len(s.split()),'Abstract words:',len(new_abs_block.split()))

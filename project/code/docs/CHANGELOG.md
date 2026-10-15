# 变更日志（Changelog）

> 本文件是 `coal-cooling-ieee39` 的单一事实来源。参数口径变更必须同步记录代码、CSV 与研究框架的对应变化。

## v0.6.1 — 2026-10-15：IEEE 39 官方数据对齐（映射机组收口到 Bus 33/34）

- [数据] `data/ieee39_unit_config.csv`：冷端建模范围由三台（G30/G34/G38）改为手稿声明的两台映射机组 **G33（Bus 33，652 MW）与 G34（Bus 34，508 MW）**，容量取 MATPOWER case39 的 `Pmax`；G30/G38 标为不建模（case39 中分别为 hydro 与 nuclear 标签）。全机组合计 7367.0 MW，非映射机组 6207.0 MW。
- [数据] `data/fault_scenarios_makeup_basin.csv`：`S1_G30/S1_G34/S1_G38` → `S1_G33/S1_G34`。
- [数据] `data/unit_thermal_hydraulic_params.csv`：baseline/regional 行由 G30/G34/G38 改为 G33（baseline 池面积 2086.4 m² = 1600 × 652/500）与 G34；移除不再建模的第三行。
- [数据] `data/framework_scenarios_v03.csv`：`primary_mw` 600 → 652；S2/S2qs/S4/G1/G2/G4 的策略统一为 `ride_down`，与手稿 Table A2 一致。
- [代码] `src/grid/opf.py`：`COLD_END_BUSES = {33: "G33", 34: "G34"}`；`src/grid/cascade.py`：Bus 33 的基准出力/容量由 600/600 改为官方的 632/652（Pg/Pmax）。
- [代码] `src/scenarios/fault_makeup_basin.py`：`COAL_WR_IDS = ("G33", "G34")`；`tools/export_calibrated_parameters.py` 改为按 `COAL_WR_IDS` 迭代；`tools/calibrate_from_historian.py`、`tools/make_nature_figures.py` 同步标识。
- [测试] `tests/test_repository_consistency.py`：断言改为两台映射机组，并新增官方容量校验（652 + 508，合计 7367.0）。`tests/test_grid_opf.py`：以 Bus 33 重写适应度测试——基准负荷下 Bus 33 全额失能力受 2–3 走廊（rateA 500 MVA）限制，产生约 122 MW 失供，不再是"被 N-1 裕度吸收"。`tests/test_scenarios.py`：regional 包断言改为 G33 行。
- [口径] 级联出口对映射容量不敏感：Bus 33 取 600 / 632 / 652 MW 时，单机跳闸均为 0 条线，双机（33+34）均为 13 条线、2 级。
- [结果] `examples/model_comparison.csv` 的电网段由 G30/1040 MW 改为 G33/652 MW（×1.15 负荷、0–8 h 增量失供电量）：瞬时跳机 4634、线性降额 3266、固定库存 2739、简化水位带 2529、机理 ride-down 2169、机理 hold-load 2163 MWh。瞬时跳机相对机理 ride-down 的高估由约 60% 变为约 53%。同组对照在 G34/508 MW 上为 3560 / 2508 / 2105 / 1943 / 1665 / 1662 MWh，排序不变。
- [结果] `examples/grid_impact_loadlevel.csv`：1.00× 负荷下 Bus 33 全额失能力产生 122.3 MW 增量失供（受 2–3 走廊 rateA 500 MVA 限制），Bus 34 为 7.6 MW；即"单机故障被 N-1 吸收"只在级联（切线）口径成立，在适应度（DC-OPF 约束）口径不成立。
- [结果] `examples/multitimescale_coupling_audit.csv`：事件感知宏步长误差在 G33 路径上为 30 min 0.085%、15 min 0.019%（相对 5 min 参考）。
- [待办] `docs/RESEARCH_FRAMEWORK.md` 在本副本中缺失，`tests/test_repository_consistency.py` 有 4 项契约测试依赖它（本次不新建该文档，避免与正式版本冲突）。
- [口径] 结果报告基准定为**映射机组实际出力**（Bus 33 = 652 MW、Bus 34 = 508 MW）；500 MW 原型（Table 2）只作设计闭合与标定基准，不再作为 Results 的报数机组。受影响的报数：S3a/S3b/S4 稳态出力改为 Bus 33 的 616 / 640 / 640 MW（Bus 34 为 480 / 499 / 499 MW），S1a/C1 的 0–8 h 交付电量改为 Bus 33 的 2748 / 2792 MWh；跳闸时刻与跳闸机制在两类机组上完全相同（容量缩放不改变强度量）。

## v0.6.0-dev — 2026-10-13：Phase B 多应急冷端入口（框架 v0.3）

- [新增] `simulate_cold_end`：统一应急入口（`makeup_interrupt` / `pump_failure` / `wet_bulb_increase` / `none`）；`simulate_makeup_interrupt` 保留为薄封装。
- [新增] 循环流量一阶滞后 `pump_tau_s`（默认 10 s）与湿球一阶滞后 `wet_bulb_tau_s`（默认 900 s）；`quasi_static=True` 关闭滞后作 C2 对照。
- [行为] 循环水接近丧失时，饱和温度驶向高背压保护目标，使泵全退情景能触发 `backpressure_protection`。
- [测试] `tests/test_contingencies_phase_b.py`；进度见 `docs/PHASE_B_SYNTHESIS.md`。
- [新增] `src/grid/cascade.py`：IEEE 39 DC 过载级联（纯标准库）；单机 Bus33 跳闸不级联，双机 33+34 跳闸可级联。  
- [新增] `data/framework_scenarios_v03.csv`、`scenarios/framework_coupling.py`、`examples/run_framework_cascade_coupling.py`：S/G/C 矩阵与冷端→级联摘要 CSV。  
- [结果] G2/G3/G4 双机终态切线 13 条；S1a/S1b 排污策略差约 71 min；S2 vs S2qs 体现动态滞后。  
- [裁定] 部分泵退出 S3 主情景改为 `ride_down`（降额不跳闸：S3a≈567 MW、S3b≈589 MW）；原 hold_load 跳闸保留为 SI `S3a_hold`。  
- [新增] U1 OAT：`examples/run_u1_sensitivity.py` / `u1_sensitivity_summary.csv`；论文 Results 骨架 `docs/PAPER_RESULTS_DRAFT.md`。  
- [文稿] Methods 优化：`docs/METHODS_SECTION_DRAFT.md`、`docs/METHODS_LITERATURE_ANCHORS.md`（Crossref 核验 DOI；Arastou 纠正为 10.1109/jsyst.2021.3122228）；`AppliedEnergy_manuscript_draft.md` §3 已改为 v0.3 多应急+级联叙事。

## v0.5.1 — 2026-10-13：事件感知的多时间尺度冷端—电网交换

- [方法] 冷端动态与电网 DC-OPF 不再共用固定 0.25–0.5 h 快照。冷端保持秒—分钟积分；电网层在 5 min 宏步长上叠加降额起点与停机等事件节点。
- [新增] `src/grid/coupling.py`：`event_aware_time_nodes`、`trajectory_event_times`、`integrate_time_series`。`evaluate_timeseries` 默认 `event_aware=True`，`sample_step_h` 仅作宏步长别名。
- [审计] `examples/run_multitimescale_coupling_audit.py` 与 `examples/multitimescale_coupling_audit.csv`：事件节点始终被包含；相对 1 min 参考，5 min 宏步长的交付电量误差约 0.32%；G30 负荷×1.15 增量失供电量 30 min 相对 5 min 仅差 0.14%。
- [结果] 对照轨迹的电网积分改为事件感知 15 min 宏步长。G30 ×1.15、0–8 h 增量失供电量更新为：瞬时跳机 5148、固定库存 3043、线性降额 3176、简化水位带 2658、机理 ride_down 2039、机理 hold_load 2399 MWh。相对瞬时跳机，机理 ride_down 约低 60%，仅适用于该合成场景。
- [边界] 本文仍不做秒级机电暂态、频率最低点或低频减载；快速 RMS 层仅作为 C/D 档预留。

## v0.5.0 — 2026-10-13：无历史数据条件下的通用机理模型定位

- [定位] 当前研究不以厂级历史数据为前提；正式路线改为文献、标准、厂家典型曲线与守恒闭合锚定的通用参数标定，历史数据拟合降为未来可选本地化。
- [新增] `docs/GENERIC_PARAMETERIZATION.md`：定义 G1–G5 参数证据层级、通用 500 MW 原型标定顺序、敏感性处理和可主张/不可主张结论。
- [数据] `data/parameter_registry.csv` 新增 `generic_anchor_type`、`generic_anchor_note`、`sensitivity_treatment`，逐项说明参数依据与不确定性处理。
- [图件] 新增 `docs/figures/cooling_grid_causal_chain.svg`，显式呈现补水中断→水位/泵/塔/凝汽器/背压/保护→出力轨迹→电网失供的因果链。
- [贡献] 论文主线明确为弥补冷却水故障黑箱表达：冷却故障先形成机组渐进降额/跳机，再在电网裕度不足时转化为失供。

## v0.4.0 — 2026-10-13：合成算例定位与论文证据补强

- [审计] 新增 `docs/DATA_AVAILABILITY_AUDIT.md`：检索 IEEE 39、Kaggle 燃煤机组数据、UCI、EIA/PUDL、NETL、EPRI 与 Zenodo 等公开来源；未获得同一机组的设计包、泵/池/保护资料与完整历史序列，故不拼凑伪厂级标定。
- [定位] 项目统一为“厂级可标定的机理建模框架 + IEEE 39 合成算例”；IEEE 39 机组只称等效机组。
- [新增] `src/cooling/benchmarks.py` 与 `examples/run_model_comparison.py`：瞬时跳机、固定库存时间跳机、预设线性降额、简化水位带与机理双策略对照，并给出 G30 的 0–8 h 增量失供电量。
- [新增] `src/cooling/uncertainty.py` 与 `examples/run_uncertainty_analysis.py`：Latin-hypercube Monte Carlo（N=384）、Morris 筛选、scrambled-Sobol/Saltelli（base N=256）及 bootstrap 区间。
- [图件] `tools/make_figures.py` 新增 `docs/figures/model_comparison.png` 与 `docs/figures/uncertainty_summary.png`。
- [说明] 上述均匀分布是合成场景范围，不是厂级后验；概率结果不得表述为真实机组预测置信区间。

## v0.3.0 — 2026-10-13：厂级可标定运行机理预测模型

### 架构升级
- [新增] `src/cooling/calibration.py` 与 `tools/calibrate_from_historian.py`：参数注册、历史 CSV 装载、Tin/Tout/pb 误差指标、加权目标函数和有界坐标下降拟合。
- [新增] `data/parameter_registry.csv`、`data/historian_data_template.csv`、`docs/CALIBRATION_GUIDE.md`：建立 L0–L3 参数证据等级、标定顺序和独立验证要求。
- [重构] 冷却塔改为设计点标定的 effectiveness/NTU 模型；凝汽器改为 UA–LMTD 模型；TTD 由输入改为输出。
- [重构] 集水池采用面积—水位状态；循环泵默认采用扬程曲线 + NPSH，旧水位带降为 fallback。
- [重构] 动态积分加入热惯性、低水位 SOP、负荷爬坡、技术最小、低真空保护、泵汽蚀及排污隔离政策。
- [新增] `examples/parameter_sensitivity.csv`：500 MW 参考原型的单参数灵敏度（由 `run_sensitivity_demo.py` 可重复生成）。

### 物理纠错
- [修正] 蒸发损失改为热平衡计算 `E = f_evap·Qc/(ρ·h_fg)`，蒸发潜热占 82% 排热；旧 `evap_frac=0.00155` 在设计点仅对应约 7.9% 排热且排热/水量不闭合。
- [修正] 删除旧幽灵设计参数的输入身份；塔性能标定量统一为 `tower_characteristic_mult × design NTU`，凝汽器性能统一为 `condenser_cleanliness × design UA`。
- [修正] `holdup` 改为导出诊断量，不再反向定义池容积/面积。
- [修正] 设计参考点固定、运行湿球独立；天气变热或设备退化可产生真实初期背压/容量损失。
- [修正] 取消循环水流量直接比例裁剪出力，流量经塔—凝汽器—背压链影响出力。

### 标定与文档状态
- 当前无任何真实电厂历史数据，`calibration_status` 全部保持 `reference_template_not_site_measured`。
- `baseline` 仅为历史复现包；`regional` 为气候区代表模板，后续可被逐台厂级参数完全替代。
- [删除追溯] 旧 704 m³ 深池、8 m 水深与 1.2–1.7 m 水位—流量带不再是默认机理；只在历史结果对照和显式 fallback 中理解。

### 参考模板结果变化
- 500 MW 参考原型：补水需求 0.0329 → 0.3375 m³/s（蒸发热平衡纠错约 10 倍量级）；可用库存 704 → 4000 m³（显式池面积/水位）；解析库存时间 6.0 → 3.29 h；动态 `ride_down` 约 5.07 h 仍为泵低水位，`hold_load` 约 4.29 h 泵低水位。

## v0.2.0 — 2026-10-13：运行机理动态化优化（P1–P7）

- 500 MW 原型增加正常/设计水力工况的严格闭合；500 MW 参考背压 7.5591 kPa。
- 动态集成水位、跳机与保护；`ride_down` 5.069 h（旧技术最小口径）、`hold_load` 5.026 h（旧背压保护口径）。
- 新增 baseline/regional 参数包、stand band、潮流再分配、动态导出字段、`grid_impact_loadlevel.csv` 与 `grid_impact_timeseries.csv`。
- 注：v0.2 的水量/池几何/泵—出力链口径已被 v0.3 机理重构取代，数值仅作历史对照。

## v0.1.0 — 2026-10-12：最小闭环

- README、研究框架、500 MW 静态原型、容量缩放、单机补水中断情景、A 档容量表与最小测试。

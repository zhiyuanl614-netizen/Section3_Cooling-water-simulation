# coal-cooling-ieee39 — 文献与标准锚定的通用冷端机理模型 + IEEE 39 合成算例

> IEEE 39 节点合成算例，两台映射等效燃煤湿冷机组（G33/Bus 33 = 652 MW、G34/Bus 34 = 508 MW，容量取 MATPOWER case39 的 Pmax）；
> 主故障谱：**补水中断 / 循环泵全停或部分退出 / 湿球升高**；
> 输出：集水池水位、循环水能力、背压、交付/瞬时出力轨迹、唯一跳闸标签、共模级联与失供影响。
>
> 当前研究不以某厂历史数据为前提：参数由文献、标准、守恒闭合与透明场景范围锚定，重点是把冷却水故障的运行机理显式传播到电网层。

## 当前定位（v0.6.1）

v0.6.1 把电网侧口径统一到 MATPOWER case39 官方数据：映射机组为 Bus 33/34 两台（652 + 508 MW），负荷合计 6254.2 MW，支路 46 条（34 线路 + 12 变压器支路，rateA 480–1800），路径与手稿 §3.2/Table 3 一致。v0.6 阶段（Phase B）补齐**多应急冷端入口 + 事件驱动 DC 级联**：`simulate_cold_end` 统一 `makeup_interrupt` / `pump_failure` / `wet_bulb_increase` / `none`，冷端按秒—分钟积分，电网 DC-OPF 按 5–15 min 宏步长求解并强制对齐降额与停机事件。当前论文路线不是等待厂级拟合，而是用标准/规范、公开文献、厂家典型曲线、热力学与水量守恒闭合标定一套通用参数，并对不确定参数做敏感性和概率场景分析。所有数值仍为通用参考模板，不是某电厂实测标定：

| 模块 | 模型 | 通用锚定的核心参数 |
|---|---|---|
| 汽轮机排热 | 净效率–部分负荷热耗–凝汽器热负荷 | 净效率、热耗修正、凝汽器热负荷分额 |
| 冷却塔 | 设计点标定的 effectiveness/NTU | 塔特性 NTU 倍率、气水比指数、风机/填料状态 |
| 凝汽器 | UA–LMTD，TTD 为输出 | 清洁度、UA、水量指数 |
| 水量 | 热平衡蒸发 + 飘滴 + 盐平衡排污 | 蒸发散热份额、飘滴、浓缩倍率 |
| 集水池 | 面积—水位状态，水位—容积表可选 | 池面积、水位联锁、有效容积 |
| 循环泵 | 泵/系统扬程曲线 + NPSH | 泵曲线、NPSHr、吸入损失、泵组配置 |
| 运行/保护 | 低水位减负荷 SOP、爬坡、技术最小、低真空、泵水位 | SOP 曲线、爬坡率、全部保护定值 |

关键修复（相对 v0.2）：

- 蒸发损失从常数比例改为塔热平衡（蒸发潜热占排热 82% 参考模板）；
- `holdup` 从输入改为导出诊断量，池体采用面积与水位；
- 参考设计点与运行湿球分离，冷却塔/凝汽器老化和高温天气会真实抬升背压；
- 循环水量不再直接按比例裁剪出力，必须通过背压影响；
- 排污隔离、低水位 SOP、负荷爬坡和保护延时全部显式化；
- 所有随附数值标注 `reference_template_not_site_measured`。

完整研究框架见 `docs/RESEARCH_FRAMEWORK.md`，无历史数据条件下的通用参数化方法见 `docs/GENERIC_PARAMETERIZATION.md`，公开数据审计见 `docs/DATA_AVAILABILITY_AUDIT.md`，可选厂级本地化见 `docs/CALIBRATION_GUIDE.md`。

冷却故障到电网失供的显式机理链见 `docs/figures/nature/fig1_causal_chain.svg`。

## 快速开始

```bash
python examples/run_prototype_demo.py      # 500 MW 参考机组设计点
python examples/run_timeseries_demo.py     # 双策略动态轨迹
python examples/run_sensitivity_demo.py    # band 包络、regional 模板与单参数灵敏度
python examples/run_model_comparison.py    # 简化停机假设与机理轨迹对照（电网部分需 pandapower）
python examples/run_uncertainty_analysis.py # Monte Carlo、Morris 与 Sobol（Sobol 建议 scipy）
python -m pytest -q                        # 测试套件（核心库零第三方依赖）
```

电网 B 档需 pandapower；Sobol 全局灵敏度建议安装 scipy（`pip install -e ".[analysis]"`）：

```bash
pip install pandapower
python examples/run_grid_impact_demo.py
```

## 通用参数标定（当前路线）

当前版本按 `docs/GENERIC_PARAMETERIZATION.md` 执行：设计点热/水量闭合 → 文献与标准锚定设备参数 → 通用几何与规程型保护规则 → OAT/Morris/Sobol/Monte Carlo 敏感性传播。参数依据逐项记录在 `data/parameter_registry.csv` 的 `generic_anchor_type`、`generic_anchor_note` 与 `sensitivity_treatment` 列。

## 可选厂级本地化（未来扩展，不是当前前提）

1. 复制 `data/historian_data_template.csv` 并填入电厂历史数据；
2. 在 `data/unit_thermal_hydraulic_params.csv` 中录入图纸、厂家曲线和保护定值；
3. 运行：

```bash
python tools/calibrate_from_historian.py --data path/to/historian.csv --gen-id G33 --package baseline --params tower_characteristic_mult,condenser_cleanliness,evap_heat_fraction --out calibration_result.json
# 审查 fitted_values 并在独立时段验证后，再回写 data/unit_thermal_hydraulic_params.csv 对应机组行；
# 然后用 python tools/export_calibrated_parameters.py --package baseline 重新导出参数表。
```

若未来做单厂本地化，结果必须带验证时段的 Tin/Tout/pb 误差；当前仓库没有真实电厂数据，因此不得把通用模板结果称为厂级实测预测。

## 参考模板结果（500 MW 原型）

| 量 | 参考值 |
|---|---:|
| 净效率 / 凝汽器排热 | 0.38 / 750.5 MWth |
| 循环水量 / 温升 | 15.77 m³/s / 11.420 K |
| 蒸发 + 排污 + 飘滴 = 补水 | 0.2531 + 0.0836 + 0.00079 = 0.3375 m³/s |
| 参考背压 | 7.562 kPa |
| 池面积 / 正常水位 / 跳泵水位 | 1600 m² / 3.5 m / 1.0 m |
| 可用库存 / derived holdup | 4000 m³ / 3.29 h |

baseline 动态参考：`ride_down` 2.56 h 开始降额、5.07 h 泵低水位停机；`hold_load` 4.29 h 泵低水位停机。两数值随模板参数而变，不是实测厂级结论。

## 仓库结构

```
src/cooling/     原型模型、动态集成、水量/泵/保护、新旧容量缩放
src/cooling/calibration.py  参数注册、历史数据指标与有界拟合
src/cooling/benchmarks.py   简化停机假设与机理轨迹对照
src/cooling/uncertainty.py  Monte Carlo、Morris 与 Sobol 全局灵敏度
src/scenarios/   情景加载与单机故障映射
src/grid/        A 档容量损失；B 档 DC-OPF（pandapower）+ 切负荷
tools/calibrate_from_historian.py  电厂历史数据拟合 CLI
tools/export_calibrated_parameters.py  自动导出设计量与动态参考结果
data/parameter_registry.csv  参数来源、拟合边界与可辨识性注册表
docs/            研究框架、数据审计、厂级标定指南、变更日志与图件
tests/           纯标准库 + pytest 断言
```

## 约束

- 仅湿冷循环映射机组 G33（Bus 33）/ G34（Bus 34）；
- 故障谱限定为补水中断、循环泵全停/部分退出、湿球升高；
- 不做直流冷却；电网级联为 DC 同时切除估计，不含缓解措施、AGC 与 AC 电压崩溃；
- IEEE 39 为合成算例，映射机组为等效机组，不是真实电厂机组；
- 不虚构厂内实测数据：新增参数必须标注来源与标定状态。

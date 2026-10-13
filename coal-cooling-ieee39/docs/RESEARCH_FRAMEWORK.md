# 燃煤循环冷却水系统显式建模与电网影响 — 研究框架说明

> **文档用途**：供人类研究者与其他模型/代理读取，统一理解本研究的目标、边界、方法论、数据接口与实现状态。  
> **项目路径**：`coal-cooling-ieee39/`  
> **语言**：中文（术语保留英文键名以便与代码/CSV 对齐）  
> **更新原则**：若情景、机组指派或电网评估深度变更，应同步修订本文档。

---

## 0. 一句话摘要

对 IEEE 39 节点系统中 **3 台燃煤湿冷循环机组**建立 **循环冷却水系统显式（工程标定）模型**，在 **集水池外来补水中断** 故障下，分别计算 **单台机组** 故障时的可用出力 \(P_{\mathrm{avail}}\)，并以此为接口评估对电网运行的影响。

---

## 1. 研究目标

### 1.1 主目标

1. **显式建模**：建立燃煤机组循环冷却水系统（湿冷）的可计算机理模型，核心包含凝汽器侧排热、循环水量、冷却塔进水温度（湿球 + approach）、背压–出力关系，以及 **集水池水量平衡**。
2. **故障映射**：将“外来水源停止向集水池供水（补水中断）”映射为集水池水位下降 → 触及最低运行水位 → 循环泵跳闸 → \(P_{\mathrm{avail}}=0\)。
3. **电网接口**：用 \(P_{\mathrm{avail}}\) 替换故障机组在 IEEE 39 中的出力上限，支撑后续功率平衡 / OPF / 级联等电网影响分析。
4. **无厂内数据条件下的可辩护标定**：参数来自行业标准与工程典型值（EPRI/NETL/IECM 量级，并可对照 GB/T 50102、DL/T 5339），采用 500 MW 原型 + 容量缩放，而非现场辨识。

### 1.2 非目标（明确排除）

- **不做**直流冷却（once-through）系统建模。
- **不做**全网全部发电机的冷却水故障；仅 3 台指定燃煤湿冷机组，且 **每个情景仅单台故障**（不做双机/三机同时故障）。
- **不宣称**还原某一真实电厂的厂内运行数据。
- **当前实现**已完成冷端 + 补水中断情景 → `Pavail`；电网 OPF/级联模块为方法论预留接口，以实现状态为准（见 §7）。

---

## 2. 研究边界与假设

### 2.1 对象系统

| 项目 | 设定 |
|------|------|
| 电网算例 | IEEE 39-bus（MATPOWER `case39` / New England 39-bus） |
| 燃煤湿冷机组 | **G30**（1040 MW）、**G34**（508 MW）、**G38**（865 MW） |
| 冷却类型 | 全部为 `wet_recirc`（循环冷却 / 湿冷） |
| 其余发电机 | 不建循环冷却冷端；`Pmax` 保持算例原值 |
| G39 | 外网互联等效；无厂内冷端 |

### 2.2 故障定义（唯一主故障）

**补水中断（makeup basin interrupt）**：外来水源停止为集水池（collecting basin / sump）供水。

物理链条：

```
外来补水 M_ext → 0
    → 集水池水位因蒸发 E + 排污 B 下降
    → 水位 ≤ Vmin
    → 循环泵无法维持安全运行（跳闸）
    → Pavail = 0
```

### 2.3 关键假设

1. 冷端采用 **准稳态** 工程方程；集水池用 **零维水量平衡**（非三维流场）。
2. 情景默认评估点为 **终端停机状态**（\(t \ge t_{\mathrm{trip}}\)），而非补水刚中断瞬间。
3. 三台机组 **强度参数相同**，仅 **容量相关广延量** 不同（见 §4）。
4. 各机集水池与外来水源相互独立（水源簇 A/B/C 仅用于标注）；每个情景仅有一台机组补水中断。

---

## 3. 方法论总框架

```
┌─────────────────────────────────────────────────────────────┐
│  Layer A  循环冷却水系统显式模型（单机）                        │
│  排热 Qc → 循环水 Qcw → 塔/进水温 → 背压 → 基线 Pavail        │
│  集水池：V0, Vmin, M=E+B, t_trip                            │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Layer B  故障表征                                           │
│  makeup_basin_interrupt → evaluate at basin trip            │
│  故障机组 Pavail=0；健康煤电机组保持设计点 Pavail≈Pmax         │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Layer C  情景组合                                           │
│  仅单台故障：S1_G30 / S1_G34 / S1_G38（共 3 个情景）          │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Layer D  电网影响（接口）                                    │
│  输入：各机 pavail_mw 字典                                    │
│  操作：故障相关机组 Pmax ← Pavail                             │
│  输出：容量损失 / OPF / 切负荷 / 级联（按实现深度）              │
└─────────────────────────────────────────────────────────────┘
```

**方法小节建议结构（学术论文）**：

| 编号 | 标题 |
|------|------|
| 2.1 | 研究框架与问题界定 |
| 2.2 | 循环冷却水系统显式模型 |
| 2.3 | 补水中断故障表征 |
| 2.4 | 工程参数标定与容量缩放 |
| 2.5 | IEEE 39 算例与机组配置 |
| 2.6 | 故障情景设计 |
| 2.7 | 电网影响评估方法 |
| 2.8 | 评价指标与计算流程 |

---

## 4. 冷端模型与参数标定

### 4.1 核心关系（概念式）

- 排热量：\(Q_c \approx P\cdot(1-\eta-\xi_{\mathrm{aux}})/\eta\)
- 循环水：\(Q_{cw}=Q_c/(\rho c_p \Delta T)\)（实现中以设计 \(Q_{cw}\) 与能量平衡求温升）
- 塔侧进水：\(T_{in}\approx T_{wb}+\mathrm{approach}\)
- 凝汽器：\(T_{sat}\approx T_{out}+\mathrm{TTD}\)，\(p_b=p_{sat}(T_{sat})\)
- 出力：相对设计背压的线性降额（工程灵敏度，非完整汽轮机特性曲线）
- 补水：\(M=E+B\)，\(E=\mathrm{evap\_frac}\cdot Q_{cw}\)，\(B=E/(\mathrm{CoC}-1)\)
- 集水池：\(V_0=M\cdot t_{\mathrm{holdup}}\)，\(V_{\min}=f_{\min}V_0\)
- 停机时间：\(t_{\mathrm{trip}}=(V_0-V_{\min})/M\)（补水中断且循环侧损失仍按运行流量计）

### 4.2 标定策略（无厂内数据）

**一级：500 MW 湿冷原型绝对标定**（`WetRecircPrototype500`）

| 键名 | 典型值 | 说明 |
|------|--------|------|
| `p_rated_mw` | 500 | 原型额定功率 |
| `eta_net` | 0.38 | 净效率 |
| `aux_frac` | 0.05 | 厂用电份额代理 |
| `qcw_design_m3s` | 15.77 | 设计循环水量 |
| `approach_design_c` | 5.55 | 逼近度 |
| `twb_design_c` | 20 | 设计湿球温度 |
| `ttd_c` | 3.5 | 凝汽器端差 |
| `pb_design_kpa` | 9.5 | 设计背压 |
| `evap_frac` | 0.00155 | 蒸发占循环水份额 |
| `cycles_of_concentration` | 4 | 浓缩倍率 |
| `basin_holdup_h` | 6 | 集水池有效存水小时数 |
| `basin_vmin_frac` | 0.15 | 最低水位占 \(V_0\) 比例 |

**二级：容量缩放**（`scale_prototype_to_unit`）

\[
s_i=\frac{P_{\max,i}}{500},\quad Q_{cw,i}=s_i\cdot Q_{cw,500}
\]

- **广延量随 \(s_i\) 变**：循环水量、排热量、补水流量、集水池容积  
- **强度量不变**：approach、Twb、TTD、效率、蒸发份额、CoC、holdup 小时、\(V_{\min}\) 比例  
- **结果**：三台机 \(t_{\mathrm{trip}}\) 相同（约 5.1 h），因库存与损失同比例放大  

已导出数值表：`data/calibrated_unit_parameters.csv`

### 4.3 三台机组（当前 Base）

| gen_id | bus | pmax_mw | cooling_type | source_cluster | include_cold_end |
|--------|-----|---------|--------------|----------------|------------------|
| G30 | 30 | 1040 | wet_recirc | A | 1 |
| G34 | 34 | 508 | wet_recirc | B | 1 |
| G38 | 38 | 865 | wet_recirc | C | 1 |

代码常量：`COAL_WR_IDS = ("G30", "G34", "G38")`

---

## 5. 故障情景设计

配置文件：`data/fault_scenarios_makeup_basin.csv`  
故障模式键名：`makeup_basin_interrupt`  
参数键名：`t_eval_h`（空值 = 评估终端停机）

| scenario_id | n_faulted | faulted_units | 含义 |
|-------------|-----------|---------------|------|
| S1_G30 | 1 | G30 | 单机补水中断 |
| S1_G34 | 1 | G34 | 单机补水中断 |
| S1_G38 | 1 | G38 | 单机补水中断 |

**对照工况**：无故障；三台煤电冷端设计点评估（`Pavail ≈ Pmax`）。

**终端情景下容量损失（设计点）**：G30 → 1040 MW；G34 → 508 MW；G38 → 865 MW。

---

## 6. 代码与数据接口（供其他模型调用）

### 6.1 目录结构

```
coal-cooling-ieee39/
  data/
    ieee39_unit_config.csv              # 机组配置
    fault_scenarios_makeup_basin.csv    # 3 个单机补水中断情景
    calibrated_unit_parameters.csv      # 缩放后参数表
  src/
    cooling/
      prototype_500mw.py                # 湿冷原型 + 集水池
      scale.py                          # 容量缩放
      pavail.py                         # Pavail 裁剪
    scenarios/
      fault_makeup_basin.py             # 情景加载与评估
  examples/
    run_prototype_demo.py               # 演示入口
  docs/
    RESEARCH_FRAMEWORK.md               # 本文件
```

### 6.2 推荐读取顺序（给其他模型）

1. 读本文件（目标与边界）  
2. 读 `data/ieee39_unit_config.csv`（谁建模）  
3. 读 `data/fault_scenarios_makeup_basin.csv`（评什么）  
4. 读 `data/calibrated_unit_parameters.csv`（参数数值）  
5. 调用 `src/scenarios/fault_makeup_basin.py` 的 `evaluate_scenario`  

### 6.3 主 API

```text
load_unit_config() -> Dict[gen_id, UnitConfig]
load_scenarios()   -> List[ScenarioSpec]
evaluate_scenario(scenario, units=None) -> dict
```

**`evaluate_scenario` 返回字典（关键字段）**：

| 字段 | 类型 | 含义 |
|------|------|------|
| `scenario_id` | str | 情景 ID |
| `n_faulted` | int | 故障台数（固定为 1） |
| `faulted_units` | list[str] | 故障机组 |
| `capacity_lost_mw` | float | 相对 Pmax 的容量损失 |
| `pavail_mw` | dict[str,float] | 全网 10 机可用出力（电网接口主输入） |
| `unit_details` | dict | 含 `time_to_trip_h`、`basin_volume_m3`、`notes` 等 |
| `description` | str | 情景文字说明 |

### 6.4 电网侧约定接口

```text
输入: pavail_mw[gen_id]
规则: 对 IEEE39 发电机, 若 gen_id 在煤电冷端集合中, 则 Pmax_used = pavail_mw[gen_id]
      其他发电机 Pmax_used = 原算例 Pmax
输出: 由所选电网方法决定（见 §7）
```

运行演示：

```bash
python examples/run_prototype_demo.py
```

---

## 7. 电网影响评估深度（实现状态）

方法论预留四档；**撰写论文 / 继续开发前须固定一档**：

| 档位 | 内容 | 当前状态 |
|------|------|----------|
| A | 仅统计容量损失与功率平衡缺口 | 可由 `capacity_lost_mw` / `pavail_mw` 直接得到 |
| B | OPF + 切负荷 | 未强制实现；接口已备 |
| C | B + 线路过载级联迭代 | 未强制实现 |
| D | C + 多时段调度 | 未强制实现 |

**默认冷端情景输出已支持 A**；若其他模型扩展 B/C/D，应在本文件 §7 更新状态。

---

## 8. 评价指标（建议）

### 8.1 冷端

- \(t_{\mathrm{trip}}\)：补水中断至触及 \(V_{\min}\) 的时间  
- \(V(t)\)：集水池容积轨迹（若做时序）  
- \(P_{\mathrm{avail}}\)：可用出力  
- 背压 \(p_b\)（可选报告）  

### 8.2 电网（随 §7 档位）

- 失供容量 / 切负荷量  
- 过载线路数、级联深度、最大连通子图（若做级联）  

---

## 9. 术语对照表

| 中文 | 英文 / 代码键 | 说明 |
|------|---------------|------|
| 循环冷却 / 湿冷 | wet_recirc | 冷却塔闭式循环 |
| 集水池 | collecting basin / basin | 循环水池 |
| 补水中断 | makeup_basin_interrupt | 外来水源停供 |
| 可用出力 | pavail_mw / Pavail | 冷端约束后的可发功率 |
| 逼近度 | approach | 塔出水相对湿球的温差 |
| 浓缩倍率 | cycles_of_concentration / CoC | 循环水浓缩倍数 |
| 端差 | TTD | 凝汽饱和温度与冷却水出水温差 |

---

## 10. 约束清单（其他模型必须遵守）

1. 冷却类型 **仅** `wet_recirc`；不得重新引入直流冷却作为本研究主线。  
2. 冷端机组 **仅** G30、G34、G38。  
3. 主故障 **仅** 集水池外来补水中断（可扩展参数，但不得静默改故障定义）。  
4. 情景仅为 **单台故障**（S1_G30 / S1_G34 / S1_G38，共 3 个）；加载器拒绝 `n_faulted≠1`。  
5. 无厂内数据时，参数变更须注明来源（标准/文献/敏感性），不得伪称为实测。  
6. 修改机组指派或情景后，同步更新：`ieee39_unit_config.csv`、`fault_scenarios_makeup_basin.csv`、`calibrated_unit_parameters.csv` 与 **本文件**。  

---

## 11. 机器可读元数据

```yaml
project: coal-cooling-ieee39
research_focus: wet_recirculating_cooling_explicit_model_and_grid_impact
grid_case: IEEE39
coal_wet_recirc_units: [G30, G34, G38]
cooling_type: wet_recirc
primary_fault: makeup_basin_interrupt
scenario_count: 3
scenario_scope: single_unit_only
scenario_file: data/fault_scenarios_makeup_basin.csv
unit_config_file: data/ieee39_unit_config.csv
parameter_file: data/calibrated_unit_parameters.csv
prototype_class: WetRecircPrototype500
scaling: Pmax_over_500
default_eval_point: basin_trip_terminal
grid_interface_field: pavail_mw
grid_assessment_tier_implemented: A
grid_assessment_tiers_planned: [B, C, D]
language: zh-CN
```

---

## 12. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-10-12 | 初版：目标、边界、方法框架、3 机补水中断、标定与 API 接口 |
| 2026-10-13 | 情景收窄为仅单台故障（移除双机/三机情景） |

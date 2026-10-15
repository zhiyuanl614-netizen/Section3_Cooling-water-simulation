# 通用参数标定与可选厂级本地化指南

> **当前论文路线**：无历史数据时，采用 `docs/GENERIC_PARAMETERIZATION.md` 的文献与标准锚定方法标定通用版本，并以敏感性分析报告不确定参数的影响。仓库随附的所有数值均为 `reference_template_not_site_measured`，不得称为某电厂实测标定；但这不妨碍其作为通用机理模型使用。
>
> 本指南后半部分的电厂图纸、厂家曲线和历史数据流程，是未来把通用模型本地化到某一台机组时的可选扩展，不是当前研究的前置条件。

## 1. 标定对象与证据等级

| 等级 | 证据 | 可否称为厂级标定 |
|---|---|---|
| L0 | 文献/标准/工程经验代表值 | 否，只能称参考模板 |
| L1 | 电厂设计图纸、设备铭牌、厂家设计曲线 | 可称设计参数标定，仍需运行验证 |
| L2 | 性能试验或稳态历史数据拟合 | 可称稳态厂级标定 |
| L3 | 独立时段验证 + 动态事件/扰动验证 | 可称预测模型厂级标定 |

本项目当前正式采用 **L0 通用参数标定**：以守恒闭合、标准/规范、公开文献和厂家典型曲线锚定通用机组。2026-10-13 的公开数据审计（`docs/DATA_AVAILABILITY_AUDIT.md`）说明公开网络没有完整的单机历史数据包，因此当前论文不以厂级拟合为证据。若未来取得真实电厂图纸、厂家曲线、保护定值和历史数据，可按 L1–L3 做可选本地化与验证。

## 2. 若做厂级本地化，需要取得的资料（当前通用研究不需要）

### 2.1 设计与设备资料

1. 汽轮机热平衡图（THA、75%、50%、40%负荷）与背压修正曲线；
2. 凝汽器设计说明书：设计热负荷、循环水量、进/出口水温、端差、清洁系数、管材/管数/流程；
3. 冷却塔设计与性能曲线：设计湿球、approach、range、循环水量、风机/自然通风状态；
4. 循环水泵厂家曲线：流量—扬程、流量—NPSHr、流量—功率、泵台数与联锁逻辑；
5. 集水池/前池土建图与水位—容积表：池底、正常水位、低水位报警、低低水位跳泵、溢流水位；
6. 保护与运行规程：低真空降负荷曲线、低真空跳机定值及延时、技术最小负荷、补水中断处置、排污隔离要求；
7. 水务资料：补水/循环水电导率或二氧化硅、浓缩倍率、排污与飘滴损失、其他取水/排水支路。

### 2.2 历史数据（DCS/PI）建议字段

`data/historian_data_template.csv` 给出最小模板：

| 字段 | 含义 |
|---|---|
| `p_net_mw` | 机组净出力 |
| `qcw_m3s` | 循环水流量 |
| `twb_c` | 环境湿球温度 |
| `airflow_ratio` | 塔风机/通风状态相对设计值（自然通风塔可置 1 并另记风速） |
| `tin_c` | 冷却塔出口/凝汽器入口水温 |
| `tout_c` | 凝汽器出口水温 |
| `pb_kpa` | 凝汽器绝对压力 |
| `basin_level_m` | 集水池水位 |
| `makeup_m3s` | 补水流量 |
| `notes` | 泵组合、阀门、清洗、胶球、真空泵状态等工况标签 |

建议采样：稳态标定可用 1 min 均值；动态标定至少 1–10 s。标定前必须做时间同步、坏点剔除、仪表零漂检查和稳态筛选。

## 3. 分步标定顺序（不要同时乱拟合全部参数）

### Step 1：几何与定值直接录入（不拟合）

直接录入池面积/水位—容积表、正常/跳泵水位、泵台数、保护定值、技术最小负荷、排污处置规程。这些量不应由优化器“猜”。

### Step 2：设计点热平衡

用设计热平衡校核：

- `eta_net_design`
- `condenser_waste_heat_frac`
- `qcw_design_m3s`
- `approach_design_c`
- `ttd_design_c`
- `pb_ref_kpa`（若厂家给出设计背压，优先直接录入）

验收：设计点 Tin、Tout、Tsat、pb 与设计文件一致；`Pavail = P_rated` 只在参考点成立。

### Step 3：冷却塔稳态拟合

用多负荷、多湿球、多循环水量稳态点拟合：

- `tower_characteristic_mult`
- `tower_ntu_exp`

观测量：Tin、Tout、Twb、Qcw、P。先固定凝汽器参数，避免塔与凝汽器互相补偿。

### Step 4：凝汽器稳态拟合

拟合：

- `condenser_cleanliness`
- `condenser_u_flow_exp`
- 必要时 `condenser_air_partial_pressure_kpa`

观测量：Tout、Tsat/pb、Qcw、Tin、P。验收指标建议：Tin/Tout RMSE ≤0.5 ℃，pb RMSE ≤0.5 kPa（最终门槛由电厂仪表精度决定）。

### Step 5：汽轮机背压修正

优先录入厂家修正曲线并离散化；当前分段线性参数只用于无厂家曲线时的拟合：

- `backpressure_sens_per_kpa`
- `backpressure_sens_high_per_kpa`
- `backpressure_break_dp_kpa`

不得把 0.7%/kPa 写成通用行业定值。

### Step 6：水量与化学平衡

用补水、排污、循环水量和水质数据拟合/核定：

- `evap_heat_fraction`
- `drift_frac`
- `cycles_of_concentration`

检查能量闭合：蒸发潜热占凝汽器排热的比例应与塔型和气象条件相符；检查盐平衡：CoC 应与电导率/二氧化硅比值一致。

### Step 7：泵与水位动态

用泵曲线录入扬程与 NPSHr，再用水位下降、泵电流、出口压力和流量历史校核：

- `pump_design_head_m`
- `pump_static_lift_design_m`
- `pump_shutoff_factor`
- `pump_npshr_design_m`
- `pump_suction_loss_m`
- `pump_eye_elevation_m`

若泵为多台定速泵，应进一步把连续流量模型替换为泵组状态机；当前连续模型只适合作为可标定降阶近似。

### Step 8：动态与保护

用负荷阶跃、循泵切换、真空变化或历史异常事件拟合：

- `tower_tau_s`
- `condenser_tau_s`
- `max_ramp_frac_per_min`

保护定值和延时直接录入，不拟合：

- `p_min_tech_frac`
- `pb_trip_kpa`
- `pb_trip_delay_s`
- `operator_shed_start_level_m`

## 4. 使用仓库拟合工具

先把真实历史数据按模板整理，然后运行：

```bash
python tools/calibrate_from_historian.py \
  --data path/to/historian.csv \
  --gen-id G34 --package baseline \
  --params tower_characteristic_mult,condenser_cleanliness,evap_heat_fraction \
  --out calibration_result.json
```

工具采用有界坐标下降，输出拟合前后 Tin/Tout/pb/补水量的 RMSE、MAE、bias 和目标函数。拟合结果必须：

1. 已纳入机组参数包的量回填到 `data/unit_thermal_hydraulic_params.csv` 的对应机组行；尚未纳入参数包的量保留在标定结果 JSON 中，扩展参数包字段后再回填，不得只改 500 MW 原型默认值冒充单机标定；
2. 把 `calibration_status` 改为实际等级，例如 `site_historian_fit_2026_validation_pending`；
3. 在 `source_note` 中写明数据时段、样本数、仪表来源和验证结果；
4. 用**另一时段**数据验证后，才可改成 `site_calibrated_validated`。

## 5. 验证与接受准则

至少报告：

- 稳态验证：Tin、Tout、pb、补水量、Pavail 的 RMSE/MAE/bias；
- 水量验证：补水量累计误差、水位轨迹误差；
- 动态验证：降额开始时间、停机时间、停机机制；
- 外推检查：高温湿球、低负荷、低循环水量下不得出现非物理温度/压力；
- 不确定性：参数后验或至少局部灵敏度 + 情景包络。

若验证集上 pb RMSE 明显大于仪表误差，或停机机制与规程不一致，应退回分步标定，而不是用一个总修正系数硬凑。

## 6. 当前参考模板的已知限制

- 500 MW 原型参数仍是老式湿冷机组代表值，不是 G33/G34 的真实设计值；
- 三个 IEEE39 发电机是算例中的等效发电机，不等同于三台已辨识的实体机组；
- 泵模型是连续降阶模型，未包含多泵离散启停的完整状态机；
- 冷却塔是 effectiveness/NTU 降阶模型，未做 Merkel 逐层积分和空气侧湿度联立；
- 在取得厂级资料前，所有动态时刻都应表述为“参考模板情景结果”。

# 代码修复与全量重跑报告

**日期**：2026-10-28 15:16–15:40
**范围**：仅代码侧 + 重跑 + 产物重建。手稿 `docs/manuscript_EN.md` **未改动**（按用户指示）。
**备份**：`_backup_prerun_20261028/`（2.4 MB / 113 文件，含不可重建的 fig_R1、fig_R2 与 scenario_master.csv）

---

## 1. 做了什么

### 1.1 修复 1：静态减载按成因分解（核心）

**问题**：`static_grid_shed_mw` 是 `shed_at()` 的**全口径**求和
（`deenergized + collapse + vcls + uvls + ufls`），字段名却暗示是"VCLS + 无源孤岛"。
因此无法回答"VCLS 到底减了多少"，直接导致稿件把 UVLS 继电器减载误读为 VCLS。

**改动**：
- `src/grid/cascade.py`
  - 新增 `shed_cause_category(cause)`：把 `uvls_r2` / `ufls_r1` 归一到 `uvls` / `ufls`。
  - `run_scenario` 内新增 `shed_by_cause` 字典，`shed_at()` 按类别分项累计。
  - 结果字典新增 `"shed_by_cause"` 键。
- `src/coupling/coupled.py`
  - 新增 `static_shed_by_cause` 与 `accum_static_shed(result)`；
    三处累计点（初始运行 L667、`event_target` L783、后续 `final_result` L852）改为调用该函数。
  - 输出 5 个新列：`deenergized_shed_mw`、`collapse_shed_mw`、`vcls_shed_mw`、
    `uvls_shed_mw`、`grid_ufls_shed_mw`。
  - 恒等式：`static_grid_shed_mw = 五项之和`。
- `src/coupling/metrics.py` — `shed_semantics` 改写，明确说明该列是**成因混合、不可读作 VCLS**。

### 1.2 修复 2：`emergency_actions` 的空操作过滤器
`coupled.py:578-580` 原为 `if stage_id > 0 and action in emergency_actions`。
经查 `run_scenario` 的 `stage += 1` 在循环体首，**日志中 stage 恒 ≥ 1**，该过滤是空操作。
它本身不造成漏记（此前 §4.4 我误判为它导致 4 vs 7，实为探测运行所致），
但会误导读者以为初始阶段动作被排除。已改为显式注释 + 去掉无效条件。

### 1.3 修复 3：`metric_audit` 的 K1 重复采集（重跑暴露）
重跑后 `results/K1/scenarios/*/cascade_summary.csv` 被生成，
`metric_audit.collect()` 中"兼容旧版 K1 目录结构"的**回退 glob 无守卫**，
导致 K1 的 6 行被重复读入（审计表 **69 行**而非 63，退化分组出现 `K1-G13, K1-G13`）。
已改为：仅当 K1 汇总表未提供任何行时才回退。

### 1.4 新增：`metric_audit` 检查项 #8
强制校验分项可加性（`|分项和 − static_grid_shed_mw| ≤ 1e-3`），
以及 `H = 0` 时不得有失电/崩溃减载。

### 1.5 新增：减载分解产出
`src/analysis/shed_decomposition.py` →
`results/analysis/shed_decomposition.csv`（逐案）+ `.md`（汇总）。

---

## 2. 全量重跑

`rerun_all.sh`：K1-all → K2 → K3 → K4 → K5 → K6，共 **63 案**，15:16:59 开始、15:29:29 结束（约 12.5 分钟）。

### 2.1 回归结果：既有列**逐位不变**

`src/analysis/verify_rerun_equivalence.py` 逐案逐列比对（排除定义文本列）：

| 项 | 结果 |
|---|---|
| 比对单元格 | 约 5,600 个 |
| **非文本列差异** | **2 处** |
| 新增列 | 5 个 |
| 消失列 | 0 |

2 处差异均为 `impact_class`，且都在 K1：

| 情景 | 旧 | 新 | 原因 |
|---|---|---|---|
| K1-G22 | `N1_voltage_violation_only` | `N0_no_recorded_violation_or_action` | F3 唯一判据下，单纯电压越限不再升类 |
| K1-G27 | `N2_emergency_control_shedding_or_severe_undervoltage` | `N2_emergency_control_shedding` | 同上 |

**这是预期且正确的**：F3 唯一判据此前只在分析脚本层生效，源汇总表仍是 F2b 时代的取值；
必须重跑 63 案才能在源头落地。**该长期遗留项现已解决。**

### 2.2 不变量前后完全一致

| 不变量 | 重跑前 | 重跑后 |
|---|---|---|
| 行数 / 唯一 id | 63 / 63 | 63 / 63 |
| H ≡ F3 | True | True |
| 总 H | 366 | **366** |
| H > 0 | 22 | **22** |
| H > 2 | 14 | **14** |
| 全收敛 | True | True |
| F3 无解分支为空 | True | True |

与主表 `scenario_master.csv` 交叉校验（主表未重新生成）：
**63/63 匹配，`H` / `ufls_shed_mw` / `total_shed_mw` / `f_nadir_hz` 最大差均为 0**。
跳闸事件仍为 **184** 条。

### 2.3 F1/F2 遗留列已从源头消除

| 检查 | 结果 |
|---|---|
| 12 个 F1/F2 遗留列（`n_f1_new`、`n_f2_pf_divergence`…） | **已全部不存在于源表** |

此前 `metric_audit.LEGACY_COLUMNS` 只能在输出口剔除它们；重跑后**源头已无**，
该过滤现为冗余（保留以防旧数据混入）。

---

## 3. 重跑后的减载成因结构（63 案）

| 成因 | 动作案数 | 合计 (MW) | 最大单案 (MW) |
|---|---:|---:|---:|
| `deenergized_shed_mw`（F3 无源路径） | 22 / 63 | 1241.97 | 133.69 |
| `collapse_shed_mw`（F3 无解路径） | **0 / 63** | 0.00 | 0.00 |
| `vcls_shed_mw`（VCLS 二分减载） | **4 / 63** | 122.99 | 58.41 |
| `uvls_shed_mw`（UVLS 继电器） | 50 / 63 | 1453.28 | 78.12 |
| `grid_ufls_shed_mw`（级联内 UFLS） | **0 / 63** | 0.00 | 0.00 |
| `ufls_shed_mw`（频率层，单独报告） | 24 / 63 | 553.44 | — |

可加性最大残差 **1.00e-04**（列为四位小数，属舍入）。

### 3.1 两条独立确认（新证据）
- **`collapse_shed_mw` = 0/63** → 从减载记账层面**独立确认 F3 的无解分支从未发生**。
  此前只能由空的 `unsolvable_buses` 字段推断，现在有两个彼此独立的证据源。
- **`grid_ufls_shed_mw` = 0/63** → 确认耦合运行中 UFLS 以统一负荷缩放施加，
  级联内部 UFLS 分支从不触发，**不存在 UFLS 重复计入**。

### 3.2 VCLS 的 4 个动作案（全含 G1+G2）

| 情景 | VCLS (MW) | UVLS (MW) | 失电 (MW) | 静态合计 (MW) | H |
|---|---:|---:|---:|---:|---:|
| K3-G1-G2-G13 | 19.13 | 40.39 | 95.99 | 155.51 | 24 |
| K3-G1-G2-G22 | 0.51 | 60.19 | 18.89 | 79.59 | 4 |
| K4-G1-G2-G13-G22 | 58.41 | 68.79 | 33.45 | 160.65 | 25 |
| K4-G1-G2-G22-G27 | 44.94 | 62.36 | 47.33 | 154.63 | 28 |

---

## 4. 产物重建

| 产物 | 结果 |
|---|---|
| 7 张表（`build_manuscript_tables.py`） | **全部重建，与备份逐字相同** |
| 13 张图（`build_manuscript_figures.py`，跳过 R1/R2） | 全部重建成功 |
| fig_R1 / fig_R2（不可重建的唯一副本） | **原样保留，未被覆盖** |
| 15 张图的数值内容比对 | **15/15 完全一致**（差异仅为 SVG 时间戳与随机字形 ID） |
| `metric_audit.csv` | 重建，63 行 / 63 唯一 id / 无重复，"未发现不自洽项" |

---

## 5. 审计与校验工具

| 脚本 | 用途 |
|---|---|
| `src/analysis/verify_rerun_equivalence.py` | 重跑前后逐案逐列回归比对 + 分项可加性 |
| `src/analysis/shed_decomposition.py` | 生成减载成因分解表（csv + md） |
| `src/analysis/probe_vcls.py` / `probe_vcls_batch.py` | VCLS 分层探针（权威 / 探测），只写 /tmp |
| `src/analysis/diag_actions.py` | 诊断 `emergency_actions` 漏记来源 |

---

## 6. 待办（手稿侧，本轮未做）

1. **L479**：`VCLS is invoked in 37 of the 63 scenarios` → **4 of 63**。
2. **L479 / L605**：`median 9.6% / max 40.5%` 描述的是 UVLS 主导的 excess，
   需改挂到 UVLS 口径；VCLS 的"modest"定性须在 4 案上重新核校（最大单案 58.41 MW = 系统负荷 30.9%）。
3. **§2.4 L268**：`S_static` 的定义须按代码改写为该五项之和。
4. `static_grid_shed_mw` 命名仍具误导性，建议后续重命名为 `cascade_shed_mw`（会牵动下游）。
5. 此前的挂起项不变：机组数 48→32/15→31/22→18/0→4、§4.6 收敛性整节、
   裕度论据撤下、清单 B 7 处空洞、G1/G2 功能角色重构。

> 分解后的权威数字已沉淀在 `results/analysis/shed_decomposition.md`，
> 改稿时可直接取用，无需再推断。

# 实验修正报告（P0 + P1）

日期：2026-10-28　范围：**仅实验与分析侧，未改动 `docs/manuscript_EN.md`**

---

## 一、根因：一处子串匹配缺陷

稿件核心结论"G1 在场是硬失供的必要条件（48 个含 G1 组合中 22 个失供，
15 个不含 G1 的组合无一失供）"**不成立**。根因为分析脚本中的子串匹配：

```python
# 原代码（build_manuscript_figures.py、build_manuscript_tables.py）
df.units.astype(str).str.contains("G1")     # "G13" 同样含子串 "G1"！
df.units.astype(str).str.contains("G2")     # 更严重：误匹配 G22 / G23 / G27（六机中的四台）
```

误差精确复现：

| 量 | 稿件值 | 实际来源 | 正确值 |
|---|---:|---|---:|
| "含 G1" 组合数 | 48 | \|G1 ∪ G13\| = 32+32−16 | **32** |
| "不含 G1" 组合数 | 15 | 既不含 G1 也不含 G13 = 2⁴−1 | **31** |
| "含 G1" 中 H>0 | 22 | 18（含 G1）+ 4（含 G13 但不含 G1） | **18** |
| "不含 G1" 中 H>0 | 0 | 15 个既不含 G1 也不含 G13 的组合 | **4** |

**4 个反例**（全部 H=2，全部含 G13+G22+G23 核心）：

```
K3-G13-G22-G23          H=2  all_faulted_units_tripped
K4-G13-G22-G23-G27      H=2  hard_service_loss_F3
K4-G2-G13-G22-G23       H=2  all_faulted_units_tripped
K5-G2-G13-G22-G23-G27   H=2  hard_service_loss_F3
```

---

## 二、已修复的缺陷（5 处代码 + 2 处数据）

### 代码

| # | 位置 | 缺陷 | 修复 |
|---|---|---|---|
| 1 | `build_manuscript_tables.py:476` | `str.contains("G1")` | 改用 `has_unit()` |
| 2 | `build_manuscript_figures.py:336`（Fig R5a） | 同上 | 同上 |
| 3 | `build_manuscript_figures.py:1054`（Fig A3） | 同上 | 同上 |
| 4 | `build_manuscript_figures.py:1292`（Fig D1） | `str.contains("G2")` 误匹配 4 台机 | 同上 |
| 5 | `build_manuscript_figures.py:1291` | `str.count("G")+1` 台数多计 1（63/63 全错） | 改用 `n_units()` |

新增 `src/analysis/unitparse.py` 作为机组归属判断的**单一权威实现**，
模块文档记录了本缺陷以免重犯。

### 数据

| # | 位置 | 缺陷 | 修复 |
|---|---|---|---|
| 6 | `_load_trip_events()` | 只读 `other_coldend_trip_events`（首跳**以外**的跳闸），系统性丢失：①每个 K2–K6 情景的首跳机组（在 `initial_trip_events`）；②K1 层全部 6 条（该表无 `scenario_id`） | 两类字段都读；K1 按层目录+初始机组合成 id |
| 7 | `metric_audit.csv` | ①残留 8 个已废止的旧状态列（`n_f2_*`、`n_f1_*`、`f2_*_buses`）；②63 案中有 6 个 K1 案 `scenario_id` 为 NaN，下游连接时静默丢失 | ①在 `--csv` 出口剔除（源表需重跑 63 案才能根除）；②`collect()` 合成 K1 的 id |

**修复 6 的验证**：跳闸事件总数现为 **184**，与稿件 §5.4"all 184 trips were
triggered by the low basin level criterion"完全吻合；记录 G1 跳闸时刻的组合
由 27 增至 **28**（补回 K1-G1 独立断水基准本身）。

---

## 三、修正后的关键统计

完整版见 `results/analysis/combination_structure/corrected_summary.md`。

| 量 | 稿件原值 | 修正值 |
|---|---:|---:|
| 含 G1 组合 / 其中 H>0 | 48 / 22 | **32 / 18** |
| 不含 G1 组合 / 其中 H>0 | 15 / 0 | **31 / 4** |
| 含 G1 子集触发率 K2–K6 | 11.1 / 31.2 / 64.3 / 100 / 100 % | **20.0 / 40.0 / 70.0 / 100 / 100 %** |
| K2 层含 G1 组合数（"nine…remaining eight"） | 9 / 8 | **5 / 4** |
| §4.3 G1 跳闸记录案数 | 27（14 H>0 / 13 H=0） | **28（14 / 14）** |

---

## 四、真正的判别因素：G1 ∧ G2（而非 G1 单独）

### 15 个机组对全检（Bonferroni α = 0.05/15 = 0.0033）

| 机组对 | 严重案 | 精确率 | 召回率 | Fisher p | 校正后 |
|---|---:|---:|---:|---:|---|
| **G1+G2** | **14** | **87.5%** | **100%** | **3.2×10⁻¹²** | **✓ 唯一显著** |
| G1+G27 / G2+G27 | 7 | 43.8% | 50% | 3.3×10⁻² | ✗ |
| 其余 12 对 | 2–6 | ≤37.5% | ≤43% | ≥0.16 | ✗ |

次优对与 G1+G2 相差 **10 个数量级**——不是事后挑数。

### 不是容量的代理（失效容量分档对照）

| 失效容量 | 含 G1+G2 | 不含 G1+G2 |
|---|---|---|
| 150–180 MW | 1 组 → **1 组严重** | 10 组 → **0 组严重** |
| 180–220 MW | 4 组 → **4 组严重** | 7 组 → **0 组严重** |
| 220–300 MW | 8 组 → **8 组严重** | 2 组 → **0 组严重** |

**结论**：16 个含 G1+G2 的组合中 14 个严重，余 2 个被停止规则截尾于 H=2；
**0 个**不含 G1+G2 的组合产生严重失供。排除截尾案后精确率 14/14 = 100%。

### 五个候选解释的判别力

| 候选解释 | 精确率 | 召回率 | 决定性反例 |
|---|---:|---:|---|
| 失效出力达严重案水平 | 37.8% | 100% | `K4-G2-G13-G22-G27` 失 146.5 MW → H=0 |
| 失效容量达严重案水平 | 37.8% | 100% | 同案失 225 MW → H=0 |
| 含中心性最低的 G1 | 43.8% | 100% | G1 介数 0.0025（倒数第二）；中心性最高的 G27 从不致严重失供 |
| 剩余容量不足 | 35.9% | 100% | 39 案不足，仅 14 案严重 |
| **同时含 G1 与 G2** | **87.5%** | **100%** | **无反例** |

### 轻微失供（H=2）是独立机制

8 案 H=2 **全部**含 G13+G22+G23 核心（8/8）；其中 4 案含 G1、4 案不含
（Fisher p = 1.00，与 G1 完全无关）。

---

## 五、新发现：重跑后全部收敛，收敛性限制已过时

源汇总表（`results/K*/tables/*_summary.csv`）现显示 **63 案全部收敛，0 条
奇异/发散告警**，而旧审计表记 3 案共 60/120 条告警。

**这不是告警捕获失效**：`ConvergenceAudit.track()` 经核查仍完整包裹整个仿真
（`coupled.py:441-448`），机制完好。

**成因**：原触发 `MatrixRankWarning` / `RuntimeWarning` 的 VCLS 二分路径，
在 F3 单一判据重构后仅在"孤岛不可解"时进入，而该分支在 63 案中从未触发。

**H 值未变**：3 个原未收敛案（K4-G1-G2-G13-G22 H=25、K4-G2-G13-G22-G27 H=0、
K5-G1-G2-G13-G22-G27 H=29）逐位一致；全 63 案 H 差异为 0，总 H 仍为 366。

**受影响的稿件内容**（待改稿时处理）：
- §2.4.2 "Three did not converge… two are conditional results"
- Table R4（未收敛情景明细）→ 现为空，已改为显示"全部 63 案均收敛"
- Table R4b（排除未收敛案的敏感性）→ 两口径已等同，现只保留一行
- §4.6 "Sensitivity to the non-converged scenarios"
- §5.4 "Solver convergence" 限制条目
- 摘要 "of which two are conditional on unproven solver convergence"

---

## 六、未能重现的 §4.4 容量裕度

稿件称"裕度中位 70.3 MW、最小 0.0、从未为负"，并以此论证"无解分支为空"。
按各候选定义直接计算，**无一能重现**：

| 定义 | 中位 | 最小 | 负值案数 |
|---|---:|---:|---:|
| 剩余容量 − 全网负荷 | −24.2 | −189.2 | 39/63 |
| 有效容量（15% 备用）− 全网负荷 | −24.2 | −189.2 | 39/63 |
| 剩余容量 −（全网负荷 − 失供负荷） | 15.8 | −185.7 | 26/63 |
| 同上，限非截尾案 | 25.8 | −79.2 | 20/57 |
| 上述首项取 max(·,0) | 0.0 | 0.0 | 0/63 |

**唯一不出现负值的定义（取 max(·,0)）中位为 0.0，与 70.3 不符。**

更根本的问题：任何"扣除已失供负荷"的定义都是**循环论证**——失供越多，
尚需供应的负荷越小，裕度越大。故"裕度从不负值"是结果而非原因，不能用它
解释"为什么没发生电压崩溃"。**建议 §4.4 改用已有的干净反事实论证**
（禁用过载跳闸后同一失效集 F3=0），撤下容量裕度论证。

---

## 七、产物清单

| 文件 | 内容 |
|---|---|
| `src/analysis/unitparse.py` | 机组归属判断的单一权威实现（新增） |
| `src/analysis/build_combination_structure.py` | 组合结构分析（新增） |
| `results/analysis/combination_structure/unit_attributes.csv` | 六机属性（电气/冷端/图论） |
| `results/analysis/combination_structure/hypothesis_tests.csv` | 五候选解释 + 反例 |
| `results/analysis/combination_structure/pair_discrimination.csv` | 15 对机组 + Bonferroni |
| `results/analysis/combination_structure/capacity_matched.csv` | 容量匹配对照 |
| `results/analysis/combination_structure/capacity_margin_recheck.csv` | 裕度重现性检验 |
| `results/analysis/combination_structure/corrected_summary.md` | 修正后关键统计 |
| `results/analysis/metric_audit.csv` | 已重生成（63 行、零旧列、全匹配） |
| `results/paper/tables/` | 7 张表已重建（R4 改为"全收敛"、R4b 改为单口径） |
| `results/paper/figures/` | R5 / A3 / D1 已重建（另有 10 张随全量重建） |

**未重建**：Fig R1 / R2——依赖已删除的 `results/reference/coldend_p5/`，
现有 SVG 为唯一副本，须保护。

**未改动**：`docs/manuscript_EN.md`（按指示暂缓）；HTML/DOCX 亦未重建，
以免嵌入新图而正文仍是旧数字、造成内部不一致。

---

## 八、待决断

1. **Table R4 / R4b** 在"全收敛"后已失去原用途：是保留为收敛性审计声明，
   还是从表集中移除（表数 8 → 6）？
2. §4.4 容量裕度段：撤下论证改用反事实，还是给出可重现的新定义？
3. 改稿时机——上述修正涉及摘要、§2.3、§2.4、§4.2–4.6、§5.2、§5.4、§6。

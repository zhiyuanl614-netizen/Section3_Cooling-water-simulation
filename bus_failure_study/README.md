# 冷端补水中断—电网级联研究

本项目以 IEEE30 为唯一电网算例，研究冷却水补水中断引发的机组退出及电网影响。当前包含 K0 无故障基准、K1 六个独立单机补水中断、K2 两机组合 15 案、K3 三机组合 20 案，K4 四机组合 15 案、K5 五机组合 6 案、K6 全六机组合 1 案，以及 P5 独立冷端参考结果。除本文件外，模型和情景说明集中在 `docs/*.md`；旧 HTML/DOCX 报告、重复上传文件和结果目录内重复 README 已清理。

## 当前结果

- **K0：已完成**。本地 IEEE30 数据表与 PYPOWER case30 数组逐项一致；无故障 AC 潮流收敛，负荷 189.20 MW、总发电 191.6438 MW、F1=0。结果在 `results/K0_baseline/`。
- **K1：已完成并复核**。G13、G1、G2、G22、G23、G27 六案独立重启；G22 有 10 条 F1，G27 有 4 条过程 F1/3 条末级 F1并切负荷 2.014 MW；六案最终硬失供均为 0/30。
- **K2：15/15 已运行**。每对机组均在 t=0 同时断水，跳机错时由冷端决定；仅 G1+G2 组合出现硬失供，F3 无源失电 23 条母线（H=23/30）。15 案结果在 `results/K2/`。
- **K3：20/20 已运行**。每组三台机组均在 t=0 同时断水，三台实际跳机错时发生；5/20 案出现 H>0，最大为 G1+G2+G27 的 H=27/30；H 正例均为 F3 无源失电。类别为 N3 5 案、N0 15 案；5 案触发 UFLS。
- **K4：15/15 已运行**。六机选四机全部无序组合，四个补水中断均在 t=0 同时发生，跳闸按冷端/电网动态；9/15 案出现 H>0，最大 H=28/30，类别 N3 9 案、N0 6 案，13 案触发 UFLS。两案按硬失供端点在第四台跳闸前停止，明确按删失记录。K4 首案 PYPOWER 奇异矩阵/除零警告可复现，文件级结果无 NaN/Inf；数值警告需在外部定稿前进一步诊断。详细结果和口径见 `docs/故障情景定义与指标口径.md`。
- **K5：6/6 已运行**。六机选五机全部组合均在 t=0 同时断水；6/6 案因 F3 硬失供停止（H=2 三案、H=29 三案），全部为 N3，5 案触发 UFLS。三案在五台全部跳闸前停止，未跳机组按删失记录。K5 第二案出现 PYPOWER 奇异矩阵/除零警告；输出 CSV 通过有限值审计，但仍需关注内部潮流收敛性。详见情景定义文档。
- **K6 first-H 基线：1/1 已运行**。六台机组补水均在 t=0 同时中断；G13、G23、G2、G22 依次跳闸，随后在 F3 硬失供（B25–B26，H=2）端点停止，G1 与 G27 在该端点未跳闸并按删失处理。该基线输出保留不变。
- **K6 延续：单独完成**。越过 first-H 后，延续运行设有六台目标机组全跳、无在线机组、24 h 和数值失败端点；该次G27于 6.2908 h、G1 于 7.5778 h 跳闸，六台目标机组均跳闸；模型端点 H=30/F3=30，UFLS=52.4877 MW，最低频率57.23438 Hz。运行出现 PYPOWER 奇异矩阵/除零警告，故作为带数值警告的模型 no-source 端点报告，不等同经独立验证的现场 blackout；结果在 `results/K6/continuation/`，不覆盖原基线。
- **UFLS**：时域频率阈值已与静态级联配置分开；K2 为 0/15 案触发，K3 为 5/20，K4 为 13/15，K5 为 5/6，K6 唯一案触发，表明高阶组合进入 UFLS 工作区。
- **P5 冷端参考**：六机同时断水、固定故障前出力的独立冷端序列保留在 `results/reference/coldend_p5/`，不与 K1/K2/K3/K4/K5/K6 耦合结果混用。

## 目录结构

```text
bus_failure_study/
├── README.md                         # 唯一项目总览/入口
├── data/
│   ├── grid/IEEE30/                  # 本地 IEEE30 bus/gen/branch/gencost 数据表
│   └── coldend/                      # 冷端锚点及耦合假设（参数唯一来源）
├── docs/                             # 技术规格书：冷端机理、电网判据、耦合、情景口径
├── scenarios/
│   ├── K0/baseline.csv               # 无故障基准定义
│   ├── K1/single_unit_matrix.csv     # 六个独立单机情景
│   ├── K2/pairwise_matrix.csv        # 15 个双机组合
│   ├── K3/triple_matrix.csv          # 20 个三机组合
│   ├── K4/quadruple_matrix.csv       # 15 个四机组合
│   ├── K5/quintuple_matrix.csv       # 6 个五机组合
│   └── K6/six_unit_matrix.csv        # 1 个全六机组合
├── src/
│   ├── coldend/                      # 冷端内核、机组装配、P5、绘图
│   ├── grid/                         # IEEE30 数据注册、AC级联、VCLS、K0测试
│   ├── coupling/                     # K1/K2/K3/K4/K5/K6 冷端—网侧耦合及批次入口
│   └── analysis/                     # K1–K6 派生数据、图表与报告构建脚本
└── results/
    ├── K0_baseline/                  # 无故障潮流结果（run.sh baseline 重建，不常驻）
    ├── K1/scenarios/<机组>/          # 六案逐案轨迹/摘要
    ├── K1/tables/                    # K1 汇总表
    ├── K2/scenarios/<组合>/          # 15 案逐案轨迹/摘要
    ├── K2/tables/pairwise_summary.csv
    ├── K3/scenarios/<组合>/          # 20 案逐案轨迹/摘要
    ├── K3/tables/triple_summary.csv
    ├── K4/scenarios/<组合>/          # 15 案逐案轨迹/摘要
    ├── K4/tables/quadruple_summary.csv
    ├── K5/scenarios/<组合>/          # 6 案逐案轨迹/摘要
    ├── K5/tables/quintuple_summary.csv
    ├── K6/scenarios/<组合>/          # first-H基线逐案轨迹/摘要
    ├── K6/tables/six_unit_summary.csv
    ├── K6/continuation/              # 独立越过first-H的全六机延续
    ├── analysis/                    # CSV 审计/汇总数据；analysis_report.html 由 build_results_report.py 重建（不常驻）
    ├── analysis/scenario_master.csv # 63案基线统一长表
    ├── analysis/mechanism_*.csv     # 冷端单位级/情景级机理指标
    ├── analysis/group_summary.csv   # K层级汇总
    ├── analysis/figures/            # 由 build_results_report.py 重建（图文件已清理，不常驻）
    ├── paper/figures/               # 由 build_manuscript_figures.py 重建（SVG 单一格式，图文件已清理）
    └── reference/coldend_p5/         # 固定 P0 冷端参考（run.sh coldend-ref 重建，不常驻）
```

## 运行入口

从项目根目录运行。依赖包括 `numpy`、`scipy`、`pandas`、`matplotlib`、`pypower`。

```bash
./run.sh baseline       # 重算 K0 IEEE30 基准潮流
./run.sh coldend-ref    # 重算 P5 冷端参考并绘图
./run.sh K1-G13         # 单跑 G13 K1
./run.sh K1-five        # 单跑 G1/G2/G22/G23/G27 五案
./run.sh K1-all         # 六案批量重跑
./run.sh K2             # 运行全部 15 个双机组合
./run.sh K3             # 运行全部 20 个三机组合
./run.sh K4             # 运行全部 15 个四机组合
./run.sh K5             # 运行全部 6 个五机组合
./run.sh K6             # 运行/重算全六机 first-H 基线
./run.sh K6-full        # 续跑 first-H 后阶段，输出到 results/K6/continuation/
python3 src/analysis/build_results_report.py  # 审计数据并重建分析图表/报告
python3 src/analysis/build_paper_figures.py   # 重建论文 Figure 1–4（不生成未运行的敏感性图）
```

## 手稿构建（manuscript.html / manuscript.docx）

手稿源为 `docs/manuscript_EN.md`，HTML/DOCX 均由脚本从源重建（图以 SVG 内嵌，
不依赖 `results/paper/figures/` 下的图文件）：

```bash
python3 src/publish/build_docx.py                  # 重建 results/paper/manuscript.docx
cd src/publish && npm install                      # 安装 katex / markdown-it（依赖清单见 package.json）
node src/publish/build_html.js                     # 重建 results/paper/manuscript.html
```

> 依赖说明：`build_html.js` 需要 `katex` 与 `markdown-it`，二者通过
> `src/publish/package.json` + `package-lock.json` 声明，`npm install` 即可恢复；
> `node_modules` 已从工作空间清理，不随项目常驻。

批次重跑会更新相应 `results/K1/`、`results/K2/`、`results/K3/`、`results/K4/`、`results/K5/` 或 `results/K6/`，请保留需要留存的人工注记。电网数据从 `data/grid/IEEE30/` 读取，冷端与耦合参数统一由 `data/coldend/` 提供。

## 关键口径

- K2/K3/K4/K5/K6 分别是六机取二/三/四/五/六的全部无序组合；每个组合中的故障机组均在 t=0 同时失去补水，但实际跳机由冷端动态和网侧再调度决定。
- **物理背景**：六台机组位于同一地区，冷端补水取自同一 regional 水源（`unit_anchors.csv: makeup_source=regional_shared_reservoir`）；失效机制为机组自身补水管线故障（`makeup_failure_mode=unit_makeup_line_break`），一台机组故障不影响同区其他机组取水。多机情景表示同时发生的多起独立机组级故障，不是单一水源共因断供。
- 最终母线硬失供：$H=\sum_i\mathbb{1}[F3_i]$，仅无源失电计入。F1/F2a 电压状态与 F2b 数值失败端点均不计入，切负荷也不等于硬失供；N0/N3 是运行状态标签，不替代 H。
- 输出中已不含任何旧失效语义列（`n_bus_failed`、`bus_failure_definition`、F2a/F2b 母线列均已移除）；硬失供只读 `n_bus_hard_failure` / `hard_failure_buses`。
- K1/K2/K3/K4/K5/K6 是规定情景集的确定性仿真，不代表概率估计；爬坡、补水能力/响应等未实测参数属于参考假设。

## 文档索引

- `docs/参考文献库.md`：52 条参考文献与标准的分类清单、引用分布规划与引用纪律。
- `docs/冷端机理模型.md`：冷却塔—凝汽器—水池机理、冷端参数来源及 P5 定位。
- `docs/电网级联与母线失供判定.md`：IEEE30 数据、级联顺序、H=1[F3] 判据（F1/F2a/F2b 仅过程量）及 UFLS 配置说明。
- `docs/冷端-电网耦合模型.md`：K1/K2/K3/K4/K5/K6 的事件编排、同时断水和错时跳机机制。
- `docs/故障情景定义与指标口径.md`：K0/K1/K2/K3/K4/K5/K6 定义、已运行结果表及端点口径。
- `src/analysis/figstyle.py`：学术绘图样式（配色、字体、轴脊、输出格式）。
- `src/analysis/build_manuscript_figures.py`：论文图生成脚本（M1/M2/M5、A1–A3、R1/R2/R3/R5/R6/R7/R8）。
- `paper_design_master.md`：**唯一论文设计总文档**。含论文总体结构、Methods/Chapter 3/Results/Discussion 分章设计、图表总清单、待确认决策点与写作纪律。早期的 `docs/论文研究框架.md`、`docs/论文图表设计.md` 已并入本文档并删除。
- `src/analysis/build_results_report.py`：从 `results/analysis/*.csv` 重建 `analysis_report.html`（63案分析报告，含图；图文件已清理、不常驻）。

## 指标口径（2026-10 修订）

指标定义集中在 `src/coupling/metrics.py`。判据已修订为 `H=1[F3]`（仅无源失电）：原判据中的 F2b 项已移除，F2b 现作为"数值失败端点"仅作披露，F1/F2a 电压状态仅为过程量，不再具有失效语义：

- **`bfi` 改为基于 H**：`bfi_hard`(=H/30)、`bfi_load`(负荷加权)、`h_load_ratio`；旧的 F1 复合口径 `bfi_legacy_composite` 已删除。
- **类别简化为 N0/N3**：`impact_class` 与 H 严格对齐——N3 ⟺ H>0（F3），N0 ⟺ H=0；不再有 F2a 单独触发的 N1/N2。
- **切负荷三量分列**：`total_shed_mw`(跨阶段动作量累计，可超全网负荷)、新增 `shed_peak_mw`、`ufls_shed_mw`；三者均不等于 EENS。
- **时间维度**：新增 `t_first_hard_s`(首次硬失供时刻)、`observation_window_h`(披露删失)。
- **收敛性审计**：`solver_converged` / `n_singular_warnings` 保留。实测 K4-G1-G2-G13-G22 与 K5-G1-G2-G13-G22-G27 捕获 60+54 条奇异/除零告警——H=F3 为拓扑判定不受收敛性影响，但该两案切负荷/频率等次级量为**条件性结果**。

审计：`python3 src/analysis/metric_audit.py`（不自洽时退出码 2）。
详见 `docs/电网级联与母线失供判定.md`。

## 论文图生成

```bash
python3 src/analysis/build_manuscript_figures.py all       # 全部，输出 SVG
python3 src/analysis/build_manuscript_figures.py R3        # 单图
python3 src/analysis/build_manuscript_figures.py all --png # 追加 PNG(300 dpi)
python3 src/analysis/build_manuscript_figures.py all --out /tmp/preview --png
```

样式定义在 `src/analysis/figstyle.py`：Okabe–Ito 色盲安全配色、冗余标记形状、
`svg.fonttype="none"`（矢量文字可编辑）。输出至 `results/paper/figures/`。

**统一为 SVG 单一格式**——矢量无损缩放，期刊可直接编辑文字。
需要位图时加 `--png`（300 dpi），需要 PDF 时加 `--pdf`。

已完成的 13 张图（M1/M2/M5、A1–A3、R1/R2/R3/R5/R6/R7/R8）见
`paper_design_master.md` 第七部分。

## 表格输出

正文表格由 `src/analysis/build_manuscript_tables.py` 生成，
输出至 `results/paper/tables/`（SVG 正式格式 + Markdown 便于正文粘贴），共 8 张：

| 编号 | 文件名 | 内容 |
|---|---|---|
| Table R1 | `table_R1_unit_coldend` | 六机组冷端特征与跳闸时刻 |
| Table R2 | `table_R2_scenario_summary` | K1–K6 分层汇总（含合计行） |
| Table R3 | `table_R3_censored_cases` | 提前终止与截尾情景清单 |
| Table R4 | `table_R4_solver_convergence` | 数值收敛性检验（3 案未收敛）+ 敏感性 |
| Table M2 | `table_M2_parameters` | 耦合侧模型参数与来源（无实测值） |
| Table M3 | `table_M3_bus_criteria` | 母线硬失供判据 F3 → H（仅无源失电） |
| Table A3 | `table_A3_protocol` | 情景枚举协议（t0 并发，63 案） |
| Table D1 | `table_D1_representation` | 固定表达与机理表达能力对比 |

重新生成：`python3 src/analysis/build_manuscript_tables.py`
（可用 `--out DIR` 输出到临时目录预览，指定表名可只生成部分表）

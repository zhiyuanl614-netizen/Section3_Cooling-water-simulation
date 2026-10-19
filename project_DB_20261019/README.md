# 湿式循环冷却冷端应急韧性研究 — 当前版本发布集（v0.7.2）

> **本发布集是当前项目版本（v0.7.2 全面闭环）的自包含交付集：手稿、图片、数据、文档与可独立运行的脚本，全部内容均属当前版本专属，不依赖完整工作树，也不包含任何早期版本内容。**

**正式标题（2026-10-19 作者拍板，方案 B）**

> Mechanistic modeling of wet-recirculating cooling contingencies for cascading failure assessment in power systems

**研究主线**：一条链条（冷端能力损失 → 发电能力轨迹 → 电网后果）、两个出口（S/H 级联与 UAE 充裕度）、一个结论（机制显式、响应条件化的评估优于统一降额/即时跳机假设）。三个研究问题 RQ1–RQ3 自冻结旧稿逐字保留（见 `docs/FINAL_AUDIT.json` 契约记录）。

---

## 目录结构

```
release_v072/
├── README.md                     # 本文件（发布集入口）
├── REPRODUCIBILITY.md            # 可复现性说明（验证层 + 仿真链）
├── requirements.txt              # 锁定依赖清单
├── manuscript/                   # 手稿（Markdown 源稿 + 图文 Word 候选稿）
├── figures/                      # 6 幅图 × 4 格式（PNG/TIFF/SVG/PDF）+ 6 页矢量图册
│   └── qa/                       # 图件 QA 审计体系（panel alignment / collisions / text）
├── data/
│   ├── outputs/                  # 科学门禁与数据（RQ2 重耦合、OPF 六编码迁移等）
│   ├── source_data/              # 图件源数据（fig02–fig06 对应 CSV）
│   └── cache/                    # OPF 仿真前置快照池（552+ 个已验证 DC-OPF 快照）
├── docs/                         # 审计存档与阶段报告
│   ├── FINAL_AUDIT.json          # 完整工作树 16 项审计（2026-10-19，全部 PASS）
│   ├── WORD_AUDIT.json           # Word 结构审计（27 OMML / 19 子小节 / 11 表 / 6 图）
│   ├── PROGRESS_REPORT_ZH.md     # RQ2 重耦合与 RQ1–RQ3 闭环交付报告（中文）
│   ├── FIGURE_CAPTIONS.json      # 图注
│   └── CROSSREF_FULL_METADATA.json  # 59 条参考文献完整元数据
├── code/                         # 模型本体（v0.7.2 完整脚本链的代码支撑）
│   ├── src/cooling|grid|scenarios  # 冷端热模型 / 电网级联与 OPF / 场景参数
│   ├── data/                     # 标定单元参数、IEEE39 配置、故障场景
│   ├── examples/run_thermal_revision_v072.py  # 热模型运行入口
│   ├── pyproject.toml            # 包元数据与可选依赖（grid/opt/analysis/test）
│   └── requirements*.txt         # 依赖清单
└── scripts/                      # 完整脚本链（与工作树字节一致）
    ├── audit_v072_release.py     # 发布集内部一致性审计（含数值门禁与脚本链完备检查）
    ├── build_release.py          # 重建本发布集 ZIP
    └── ...                       # 14 个最终版脚本（见下表）
```

## 完整脚本链（scripts/，与工作树 `rq2_recoupled_v072/` 字节一致）

| 阶段 | 脚本 |
|---|---|
| 模型运行 | `run_thermal_revision_v072.py`（`code/examples/`）、`run_recoupled_rq2.py`（RQ2 热-电重耦合，80 次级联） |
| 数据仿真 | `run_opf_expand_v072.py`（六编码×五负荷×G34 迁移，162 快照）、`test_rq2_recoupled.py`（26 项契约测试） |
| 可视化 | `render_fig04_update.py`（重绘 Figure 4，配合 `figures/qa/` 对齐审计） |
| 文献/整稿 | `finalize_bibliography.py`（59 条文献元数据）、`update_manuscript.py`（整稿同步） |
| 文档转换 | `export_word.py`（Word 导出，需 pandoc + python-docx） |
| 审计 | `audit_rq2_recoupled.py`（工作树 16 项审计）、`audit_v072_release.py`（发布集审计） |
| 打包/标题 | `build_package.py`、`update_title_in_docx.py`、`build_release.py` |
| 留痕 | `retire_dc_v07_from_manifest.py`、`retire_opf_v071_from_manifest.py`、`check_sync_B.py`、`switch_title_B.py` |

## 手稿与图

| 文件 | 说明 |
|---|---|
| `manuscript/Full_manuscript_rq2_rq3_complete_v072.md` | 完整 Markdown 源稿（704 行，首行为正式标题） |
| `manuscript/Full_manuscript_rq2_rq3_complete_v072.docx` | 图文 Word 候选稿（27 条原生 OMML 公式、19 子小节、11 表、6 幅 170 mm 图、59 条完整文献） |
| `figures/fig01–06.{png,tiff,svg,pdf}` | 六幅图四格式（PNG 预览 / TIFF 600 dpi 印刷 / SVG 矢量源 / PDF 矢量） |
| `figures/Figure_atlas_rq2_rq3_v072.pdf` | 6 页图册（含重绘 Figure 4） |

## 数据与证据

- `data/outputs/RQ2_RECOUPLED_GATE.json`：80 次级联求解完整门禁（最大残差 1.07e−11 MW）
- `data/outputs/OPF_EXPAND_V072_GATE.json`：六编码 × 五负荷 × G34 充裕度门禁（162 个新快照）
- `data/outputs/*.csv`：最小门禁、评级敏感性、级联鲁棒性、编码扩展等
- `data/source_data/`：fig02–fig06 的图件源数据（含 fig04 的 68 行重耦合探针）

## 审计与验证状态

| 项 | 状态 |
|---|---|
| 完整工作树审计（存档于 `docs/FINAL_AUDIT.json`） | **16 项全部 PASS**（2026-10-19） |
| 242 个冻结历史文件 | 字节级未变 |
| 本发布集内部审计（`scripts/audit_v072_release.py`） | 版本内部一致性，自包含 |
| 联合契约测试 | 26 项通过（作者原环境） |
| 图件 QA | 6 图对齐、最小字号 ≥5.6 pt、0 FAIL / 0 WARN |
| 外部标定 | `NOT_ESTABLISHED_DATA_GAP`（显式未来工作） |

**投稿前缺口**：作者姓名/单位/资助为结构化占位符待填；最终页面排版校样未完成（`word_final_page_layout_reviewed=false`）。

## 脚本用法

```bash
# 发布集内部审计（纯标准库，无额外依赖；含数值门禁断言）
python scripts/audit_v072_release.py

# 重建本发布集 ZIP（输出至 project/Current_release_v072.zip）
python scripts/build_release.py

# 标题原位替换（幂等；已按方案 B 完成）
python scripts/update_title_in_docx.py
```

**可复现性**：验证层（手稿—图—数据—门禁结论一致性）在发布集内即可复现；科学计算层（80 次级联、162 快照）需完整工作树与锁定依赖，精确路径与版本条件见 `REPRODUCIBILITY.md` 与 `requirements.txt`。

> **与完整工作树的关系**：完整项目工作树（`code/`、`figures/`、`manuscript/revisions/` 版本链、冻结契约与可复现计算脚本）保留在项目根 `project/` 下，用于完整复现与投稿前收束；本发布集为独立、可单独交付的当前版本集。早期版本（v0.7.1 及更早的 dc_v07、opf_v071）已剥离，其历史记录仅存于项目根 `CHANGELOG.md` 与 `WORKSPACE_CLEANUP.md`（历史快照）。

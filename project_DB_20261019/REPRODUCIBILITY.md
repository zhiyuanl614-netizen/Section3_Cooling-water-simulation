# 可复现性说明（v0.7.2 当前版本发布集）

本发布集按"**只含当前版本文件、脚本链完整**"原则构建：手稿、图、数据、文档、**完整脚本链（模型运行 → 数据仿真 → 可视化 → QA）与模型本体代码**全部归档，不含早期版本与冻结历史。
可复现性分三层，各层的复现方法与边界如下。

---

## 第一层：产物级复现（发布集内可直接完成）

给定本发布集，可独立复现**从数据到结论**的全部验证链路，仅需标准库 Python（3.10+）：

```bash
python scripts/audit_v072_release.py
```

该脚本（29 项检查）复现并验证：

| 检查类别 | 覆盖内容 |
|---|---|
| 标题契约 | Markdown 首行 = 正式标题（方案 B）；无 RQ 编号子小节 |
| 手稿结构 | 27 条 display 公式（tag 1–27）、11 表、19 子小节、59 条参考文献 |
| Word 结构 | docx 内 27 个 oMathPara、6 幅嵌入图；媒体哈希与发布图 PNG 逐一匹配 |
| 审计一致性 | `docs/WORD_AUDIT.json` 哈希与手稿一致；`docs/FINAL_AUDIT.json` 16 项 PASS 存档 |
| 图件完备 | 6 图 × 4 格式 + 6 页矢量图册；`figures/qa/` QA 体系齐全 |
| 数据完备 | 8 个 outputs、6 个 source_data、2 个 OPF 前置缓存 |
| **数值门禁** | RQ2 重耦合门禁（8+60+12 行，最大残差 < 1e−7 MW）；OPF 迁移门禁（14+24 行、162 快照）；CSV 行数契约 |
| **脚本链完备** | 分析/仿真/可视化/QA/文献/审计/打包脚本齐全；模型代码三包与标定数据齐全 |

## 第二层：科学计算复现（发布集内含全部输入与脚本，运行需完整工作树结构）

科学数值（80 次级联求解、162 个 DC-OPF 快照、Figure 4 重绘）的产生需要**与工作树相同的目录结构**，原因：最终版计算脚本为保持与工作树**字节一致**，内置了 242 个冻结文件守卫（`PRE_EDIT_STATE.json`）、以 `parents[3]` 定位项目根，并读取版本链缓存。

**发布集已归档的复现输入**：
- 模型本体：`code/src/`（cooling 9 + grid 4 + scenarios 4 个模块，与工作树 `code/src/` 字节一致）
- 标定参数与场景：`code/data/`（7 个 CSV：标定单元参数、IEEE39 配置、故障场景、参数注册表）
- 包元数据与依赖：`code/pyproject.toml`、`code/requirements*.txt`、`requirements.txt`
- OPF 前置快照池：`data/cache/`（opf_snapshot_cache_v072.json 552+ 快照 + additional_dc_snapshots.json）

**运行前置**：
- 依赖（版本锁定）：`pip install -r requirements.txt` → `pandapower==3.5.6`、`numpy==2.3.5`、`scipy==1.17.1`、`pandas==2.3.3`、`matplotlib`
- 目录结构：将 `code/` 与 `scripts/` 放回与工作树一致的相对位置（项目根含 `manuscript/revisions/rq2_recoupled_v072/` 与版本链），或直接在完整工作树内运行（脚本与工作树同字节，结果逐字节可比对发布集 `data/`）

**复现步骤（在完整工作树 `manuscript/revisions/rq2_recoupled_v072/` 内）**：

```bash
python run_thermal_revision_v072.py   # 热模型运行（code/examples/）
python run_recoupled_rq2.py           # RQ2 重耦合：80 次级联求解
python run_opf_expand_v072.py         # 六编码 × 五负荷 × G34 充裕度迁移（162 快照）
python render_fig04_update.py         # 用 68 行重耦合矩阵重绘 Figure 4
python test_rq2_recoupled.py          # 26 项契约测试
```

**受保护性**：计算脚本内置 242 冻结守卫与求解器签名校验——冻结文件被改动或求解器版本不符会拒绝运行；产出写入 `outputs/`、`source_data/`、`figures/`，可与发布集 `data/`、`figures/` 逐字节比对。

## 第三层：图件 QA 复现（`figures/qa/`）

六幅图的对齐、碰撞与文字审计脚本（`audit_panel_alignment.py`、`audit_figure_collisions.py`、`audit_pdf_text.py`、`audit_svg_schematic.py`、`validate_figure.py`）已归档；配合 `render_fig04_update.py` 可复现 Figure 4 的渲染与 QA 判定（需 matplotlib）。

---

## 参考哈希（交付时记录）

- 完整工作树交付包：`RQ2_RQ3_complete_candidate_v072.zip`（86 成员）
- 本发布包：`Current_release_v072.zip`（重建后成员数以交付时为准）

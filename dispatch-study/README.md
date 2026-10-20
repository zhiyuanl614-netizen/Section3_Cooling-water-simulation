# IEEE 30节点 纯AC火电级联 - 极简版

> **当前仅AC潮流**（2026-10-20），6台火电，RTS-96爬坡2.0/1.5 MW/min

## 运行

```bash
pip install -r requirements.txt  # PYPOWER
python src/ac_base_run.py          # 无故障基态AC潮流
python src/ac_cascade_thermal.py   # N-k级联 k=1..6全枚举
```

## 数据

- `data/case30.json`：IEEE30 30母线41支路，Pd189.2MW，6火电机组 $P_{max}$80/80/50/55/30/40，$RU$ 按RTS-96类比
- `results/ac_base_*.csv`：基态AC潮流（$V_m$ 0.96-1.0，无越限）
- `results/ac_thermal_cascade_*.csv`：N-k级联汇总/明细（$N-3$边界，$N-4$必崩）

## 脚本

- `src/ac_base_run.py`：无故障AC潮流
- `src/ac_cascade_thermal.py`：同时等比例爬坡级联引擎（AC过载跳闸/孤岛）

已移除：所有DC相关（dcopf_model/cascade_engine/run_experiment/scenarios）、DC报告、图片、可视化

# Coal wet-recirc × IEEE39 — 集水池补水中断

> **给其他模型/协作者的完整研究框架说明**：[`docs/RESEARCH_FRAMEWORK.md`](docs/RESEARCH_FRAMEWORK.md)

IEEE 39 算例中设定 **3 台燃煤湿冷循环机组**（G30 / G34 / G38），故障为：

> **外来水源停止向集水池（collecting basin）供水（补水中断）**

仅模拟 **单台机组** 故障（共 3 个情景：S1_G30 / S1_G34 / S1_G38）。其余发电机无循环冷却冷端模型。

## 机组

| 机组 | 节点 | Pmax | 冷却 | 水源簇 |
|------|------|------|------|--------|
| G30 | 30 | 1040 MW | 湿冷循环 | A |
| G34 | 34 | 508 MW | 湿冷循环 | B |
| G38 | 38 | 865 MW | 湿冷循环 | C |

## 集水池模型（工程标定）

- 设计补水 \(M = E + B\)（蒸发 + 排污）
- 有效库容 \(V_0 = M \times t_{\mathrm{holdup}}\)（默认 holdup = 6 h）
- 最低运行水位 \(V_{\min} = 0.15 V_0\)
- 外来补水中断后：\(t_{\mathrm{trip}} = (V_0 - V_{\min}) / M\)
- 情景默认评估 **集水池降至 \(V_{\min}\) 后的停机状态**（\(P_{\mathrm{avail}}=0\)）

## 情景（仅单机）

| ID | 故障机组 |
|----|----------|
| S1_G30 | G30 |
| S1_G34 | G34 |
| S1_G38 | G38 |

## 运行

```bash
python examples/run_prototype_demo.py
```

## 文件

```
data/ieee39_unit_config.csv
data/fault_scenarios_makeup_basin.csv
src/cooling/prototype_500mw.py          # 含集水池水量平衡
src/scenarios/fault_makeup_basin.py
```

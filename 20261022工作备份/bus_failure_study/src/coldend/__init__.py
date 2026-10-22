"""
coldend —— 冷却水系统（冷端）机理模型与六机组场景生成
====================================================
    model.py  冷端引擎，与上传的 coldend_makeup_interrupt.py 逐位等价
              （sha256 31736c0baf518e68324c9637f77ae139d4176638bde09c2540ff3e4630488fc7）
    units.py  每台机组一套冷却水系统的装配（参数见 data/coldend/unit_anchors.csv）
    fleet.py  场景生成：退出序列 / 功率轨迹 / 跳机事件流 / 排序稳健性
    plot.py   四张结果图

物理与数值格式未改动；所有机组间差异都在参数层，可替换、可溯源。
"""

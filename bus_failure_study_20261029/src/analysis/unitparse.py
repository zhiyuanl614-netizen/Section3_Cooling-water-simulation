#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""机组集合解析的单一权威实现。

背景（必须保留本说明）
----------------------
分析脚本曾使用 ``units.astype(str).str.contains("G1")`` 判断"组合是否含
G1"。这是**子串匹配**，"G13" 同样含子串 "G1"，于是"含 G1 的组合"实为
"含 G1 或 G13 的组合"：32 + 32 − 16 = 48 组（正确值 32 组）。
同理 ``contains("G2")`` 会误匹配 G22 / G23 / G27（六机中的四台）。

该缺陷曾直接产出稿件中的 "48 / 15 / 22" 三个数字，并据此形成
"G1 在场是硬失供的必要条件" 这一结论。经核验该结论不成立：
排除 G1 的 31 个组合中有 4 个产生硬失供（H = 2）。

因此：**任何机组归属判断都必须经过本模块，禁止再用 str.contains
或 `u in str` 判断机组名。**

用法
----
    from unitparse import has_unit, unit_set, n_units, has_all

    has_unit(df.units, "G1")        # -> bool Series（精确 token 匹配）
    has_all(df.units, {"G1", "G2"}) # -> bool Series
    n_units(df.units)               # -> int Series
    unit_set("G1+G13+G22")          # -> {'G1', 'G13', 'G22'}
"""

from __future__ import annotations

import re
from typing import Iterable, Set, Union

import pandas as pd

#: 六台机组的规范顺序（与稿件 Table 1 一致）
UNITS = ("G1", "G2", "G13", "G22", "G23", "G27")

#: 分隔机组名的字符：scenario_master.csv 用 "+"，部分源用 ";" 或 ","
_SPLIT = re.compile(r"[;,+\s]+")


def unit_set(value) -> Set[str]:
    """把机组名字串解析为集合。空值/NaN 返回空集。

    例：``"G1+G13+G22"`` -> ``{'G1', 'G13', 'G22'}``
    """
    if value is None:
        return set()
    if isinstance(value, (set, frozenset)):
        return set(value)
    if isinstance(value, (list, tuple)):
        return {str(v).strip() for v in value if str(v).strip()}
    s = str(value)
    if s.lower() in ("nan", "none", ""):
        return set()
    return {t for t in _SPLIT.split(s) if t}


def has_all(values: Union[pd.Series, Iterable, str], units: Iterable[str]) -> pd.Series:
    """``values`` 中每一项的机组集合是否**同时**包含 ``units`` 的全部机组。"""
    target = set(units)
    if isinstance(values, str) or not isinstance(values, (pd.Series, list, tuple)):
        values = [values]
    if not isinstance(values, pd.Series):
        values = pd.Series(list(values))
    return values.map(lambda v: target <= unit_set(v))


def has_unit(values: Union[pd.Series, Iterable, str], unit: str) -> pd.Series:
    """``values`` 中每一项的机组集合是否包含 ``unit``（精确匹配）。"""
    return has_all(values, {unit})


def n_units(values: Union[pd.Series, Iterable, str]) -> pd.Series:
    """每一项的机组台数。

    注意：曾写作 ``str.count("G") + 1``，对 63 案全部多计 1 台
    （"G1+G2" 有 2 个 G，台数为 2，而非 3）。此处按集合大小计算。
    """
    if isinstance(values, str) or not isinstance(values, (pd.Series, list, tuple)):
        values = [values]
    if not isinstance(values, pd.Series):
        values = pd.Series(list(values))
    return values.map(lambda v: len(unit_set(v)))


__all__ = ["UNITS", "unit_set", "has_all", "has_unit", "n_units"]

"""流量分位（豊水/平水/渇水）。

仕様: docs/specs/02_scoring.md
"""
import pandas as pd


def flow_at_exceedance(daily_flow: pd.Series, exceedance_days: int) -> float:
    if len(daily_flow) < 365:
        raise ValueError("365日未満のデータでは流量分位を計算できない")
    sorted_desc = daily_flow.sort_values(ascending=False).reset_index(drop=True)
    return float(sorted_desc.iloc[exceedance_days - 1])


def abundant_flow(daily_flow: pd.Series) -> float:
    return flow_at_exceedance(daily_flow, 95)


def normal_flow(daily_flow: pd.Series) -> float:
    return flow_at_exceedance(daily_flow, 185)


def low_flow(daily_flow: pd.Series) -> float:
    return flow_at_exceedance(daily_flow, 275)


def drought_flow(daily_flow: pd.Series) -> float:
    return flow_at_exceedance(daily_flow, 355)

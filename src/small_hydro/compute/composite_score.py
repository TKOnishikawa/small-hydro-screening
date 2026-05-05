"""候補地の合成スコア。

複数の指標を加重和で統合して有望度を1次元のスコアに集約する。

入力カラム:
  output_kw, const_cost_mjpy, annual_kwh
  in_protected_area (bool, optional)
  near_weir (bool, optional)

追加カラム:
  cost_per_kw_mjpy, band_score, cost_score, cf_score, weir_bonus
  composite_score, excluded, rank

仕様: docs/specs/02_scoring.md
"""
import pandas as pd

DEFAULT_WEIGHTS: dict[str, float] = {
    "band": 0.5,
    "cost": 0.3,
    "cf": 0.2,
    "weir_bonus": 0.15,
}


def output_band_score(output_kw: float) -> float:
    """ユーザ要望に従い 50-100kW を最優先、100-150kW を次点。"""
    if pd.isna(output_kw) or output_kw <= 0:
        return 0.0
    if 50 <= output_kw < 100:
        return 1.0
    if 100 <= output_kw < 150:
        return 0.7
    if 30 <= output_kw < 50:
        return 0.4
    if 150 <= output_kw < 300:
        return 0.5
    if 10 <= output_kw < 30:
        return 0.2
    return 0.1


def cost_efficiency_score(cost_mjpy: float, output_kw: float) -> float:
    """5百万円/kW 以下なら 1.0、線形に低下。"""
    if (
        pd.isna(cost_mjpy)
        or pd.isna(output_kw)
        or cost_mjpy <= 0
        or output_kw <= 0
    ):
        return 0.0
    cost_per_kw = cost_mjpy / output_kw
    return min(1.0, 5.0 / cost_per_kw)


def capacity_factor_score(annual_kwh: float, output_kw: float) -> float:
    """設備利用率（年間発電量 / 設備容量×8760時間）。0.5 以上で max。"""
    if (
        pd.isna(annual_kwh)
        or pd.isna(output_kw)
        or annual_kwh <= 0
        or output_kw <= 0
    ):
        return 0.0
    cf = annual_kwh / (output_kw * 8760.0)
    return min(1.0, cf / 0.5)


def compute_composite(
    df: pd.DataFrame,
    weights: dict | None = None,
) -> pd.DataFrame:
    weights = weights or DEFAULT_WEIGHTS
    df = df.copy()

    df["cost_per_kw_mjpy"] = df.apply(
        lambda r: (r["const_cost_mjpy"] / r["output_kw"])
        if r.get("output_kw", 0) > 0 and r.get("const_cost_mjpy", 0) > 0
        else float("nan"),
        axis=1,
    )

    df["band_score"] = df["output_kw"].apply(output_band_score)
    df["cost_score"] = df.apply(
        lambda r: cost_efficiency_score(
            r.get("const_cost_mjpy", 0), r.get("output_kw", 0)
        ),
        axis=1,
    )
    df["cf_score"] = df.apply(
        lambda r: capacity_factor_score(
            r.get("annual_kwh", 0), r.get("output_kw", 0)
        ),
        axis=1,
    )

    near_weir = df["near_weir"] if "near_weir" in df.columns else pd.Series(
        [False] * len(df), index=df.index
    )
    df["weir_bonus"] = near_weir.fillna(False).astype(bool).map(
        lambda x: weights["weir_bonus"] if x else 0.0
    )

    excluded = df["in_protected_area"] if "in_protected_area" in df.columns else (
        pd.Series([False] * len(df), index=df.index)
    )
    df["excluded"] = excluded.fillna(False).astype(bool)

    composite = (
        df["band_score"] * weights["band"]
        + df["cost_score"] * weights["cost"]
        + df["cf_score"] * weights["cf"]
        + df["weir_bonus"]
    )
    df["composite_score"] = composite.where(~df["excluded"], 0.0)
    return df


def rank_candidates(
    df: pd.DataFrame,
    weights: dict | None = None,
    drop_excluded: bool = True,
) -> pd.DataFrame:
    df = compute_composite(df, weights=weights)
    if drop_excluded:
        df = df[~df["excluded"]].copy()
    df = df.sort_values("composite_score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    return df


def filter_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """REPOSデータの明らかな異常値を除外する。"""
    df = df.copy()
    if "output_kw" in df.columns:
        df = df[df["output_kw"].fillna(0) > 0]
    if "const_cost_mjpy" in df.columns:
        df = df[df["const_cost_mjpy"].fillna(0) > 0]
    if "annual_kwh" in df.columns:
        df = df[df["annual_kwh"].fillna(0) > 0]
    return df.reset_index(drop=True)

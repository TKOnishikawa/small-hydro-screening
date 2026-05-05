"""候補地スコアリング。

仕様: docs/specs/02_scoring.md
"""
import pandas as pd

from small_hydro.config import Config


def score_candidates(df: pd.DataFrame, config: Config) -> pd.DataFrame:
    df = df.copy()
    df = df[df["output_kw_drought"] >= config.min_output_kw]
    df = df[df["head_m"] >= config.min_head_m]

    grid_factor = df.get("grid_capacity_factor", pd.Series([0.0] * len(df), index=df.index))
    df["score"] = (
        df["output_kw_drought"] * 0.5
        + df["output_kw_normal"] * 0.3
        + grid_factor * 0.2
    )
    return df.sort_values("score", ascending=False).reset_index(drop=True)

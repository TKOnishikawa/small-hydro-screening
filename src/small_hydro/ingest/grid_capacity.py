"""系統空き容量データ取得。

対象事業者は ADR-003 で確定（Phase 3）。
事業者ごとにフォーマットが異なる:
- 中部電力PG: CSV
- 関西電力送配電: CSV / PDF
- 東京電力PG: CSV
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd

GRID_DIR = Path("data/raw/grid")


def load_grid_capacity(provider: str = "chubu") -> gpd.GeoDataFrame:
    """事業者別の系統空き容量を読み込み。

    Phase 3: ADR-003 確定後に provider 別パーサ実装。
    """
    raise NotImplementedError(
        "Phase 3: ADR-003 で対象事業者を確定後にプロバイダ別パーサ実装"
    )


def load_cached_grid_csv(path: Path) -> pd.DataFrame:
    """汎用CSV読み込み（フォーマット手動調整想定）。"""
    if not path.exists():
        raise FileNotFoundError(f"系統データなし: {path}")
    return pd.read_csv(path)

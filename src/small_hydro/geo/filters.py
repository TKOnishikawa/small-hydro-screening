"""国立公園・保安林の除外フィルタ。

データソース候補:
- 国立公園: 環境省 自然公園データ（要DL）
- 保安林: 林野庁 J-FAS / 都道府県オープンデータ

レイヤは `data/raw/regulatory/{layer}.shp` 配下に配置想定。
存在しないレイヤは無視（フィルタ無効化）。
"""
from pathlib import Path

import geopandas as gpd

REGULATORY_DIR = Path("data/raw/regulatory")
DEFAULT_LAYERS: tuple[str, ...] = ("national_park", "protected_forest")


def filter_by_regulations(
    candidates: gpd.GeoDataFrame,
    exclude_layers: tuple[str, ...] = DEFAULT_LAYERS,
) -> gpd.GeoDataFrame:
    result = candidates.copy()

    for layer_name in exclude_layers:
        layer_path = REGULATORY_DIR / f"{layer_name}.shp"
        if not layer_path.exists():
            continue

        regulated = gpd.read_file(layer_path).to_crs(result.crs)
        joined = gpd.sjoin(result, regulated, predicate="within", how="left")
        result = joined[joined["index_right"].isna()]
        drop_cols = [c for c in result.columns if c.endswith("_right") or c == "index_right"]
        result = result.drop(columns=drop_cols)
        result = gpd.GeoDataFrame(result, geometry="geometry", crs=candidates.crs)

    return result

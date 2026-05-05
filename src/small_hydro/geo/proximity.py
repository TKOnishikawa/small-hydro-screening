"""空間近接性 / 包含判定ヘルパ。"""
import geopandas as gpd

DEFAULT_METRIC_CRS = "EPSG:3857"


def add_min_distance_m(
    candidates: gpd.GeoDataFrame,
    layer: gpd.GeoDataFrame,
    column: str,
    metric_crs: str = DEFAULT_METRIC_CRS,
) -> gpd.GeoDataFrame:
    """各候補から layer のいずれかへの最短距離(m)を column に追加。"""
    result = candidates.copy()
    if layer.empty:
        result[column] = float("inf")
        return result

    cands_m = candidates.to_crs(metric_crs)
    layer_m = layer.to_crs(metric_crs)
    union = layer_m.geometry.unary_union
    result[column] = cands_m.geometry.distance(union)
    return result


def add_within_flag(
    candidates: gpd.GeoDataFrame,
    layer: gpd.GeoDataFrame,
    column: str,
) -> gpd.GeoDataFrame:
    """各候補が layer のいずれかと交差するか bool で column に追加。"""
    result = candidates.copy()
    if layer.empty:
        result[column] = False
        return result
    union = layer.geometry.unary_union
    result[column] = candidates.geometry.intersects(union)
    return result


def add_proximity_flag(
    candidates: gpd.GeoDataFrame,
    layer: gpd.GeoDataFrame,
    column: str,
    threshold_m: float,
    metric_crs: str = DEFAULT_METRIC_CRS,
) -> gpd.GeoDataFrame:
    """layer から threshold_m 以内に存在するか bool で column に追加。"""
    result = candidates.copy()
    if layer.empty:
        result[column] = False
        return result

    cands_m = candidates.to_crs(metric_crs)
    layer_m = layer.to_crs(metric_crs)
    union = layer_m.geometry.unary_union
    result[column] = cands_m.geometry.distance(union) <= threshold_m
    return result

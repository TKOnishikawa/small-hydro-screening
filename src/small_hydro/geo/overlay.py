"""空間オーバーレイ・距離計算ヘルパ。"""
import geopandas as gpd


def add_distance_to_layer(
    candidates: gpd.GeoDataFrame,
    layer: gpd.GeoDataFrame,
    column: str,
) -> gpd.GeoDataFrame:
    """各候補から layer の最寄り点までの距離(km)を column に追加。

    内部で Web Mercator (EPSG:3857) に投影してメートル計算。
    日本の緯度では数%の誤差を許容する想定。厳密な距離が必要な場合は
    平面直角座標系に切り替える。
    """
    result = candidates.copy()

    if layer.empty:
        result[column] = float("inf")
        return result

    cands_m = candidates.to_crs("EPSG:3857")
    layer_m = layer.to_crs("EPSG:3857")
    union = layer_m.geometry.unary_union
    result[column] = cands_m.geometry.distance(union) / 1000.0
    return result

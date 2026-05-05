"""OSM 堰候補に対して標高差を推定する。

各堰の周囲4方位（N/S/E/W）に offset_m メートル離れた点で標高をサンプリングし、
max - min を「落差プロキシ」として返す。

注意:
- 物理的に正確な「有効落差」ではない。スクリーニング用の粗い指標
- 真の有効落差は河川経路に沿った上流・下流の elevation 差で決まる
- v2 では河川ジオメトリ（waterway= line）を併用して改善予定
"""
import math

from small_hydro.config import Config
from small_hydro.ingest.gsi_elevation import fetch_elevations

EARTH_RADIUS_M = 6_378_137.0


def offset_point(
    lat: float, lon: float, dlat_m: float, dlon_m: float
) -> tuple[float, float]:
    """緯度経度を指定メートルだけずらす（小範囲近似）。"""
    new_lat = lat + (dlat_m / EARTH_RADIUS_M) * (180.0 / math.pi)
    new_lon = lon + (
        dlon_m / (EARTH_RADIUS_M * math.cos(math.radians(lat)))
    ) * (180.0 / math.pi)
    return new_lat, new_lon


def estimate_head_proxy(
    lat: float, lon: float, config: Config, offset_m: float = 50.0
) -> tuple[float, list[float | None]]:
    """4方位の標高サンプリングで落差プロキシを返す。

    Returns:
        (head_proxy_m, [N, S, E, W elevations])
    """
    coords = []
    for dlat_m, dlon_m in [(offset_m, 0), (-offset_m, 0), (0, offset_m), (0, -offset_m)]:
        plat, plon = offset_point(lat, lon, dlat_m, dlon_m)
        coords.append((plat, plon))

    results = fetch_elevations(coords, config)
    samples = [r[0] for r in results]

    valid = [e for e in samples if e is not None]
    if len(valid) < 2:
        return 0.0, samples
    return max(valid) - min(valid), samples

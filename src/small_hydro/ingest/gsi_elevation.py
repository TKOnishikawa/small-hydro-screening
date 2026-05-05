"""国土地理院 標高API クライアント。

サーバ負荷規約遵守のためレート制御を内蔵。
"""
import time

import requests

from small_hydro.config import Config


def fetch_elevation(
    lat: float, lon: float, config: Config
) -> tuple[float | None, str | None]:
    """指定座標の標高を取得。エラー or 海域時は (None, None)。"""
    params = {"lat": lat, "lon": lon, "outtype": "JSON"}
    response = requests.get(config.gsi_api_base_url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    elevation = data.get("elevation")
    if elevation == "-----" or elevation is None:
        return None, None
    return float(elevation), data.get("hsrc")


def fetch_elevations(
    coords: list[tuple[float, float]], config: Config
) -> list[tuple[float | None, str | None]]:
    """複数座標を順次取得。レート制御は config に従う。"""
    results = []
    for lat, lon in coords:
        results.append(fetch_elevation(lat, lon, config))
        time.sleep(config.gsi_api_rate_limit_sec)
    return results

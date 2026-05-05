"""OpenStreetMap Overpass API クライアント。

waterway=weir / boundary=national_park 等を取得する。
公開Overpassインスタンスは過負荷で 504/429 が頻発するため、
ディスクキャッシュ + 指数バックオフ再試行で安定化させる。
"""
import hashlib
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "small-hydro-screening/0.1.0"
OSM_CACHE_DIR = Path("data/raw/osm")


def _bbox_cache_key(bbox: tuple[float, float, float, float]) -> str:
    s = f"{bbox[0]:.4f}_{bbox[1]:.4f}_{bbox[2]:.4f}_{bbox[3]:.4f}"
    return hashlib.md5(s.encode()).hexdigest()[:10]


def _retry_overpass(
    query: str, timeout: int = 60, max_retries: int = 3
) -> requests.Response:
    """指数バックオフ付きでOverpassに問合せ。"""
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = requests.get(
                OVERPASS_URL,
                params={"data": query},
                headers={"User-Agent": USER_AGENT},
                timeout=timeout * 2,
            )
            response.raise_for_status()
            return response
        except (requests.HTTPError, requests.Timeout, requests.ConnectionError) as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = 2**attempt * 5
                time.sleep(wait)
    if last_error is not None:
        raise last_error
    raise RuntimeError("unreachable")


def _build_weir_query(bbox: tuple[float, float, float, float], timeout: int = 60) -> str:
    minlon, minlat, maxlon, maxlat = bbox
    return (
        f"[out:json][timeout:{timeout}];"
        f"node[waterway=weir]({minlat},{minlon},{maxlat},{maxlon});"
        f"out body;"
    )


def _build_protected_query(
    bbox: tuple[float, float, float, float], timeout: int = 180
) -> str:
    minlon, minlat, maxlon, maxlat = bbox
    return (
        f"[out:json][timeout:{timeout}];"
        f"("
        f"relation[boundary=national_park]({minlat},{minlon},{maxlat},{maxlon});"
        f"way[boundary=national_park]({minlat},{minlon},{maxlat},{maxlon});"
        f"relation[boundary=protected_area]({minlat},{minlon},{maxlat},{maxlon});"
        f");"
        f"out geom;"
    )


def _empty_weirs() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"osm_id": [], "river_name": [], "lat": [], "lon": []},
        geometry=gpd.GeoSeries([], crs="EPSG:4326"),
        crs="EPSG:4326",
    )


def _empty_protected() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"osm_id": [], "name": [], "boundary": []},
        geometry=gpd.GeoSeries([], crs="EPSG:4326"),
        crs="EPSG:4326",
    )


def fetch_weirs(
    bbox: tuple[float, float, float, float],
    timeout: int = 60,
    use_cache: bool = True,
    max_retries: int = 3,
) -> gpd.GeoDataFrame:
    cache_path = OSM_CACHE_DIR / f"weirs_{_bbox_cache_key(bbox)}.geojson"
    if use_cache and cache_path.exists():
        return gpd.read_file(cache_path)

    response = _retry_overpass(
        _build_weir_query(bbox, timeout=timeout),
        timeout=timeout,
        max_retries=max_retries,
    )
    elements = response.json().get("elements", [])
    if not elements:
        gdf = _empty_weirs()
    else:
        rows = []
        for el in elements:
            tags = el.get("tags", {})
            rows.append(
                {
                    "osm_id": el["id"],
                    "lat": el["lat"],
                    "lon": el["lon"],
                    "river_name": tags.get("name") or tags.get("waterway:name"),
                }
            )
        df = pd.DataFrame(rows)
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df["lon"], df["lat"]),
            crs="EPSG:4326",
        )

    if use_cache and not gdf.empty:
        OSM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        gdf.to_file(cache_path, driver="GeoJSON")
    return gdf


def fetch_protected_areas(
    bbox: tuple[float, float, float, float],
    timeout: int = 180,
    use_cache: bool = True,
    max_retries: int = 3,
) -> gpd.GeoDataFrame:
    """国立公園・国定公園・自然公園を取得（osm2geojsonでポリゴン化）。"""
    import osm2geojson

    cache_path = OSM_CACHE_DIR / f"protected_{_bbox_cache_key(bbox)}.geojson"
    if use_cache and cache_path.exists():
        return gpd.read_file(cache_path)

    response = _retry_overpass(
        _build_protected_query(bbox, timeout=timeout),
        timeout=timeout,
        max_retries=max_retries,
    )
    overpass_data = response.json()
    geojson = osm2geojson.json2geojson(overpass_data)

    features = geojson.get("features", [])
    if not features:
        gdf = _empty_protected()
    else:
        rows = []
        geoms = []
        for f in features:
            geom = f.get("geometry")
            if not geom:
                continue
            props = f.get("properties", {})
            tags = props.get("tags", {})
            rows.append(
                {
                    "osm_id": props.get("id"),
                    "name": tags.get("name"),
                    "boundary": tags.get("boundary"),
                    "protect_class": tags.get("protect_class"),
                }
            )
            geoms.append(geom)

        if not rows:
            gdf = _empty_protected()
        else:
            from shapely.geometry import shape

            shapely_geoms = [shape(g) for g in geoms]
            gdf = gpd.GeoDataFrame(
                pd.DataFrame(rows), geometry=shapely_geoms, crs="EPSG:4326"
            )
            gdf = gdf[
                gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
            ].reset_index(drop=True)

    if use_cache and not gdf.empty:
        OSM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        gdf.to_file(cache_path, driver="GeoJSON")
    return gdf

"""環境省 REPOS データローダー。

`data/raw/repos/` 配下の Shapefile or CSV を自動検出して GeoDataFrame に変換。
カラム名のゆらぎ（日本語/英語/略号）は COLUMN_ALIASES で吸収。

REPOS R4 (令和4年度) 河川水力ポテンシャルのカラム:
- LINKID: 区間ID
- HYDRO_IC: 設備容量 (kW) → output_kw
- HYDRO_PG: 年間発電量 (kWh) → annual_kwh
- CONST_COST: 建設コスト (百万円) → const_cost_mjpy
- PREFECTURE / MUNICIPAL / MUNIC_CODE: 行政区域
- CRS: EPSG:4612 (JGD2000) → 4326 へ再投影

`_p` (Point) と `_l` (LineString) の両方が存在する場合は `_p` を優先。
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd

REPOS_DIR = Path("data/raw/repos")

COLUMN_ALIASES: dict[str, list[str]] = {
    "river_name": ["河川名", "河川", "RIVER", "river", "RiverName"],
    "head_m": ["有効落差", "落差", "落差(m)", "H", "head", "HEAD_M"],
    "flow_m3s": ["流量", "流量(m3/s)", "Q", "flow", "FLOW_M3S"],
    "output_kw": [
        "HYDRO_IC",
        "概算発電出力",
        "想定出力",
        "設備容量",
        "出力(kW)",
        "出力",
        "P",
        "OUTPUT_KW",
    ],
    "annual_kwh": ["HYDRO_PG", "年間発電量", "年間kWh"],
    "const_cost_mjpy": ["CONST_COST", "建設コスト", "建設費"],
    "prefecture": ["PREFECTURE", "都道府県"],
    "municipality": ["MUNICIPAL", "市区町村"],
    "munic_code": ["MUNIC_CODE", "市区町村コード"],
    "linkid": ["LINKID", "link_id"],
    "intake_lat": ["取水緯度", "上流緯度", "INTAKE_LAT", "lat_in"],
    "intake_lon": ["取水経度", "上流経度", "INTAKE_LON", "lon_in"],
    "outflow_lat": ["放水緯度", "下流緯度", "OUTFLOW_LAT", "lat_out"],
    "outflow_lon": ["放水経度", "下流経度", "OUTFLOW_LON", "lon_out"],
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns and alias != canonical:
                rename_map[alias] = canonical
                break
    return df.rename(columns=rename_map)


def _read_csv_robust(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "cp932", "shift_jis", "utf-8"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(
        "utf-8-sig/cp932/shift_jis/utf-8 全て失敗", b"", 0, 0, str(path)
    )


def _prefer_point_shapefile(shapefiles: list[Path]) -> list[Path]:
    """`_p` / `_point` 末尾（Point）を優先するソート。"""
    return sorted(
        shapefiles,
        key=lambda p: (0 if p.stem.endswith(("_p", "_point", "_pt")) else 1, p.name),
    )


def load_repos(
    path: Path | None = None,
    bbox: tuple[float, float, float, float] | None = None,
) -> gpd.GeoDataFrame:
    """REPOSデータを読み込む。

    Args:
        path: REPOSディレクトリ。未指定なら REPOS_DIR
        bbox: (minlon, minlat, maxlon, maxlat) で空間フィルタ。未指定なら全件
    """
    path = path or REPOS_DIR
    if not path.exists():
        raise FileNotFoundError(
            f"{path} が存在しない。REPOSサイト( https://www.renewable-energy-potential.env.go.jp/RePos/ )"
            f"からデータDLし配置してください"
        )

    shapefiles = list(path.glob("**/*.shp"))
    if shapefiles:
        chosen = _prefer_point_shapefile(shapefiles)[0]
        gdf = gpd.read_file(chosen)
        gdf = _normalize_columns(gdf)
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        gdf = gdf.to_crs("EPSG:4326")
        if bbox is not None:
            minlon, minlat, maxlon, maxlat = bbox
            gdf = gdf.cx[minlon:maxlon, minlat:maxlat].reset_index(drop=True)
        return gdf

    csvs = sorted(path.glob("**/*.csv"))
    if csvs:
        df = _read_csv_robust(csvs[0])
        df = _normalize_columns(df)
        if "intake_lat" in df.columns and "intake_lon" in df.columns:
            geometry = gpd.points_from_xy(df["intake_lon"], df["intake_lat"])
            gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
        else:
            gdf = gpd.GeoDataFrame(df, geometry=gpd.GeoSeries(), crs="EPSG:4326")
        if bbox is not None:
            minlon, minlat, maxlon, maxlat = bbox
            gdf = gdf.cx[minlon:maxlon, minlat:maxlat].reset_index(drop=True)
        return gdf

    raise FileNotFoundError(f"{path} 配下に Shapefile も CSV も見つからない")

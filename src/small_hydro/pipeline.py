"""パイプラインオーケストレーター。

Phase 0: REPOS 読込 → 出力カラム補完 → スコアリング → CSV/GeoJSON 出力
Phase 1.5: OSM Overpass + 標高API ベースの REPOS不要パイプライン
Phase 2: REPOS + OSM(堰/規制) を統合した合成スコアによるエンリッチドスクリーニング
"""
from pathlib import Path

import geopandas as gpd
from tqdm import tqdm

from small_hydro.compute.composite_score import filter_anomalies, rank_candidates
from small_hydro.compute.head_estimation import estimate_head_proxy
from small_hydro.compute.output import theoretical_output_kw
from small_hydro.compute.scoring import score_candidates
from small_hydro.config import Config, load_config
from small_hydro.geo.proximity import add_proximity_flag, add_within_flag
from small_hydro.ingest.osm_overpass import fetch_protected_areas, fetch_weirs
from small_hydro.ingest.repos import load_repos

OUTPUT_DIR = Path("output")

ASSUMED_FLOW_M3S = 0.3
WEIR_PROXIMITY_THRESHOLD_M = 200.0


def enrich_with_output(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """流量・落差から想定出力カラムを補完。"""
    df = gdf.copy()

    if "output_kw" not in df.columns:
        if "flow_m3s" not in df.columns or "head_m" not in df.columns:
            raise ValueError(
                "output_kw も flow_m3s/head_m も無い: 出力計算不可。カラム構成を確認"
            )
        df["output_kw"] = [
            theoretical_output_kw(q, h)
            for q, h in zip(df["flow_m3s"], df["head_m"])
        ]

    if "output_kw_drought" not in df.columns:
        df["output_kw_drought"] = df["output_kw"]
    if "output_kw_normal" not in df.columns:
        df["output_kw_normal"] = df["output_kw"]

    return df


def run_screening(config: Config | None = None) -> gpd.GeoDataFrame:
    """REPOS ベースのスクリーニング（Phase 0）。"""
    config = config or load_config()
    gdf = load_repos(bbox=config.target_bbox)
    gdf = enrich_with_output(gdf)
    return score_candidates(gdf, config)


def run_screening_osm(
    config: Config | None = None,
    limit: int | None = None,
    offset_m: float = 50.0,
    assumed_flow_m3s: float = ASSUMED_FLOW_M3S,
) -> gpd.GeoDataFrame:
    """OSM + 標高API ベースのスクリーニング（Phase 1.5）。"""
    config = config or load_config()
    weirs = fetch_weirs(config.target_bbox)
    if weirs.empty:
        return weirs
    if limit is not None:
        weirs = weirs.head(limit).copy()

    heads = []
    for _, row in tqdm(weirs.iterrows(), total=len(weirs), desc="elev sampling"):
        head, _ = estimate_head_proxy(
            row["lat"], row["lon"], config, offset_m=offset_m
        )
        heads.append(head)
    weirs["head_m"] = heads
    weirs["flow_m3s"] = assumed_flow_m3s
    weirs = enrich_with_output(weirs)
    return score_candidates(weirs, config)


def run_screening_enriched(
    config: Config | None = None,
    skip_protected_areas: bool = False,
    skip_weir_proximity: bool = False,
) -> gpd.GeoDataFrame:
    """REPOS + OSM(堰近接 + 国立公園除外) + 設備利用率 で合成スコア算出（Phase 2）。"""
    config = config or load_config()

    gdf = load_repos(bbox=config.target_bbox)
    gdf = filter_anomalies(gdf)

    if not skip_protected_areas:
        protected = fetch_protected_areas(config.target_bbox)
        gdf = add_within_flag(gdf, protected, column="in_protected_area")
    else:
        gdf["in_protected_area"] = False

    if not skip_weir_proximity:
        weirs = fetch_weirs(config.target_bbox)
        gdf = add_proximity_flag(
            gdf,
            weirs,
            column="near_weir",
            threshold_m=WEIR_PROXIMITY_THRESHOLD_M,
        )
    else:
        gdf["near_weir"] = False

    ranked = rank_candidates(gdf)
    return ranked


def export_results(gdf: gpd.GeoDataFrame, fmt: str = "geojson") -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"candidates.{fmt}"

    if fmt == "geojson":
        gdf.to_file(out_path, driver="GeoJSON")
    elif fmt == "csv":
        df = gdf.drop(columns="geometry") if "geometry" in gdf.columns else gdf
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
    else:
        raise ValueError(f"未対応のフォーマット: {fmt}")

    return out_path

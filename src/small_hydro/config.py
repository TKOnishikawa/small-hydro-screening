import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    target_bbox: tuple[float, float, float, float]
    gsi_api_rate_limit_sec: float
    gsi_api_base_url: str
    min_output_kw: float
    min_head_m: float


def load_config() -> Config:
    bbox_raw = os.environ.get("TARGET_BBOX")
    if not bbox_raw:
        raise ValueError("TARGET_BBOX 未設定。.env を確認のこと")

    bbox = tuple(float(x) for x in bbox_raw.split(","))
    if len(bbox) != 4:
        raise ValueError("TARGET_BBOX は 'minlon,minlat,maxlon,maxlat' 形式")

    return Config(
        target_bbox=bbox,  # type: ignore[arg-type]
        gsi_api_rate_limit_sec=float(os.getenv("GSI_API_RATE_LIMIT_SEC", "1.0")),
        gsi_api_base_url=os.getenv(
            "GSI_API_BASE_URL",
            "https://cyberjapandata2.gsi.go.jp/general/dem/scripts/getelevation.php",
        ),
        min_output_kw=float(os.getenv("MIN_OUTPUT_KW", "10")),
        min_head_m=float(os.getenv("MIN_HEAD_M", "2")),
    )

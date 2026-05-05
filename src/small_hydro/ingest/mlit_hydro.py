"""国交省 水文水質DB スクレイピング。

データソース: http://www1.river.go.jp/
取得方式: ADR-002 で決定（暫定: Selenium）

データフォーマット（dataout.csv）:
- エンコーディング: cp932
- 観測項目: 流量 / 水位 / 雨量
"""
from datetime import date
from pathlib import Path

import pandas as pd

CACHE_DIR = Path("data/raw/mlit_hydro")
CSV_ENCODING = "cp932"


def fetch_flow_timeseries(
    station_code: str, start_date: date, end_date: date
) -> pd.DataFrame:
    """指定観測所の流量時系列を取得。

    Phase 2 で実装。ADR-002 確定後に Selenium / DPFssDB2.exe / requests のいずれか。
    """
    raise NotImplementedError("Phase 2: ADR-002 確定後に実装")


def load_cached_flow(station_code: str) -> pd.DataFrame:
    path = CACHE_DIR / f"{station_code}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"観測所 {station_code} のキャッシュなし: {path}"
        )
    return pd.read_csv(path, encoding=CSV_ENCODING)

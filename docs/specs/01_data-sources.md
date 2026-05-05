# データソース仕様

## 1. 環境省 REPOS（再生可能エネルギー情報提供システム）
- **URL**: https://www.renewable-energy-potential.env.go.jp/RePos/
- **形式**: Shapefile / CSV
- **提供内容**: 落差・流量・想定発電出力（事前計算済み）
- **取得方法**: 手動DL → `data/raw/repos/`
- **更新頻度**: 不定期
- **位置づけ**: 一次情報源（ADR-001）

## 2. 国土地理院 標高API
- **エンドポイント**: https://cyberjapandata2.gsi.go.jp/general/dem/scripts/getelevation.php
- **パラメータ**:
  - `lon`: 経度（必須）
  - `lat`: 緯度（必須）
  - `outtype`: `JSON` 推奨
  - `callback`: JSONP用（`outtype` と排他）
- **レスポンス**: `{elevation: float|"-----", hsrc: string}`
- **データソース種別 (`hsrc`)**:
  | hsrc | 精度（標準偏差） |
  |------|----------------|
  | 1m（レーザ） | 0.3m / 計測点なしで2.0m |
  | 5m（レーザ） | 0.3m / 計測点なしで2.0m |
  | 5m（写真測量） | 0.7m |
  | 5m（写真測量5C） | 1.4m |
  | 10m（等高線） | 5.0m |
- **制約**:
  - サーバ負荷禁止規約 → `time.sleep` 必須
  - 補間性質上、急峻地形では誤差大
  - エラー時は `"-----"` 文字列が返る → Null処理
  - 建物・橋梁等の人工構造物は反映されない

## 3. 国土交通省 水文水質データベース
- **URL**: http://www1.river.go.jp/
- **API**: なし
- **取得方法**: ADR-002 参照
  - A. `DPFssDB2.exe` をsubprocess駆動（Windows専用）
  - B. Selenium で検索画面操作
- **提供内容**: 河川流量・水位・降水量の時系列
- **出力**: `dataout.csv`

## 4. OpenStreetMap Overpass API（Phase 1.5）
- **エンドポイント**: https://overpass-api.de/api/interpreter
- **クエリ言語**: Overpass QL
- **対象タグ**: `waterway=weir`（堰）
- **取得方法**: HTTP POST（JSON）
- **位置づけ**: REPOSが手動DLな点を補う、即時取得可能な代替候補抽出経路
- **制約**:
  - 公開インスタンスは負荷高 → 大BBOXは時間かかる
  - 厳密な「有効落差」は不明 → 標高API併用で推定
- **使用例**:
  ```
  [out:json][timeout:60];
  node[waterway=weir](34.5,135.8,36.5,138.3);
  out body;
  ```

## 5. 系統空き容量
- **提供元**: 各一般送配電事業者（中部電力PG / 関西電力送配電 等）
- **形式**: 事業者により異なる（CSV / PDF / 地図画像 / Webアプリ）
- **スコープ**: Phase 3 で1事業者からPoC（ADR-003）

## データ取扱いルール
- `data/raw/` は**生データ保管。書き換え禁止**
- 変換結果は `data/interim/`、最終形は `data/processed/`
- 全 `data/` は `.gitignore` 対象

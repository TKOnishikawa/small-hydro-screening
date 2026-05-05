# small-hydro-screening AI参謀向け指示

## プロジェクト概要
公開データ（REPOS / 国土地理院標高API / 国交省水文DB / 系統空き容量）を統合し、小水力発電の候補地を机上でスクリーニングする。

## 重要な制約

### 国土地理院 標高API
- **サーバ負荷規約あり**。`time.sleep(config.gsi_api_rate_limit_sec)` でレート制御必須
- レスポンス `elevation` が `"-----"` の場合はNull扱い
- 補間アルゴリズムの性質上、急峻地形では誤差が出る点を留意

### 国交省 水文水質DB
- 公開APIなし。`DPFssDB2.exe` 経由 or Selenium スクレイピング（ADR-002）
- `DPFssDB2.exe` はWindows専用 → Cloud Run等のLinux環境では動かない

### データ取り扱い
- `data/raw/` は**書き換え禁止**（生データの再現性を確保）
- 中間処理は `data/interim/`、最終形は `data/processed/` に配置
- `data/` `output/` `.credentials/` `.env` は `.gitignore` 済

## 関連ドキュメント
- 仕様: `docs/specs/`
- 設計判断: `docs/plan/adr/`
- Phase分解: `docs/plan/roadmap.md`

## 開発フェーズ
現在: **Phase 0**（REPOS DL → QGIS可視化）

| Phase | スコープ |
|------|---------|
| 0 | REPOS DL → QGIS目視 |
| 1 | 標高API統合（落差自動算出） |
| 2 | 水文DB統合（流量分析） |
| 3 | 系統空き容量＋法規制フィルタ |

## 実装規約
- Python 3.11+
- 計算ロジック (`compute/`) は外部依存なしの純粋関数で書く（テスト容易性）
- 外部I/O は `ingest/` に隔離
- 例外発生時の挙動は呼び出し側で決める（ライブラリ層では握り潰さない）

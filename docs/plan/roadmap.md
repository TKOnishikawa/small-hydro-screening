# Roadmap

## Phase 一覧

| Phase | スコープ | 想定工数 | 完了条件 |
|-------|---------|---------|---------|
| **Phase 0** | REPOS DL → QGISで目視確認 | 0.5日 | `data/raw/repos/` にREPOS全件、QGISで地図表示確認 |
| **Phase 1** | 標高API統合 → 任意点の落差自動算出 | 3-5日 | ✅ `small-hydro head --upstream-* --downstream-*` で落差返却 |
| **Phase 1.5** | OSM Overpass + 標高API → REPOS非依存パイプライン | 3-5日 | ✅ `small-hydro screen --source=osm` で堰候補ランキング出力 |
| **Phase 2** | 水文DB統合 → 流量分析 | 1週間 | 観測所コード入力で豊水/平水/渇水を返す関数 |
| **Phase 3** | 系統空き容量＋法規制フィルタ | 1週間 | 候補リスト最終出力（CSV + GeoJSON） |

## 受入条件（全Phase共通）
- [ ] 同じ入力で2回実行して同じ結果（冪等性）
- [ ] `make screen` 1コマンドで再現可
- [ ] テスト: ユニット必須、統合は1ケースで可
- [ ] 出力データ辞書（[03_output-schema.md](../specs/03_output-schema.md)）を満たす

## Phase 詳細

### Phase 0: REPOS PoC
- [ ] REPOSサイトから対象エリアのデータDL
- [ ] `data/raw/repos/` に配置
- [ ] QGISで読込・可視化
- [ ] 出力件数・属性の目視確認

### Phase 1: 標高API統合
- [ ] `ingest/gsi_elevation.py` 実装
- [ ] レート制御の動作確認
- [ ] `compute/head.py` のテストグリーン
- [ ] CLI: `small-hydro elevation --lat=X --lon=Y`

### Phase 2: 水文DB統合
- [ ] ADR-002 確定
- [ ] スクレイパ実装
- [ ] `compute/flow.py` で渇水/平水流量算出
- [ ] 観測所コード→流量分位の動作確認

### Phase 3: 系統＋規制フィルタ
- [ ] ADR-003 確定（対象事業者）
- [ ] 系統空き容量パーサ実装
- [ ] 国立公園・保安林データ統合
- [ ] 最終候補リスト出力

## Out of Scope
- 水利権交渉・保安林申請・現地測量
- 詳細設計・コスト見積（建設費・利回り計算）
- 全電力会社の系統データ網羅（Phase 3後の継続課題）

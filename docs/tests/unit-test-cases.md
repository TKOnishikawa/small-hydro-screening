# ユニットテストケース

## compute/head.py

- **UT-HEAD-001: 単純落差計算**
  - Given: 上流標高 100m, 下流標高 50m
  - When: `compute_head(100, 50)`
  - Then: 50

- **UT-HEAD-002: ゼロ落差で例外**
  - Given: 上下流とも 50m
  - When: `compute_head(50, 50)`
  - Then: `ValueError`

- **UT-HEAD-003: 上下逆転で例外**
  - Given: 上流50m, 下流100m
  - When: `compute_head(50, 100)`
  - Then: `ValueError`

## compute/flow.py

- **UT-FLOW-001: 渇水流量算出**
  - Given: 365日の降順流量データ（365, 364, ..., 1）
  - When: `flow_at_exceedance(data, 355)`
  - Then: 355日超過する流量（= 11）

- **UT-FLOW-002: 365日未満で例外**
  - Given: 100日分のデータ
  - When: `drought_flow(data)`
  - Then: `ValueError`

- **UT-FLOW-003: 平水 ≧ 渇水**
  - Given: 任意の365日データ
  - When: `normal_flow >= drought_flow`
  - Then: 常に真

## compute/output.py

- **UT-OUTPUT-001: ゼロ流量で出力ゼロ**
  - Given: Q=0, H=10
  - Then: 0.0

- **UT-OUTPUT-002: 基本式の検証**
  - Given: Q=1.0 m³/s, H=10m, η=0.7
  - When: `theoretical_output_kw(1.0, 10.0, 0.7)`
  - Then: ≈ 68.67 kW (= 9.81 × 1.0 × 10.0 × 0.7)

## compute/scoring.py

- **UT-SCORE-001: MIN_OUTPUT_KW 未満で除外**
- **UT-SCORE-002: MIN_HEAD_M 未満で除外**
- **UT-SCORE-003: スコア降順ソート**

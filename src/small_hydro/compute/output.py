"""理論水力出力。

P (kW) = ρ × g × Q × H × η / 1000
"""

WATER_DENSITY = 1000.0
GRAVITY = 9.81
DEFAULT_EFFICIENCY = 0.7


def theoretical_output_kw(
    flow_m3s: float, head_m: float, efficiency: float = DEFAULT_EFFICIENCY
) -> float:
    if flow_m3s <= 0 or head_m <= 0:
        return 0.0
    return WATER_DENSITY * GRAVITY * flow_m3s * head_m * efficiency / 1000.0

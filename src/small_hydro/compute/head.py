def compute_head(upstream_elev_m: float, downstream_elev_m: float) -> float:
    head = upstream_elev_m - downstream_elev_m
    if head <= 0:
        raise ValueError(
            f"上流({upstream_elev_m}m) <= 下流({downstream_elev_m}m): 落差計算不可"
        )
    return head

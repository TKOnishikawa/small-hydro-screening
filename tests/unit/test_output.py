from small_hydro.compute.output import theoretical_output_kw


def test_zero_flow():
    assert theoretical_output_kw(0, 10) == 0.0


def test_zero_head():
    assert theoretical_output_kw(1.0, 0) == 0.0


def test_basic_formula():
    p = theoretical_output_kw(1.0, 10.0, 0.7)
    assert abs(p - 68.67) < 0.01

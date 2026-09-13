from yield_rate import calculate_yield


def test_calculates_fractional_yield() -> None:
    assert calculate_yield(9, 10) == 90.0

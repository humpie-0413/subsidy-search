from calculator import calculate_income_percentile, extract_amount_number


def test_income_percentile_1person_low():
    pct = calculate_income_percentile(income_monthly=1000000, household_size=1)
    assert 40 <= pct <= 43


def test_income_percentile_4person_median():
    pct = calculate_income_percentile(income_monthly=6097773, household_size=4)
    assert pct == 100


def test_income_percentile_high_income():
    pct = calculate_income_percentile(income_monthly=12000000, household_size=1)
    assert pct > 200


def test_income_percentile_zero():
    pct = calculate_income_percentile(income_monthly=0, household_size=1)
    assert pct == 0


def test_income_percentile_household_capped_at_4():
    pct = calculate_income_percentile(income_monthly=6097773, household_size=5)
    assert pct == 100


def test_extract_amount_number_basic():
    assert extract_amount_number("최대 5,000만원") == 50000000


def test_extract_amount_number_monthly():
    assert extract_amount_number("월 최대 20만원") == 200000


def test_extract_amount_number_yearly():
    assert extract_amount_number("자녀 1인당 연 100만원") == 1000000


def test_extract_amount_number_billion():
    assert extract_amount_number("최대 3억원 (자부담 30%)") == 300000000


def test_extract_amount_number_unparseable():
    assert extract_amount_number("설치비의 최대 50%") is None


def test_extract_amount_number_per_person():
    assert extract_amount_number("월 최대 80만원/인") == 800000

"""Тесты расчётного движка методики: сверка балльных шкал раздела 4 ТЗ."""

from datetime import date

import pytest

from vulnerability_index.methodology import (
    MethodologyError,
    MethodologyRepository,
    NoMatchingRuleError,
)


@pytest.fixture(scope="module")
def methodology():
    return MethodologyRepository().latest()


# ---------------------------------------------------------------------------
# GEO (п. 4.2 ТЗ)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "value,expected_score",
    [(1499, 1), (1499.9, 1), (1500, 2), (1999, 2), (2000, 3), (5000, 3)],
)
def test_geo_height(methodology, value, expected_score):
    score, _ = methodology.score_indicator("GEO", "height", value)
    assert score == expected_score


@pytest.mark.parametrize(
    "value,expected_score", [(0, 1), (11.9, 1), (12, 2), (20, 2), (20.1, 3), (45, 3)]
)
def test_geo_slope(methodology, value, expected_score):
    score, _ = methodology.score_indicator("GEO", "slope", value)
    assert score == expected_score


def test_geo_component_formula(methodology):
    # GEO = 0.8*height + 0.2*slope; height=2000(->3), slope=10(->1)
    scores = {"height": 3.0, "slope": 1.0}
    value = methodology.compute_component("GEO", scores)
    assert value == pytest.approx(0.8 * 3 + 0.2 * 1)


# ---------------------------------------------------------------------------
# ACC (п. 4.3 ТЗ)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("value,expected", [(30, 1), (31, 2), (60, 2), (61, 3)])
def test_acc_time_to_raion(methodology, value, expected):
    score, _ = methodology.score_indicator("ACC", "time_to_raion", value)
    assert score == expected


@pytest.mark.parametrize("value,expected", [(5, 1), (6, 2), (20, 2), (21, 3)])
def test_acc_distance_to_road(methodology, value, expected):
    score, _ = methodology.score_indicator("ACC", "distance_to_road", value)
    assert score == expected


@pytest.mark.parametrize("value,expected", [(60, 1), (61, 2), (120, 2), (121, 3)])
def test_acc_winter(methodology, value, expected):
    score, _ = methodology.score_indicator("ACC", "time_to_raion_winter", value)
    assert score == expected


# ---------------------------------------------------------------------------
# DEM (п. 4.4 ТЗ)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "value,expected", [(999, 3), (1000, 3), (1001, 2), (2000, 2), (2001, 1), (3000, 1), (3001, 0)]
)
def test_dem_population(methodology, value, expected):
    score, _ = methodology.score_indicator("DEM", "population", value)
    assert score == expected


@pytest.mark.parametrize(
    "value,expected",
    [(-10.1, 3), (-10, 2), (0, 2), (5, 2), (5.1, 1), (10, 1), (10.1, 0)],
)
def test_dem_depopulation(methodology, value, expected):
    score, _ = methodology.score_indicator("DEM", "depopulation_pct", value)
    assert score == expected


@pytest.mark.parametrize(
    "value,expected", [(-15.1, 3), (-15, 2), (-5, 2), (-4.9, 1), (5, 1), (5.1, 0)]
)
def test_dem_migration(methodology, value, expected):
    score, _ = methodology.score_indicator("DEM", "net_migration", value)
    assert score == expected


def test_dem_missing_value_raises(methodology):
    with pytest.raises(NoMatchingRuleError):
        methodology.score_indicator("DEM", "population", None)


# ---------------------------------------------------------------------------
# SERV (п. 4.5 ТЗ)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "option,expected", [("in_settlement", 0), ("within_5km", 1), ("over_5km", 2), ("absent", 3)]
)
def test_serv_school(methodology, option, expected):
    score, _ = methodology.score_indicator("SERV", "school", option)
    assert score == expected


def test_serv_kindergarten_minimum_two(methodology):
    score, _ = methodology.score_indicator("SERV", "kindergarten", "present")
    assert score == 2  # минимум 2 балла даже при наличии объекта (п. 4.5 ТЗ)


def test_serv_unknown_option_raises(methodology):
    with pytest.raises(NoMatchingRuleError):
        methodology.score_indicator("SERV", "school", "does_not_exist")


# ---------------------------------------------------------------------------
# ECO (п. 4.7 ТЗ) — минимум компонента 2 балла
# ---------------------------------------------------------------------------
def test_eco_minimum_two(methodology):
    scores = {
        "landslide_risk": methodology.score_indicator("ECO", "landslide_risk", "documented_absent")[0],
        "seismicity": methodology.score_indicator("ECO", "seismicity", "up_to_7")[0],
    }
    value = methodology.compute_component("ECO", scores)
    assert value == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# ECON (п. 4.8 ТЗ)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "value,expected", [(0, 0), (0.5, 1), (2.9, 1), (3, 2), (10, 2), (10.1, 3), (50, 3)]
)
def test_econ_tzhs(methodology, value, expected):
    score, _ = methodology.score_indicator("ECON", "tzhs_share", value)
    assert score == expected


@pytest.mark.parametrize("value,expected", [(0, 3), (0.5, 2), (0.99, 2), (1, 1), (5, 1)])
def test_econ_irrigated_land(methodology, value, expected):
    score, _ = methodology.score_indicator("ECON", "irrigated_land_per_capita", value)
    assert score == expected


@pytest.mark.parametrize("value,expected", [(0, 3), (5, 3), (5.1, 2), (10, 2), (10.1, 1), (20, 1), (20.1, 0)])
def test_econ_business_density(methodology, value, expected):
    score, _ = methodology.score_indicator("ECON", "business_density", value)
    assert score == expected


# ---------------------------------------------------------------------------
# Итоговая формула ИУ (п. 4.1 ТЗ)
# ---------------------------------------------------------------------------
def test_overall_formula_weights_sum_to_one(methodology):
    total = sum(c.weight for c in methodology.components.values())
    assert total == pytest.approx(1.0)


def test_overall_index_formula(methodology):
    component_values = {
        "GEO": 3.0, "ACC": 3.0, "DEM": 3.0, "SERV": 3.0,
        "INFRA": 3.0, "ECO": 3.0, "ECON": 3.0,
    }
    assert methodology.compute_index(component_values) == pytest.approx(3.0)

    component_values_zero = {k: 0.0 for k in component_values}
    assert methodology.compute_index(component_values_zero) == pytest.approx(0.0)

    mixed = {
        "GEO": 1.0, "ACC": 2.0, "DEM": 0.0, "SERV": 3.0,
        "INFRA": 1.0, "ECO": 2.0, "ECON": 3.0,
    }
    expected = 0.20 * 1 + 0.30 * 2 + 0.10 * 0 + 0.10 * 3 + 0.10 * 1 + 0.10 * 2 + 0.10 * 3
    assert methodology.compute_index(mixed) == pytest.approx(expected)


def test_index_value_range(methodology):
    assert methodology.value_range == (0.0, 3.0)


# ---------------------------------------------------------------------------
# Категоризация (п. 4.9 ТЗ) и версия методики
# ---------------------------------------------------------------------------
def test_categorize_defaults(methodology):
    assert methodology.categorize(0.5) == "условно уязвимый"
    assert methodology.categorize(1.5) == "умеренно уязвимый"
    assert methodology.categorize(2.5) == "критично уязвимый"


def test_categories_not_yet_approved(methodology):
    # Требование ТЗ: методика не фиксирует точные пороги — модуль должен
    # явно отражать неутверждённый статус временных порогов.
    assert methodology.categories_approved() is False


def test_get_for_date(methodology):
    repo = MethodologyRepository()
    m = repo.get_for_date(date(2030, 1, 1))
    assert m.version == methodology.version

    with pytest.raises(MethodologyError):
        repo.get_for_date(date(2000, 1, 1))


def test_partial_component_renormalizes_weights(methodology):
    # Если один из показателей компонента отсутствует, вес пересчитывается
    # среди оставшихся, а не приводит к ошибке (обязательное условие
    # диалога при показателе "нет данных").
    only_height = {"height": 3.0}
    value = methodology.compute_component("GEO", only_height, allow_partial=True)
    assert value == pytest.approx(3.0)  # единственный доступный показатель определяет компонент

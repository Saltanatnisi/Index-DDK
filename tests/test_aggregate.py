"""Тесты сборки итогового результата из произвольного набора показателей
(используется веб-приложением и диалоговым модулем)."""

import pytest

from vulnerability_index.aggregate import aggregate_index_result
from vulnerability_index.methodology import MethodologyRepository
from vulnerability_index.models import DataValue, IndicatorResult, Settlement


@pytest.fixture(scope="module")
def methodology():
    return MethodologyRepository().latest()


@pytest.fixture
def settlement():
    return Settlement(code="KG-001", name="Тест", district="Р", region="О")


def _result(methodology, component_key, indicator_key, raw_value) -> IndicatorResult:
    spec = methodology.indicator(component_key, indicator_key)
    score, label = spec.score(raw_value)
    return IndicatorResult(
        key=indicator_key, title=spec.title, component_key=component_key,
        weight_within_component=spec.weight,
        data=DataValue(raw_value=raw_value, source_name="test", source_kind="file"),
        score=score, matched_rule_label=label,
    )


def test_aggregate_full_settlement_matches_manual_formula(methodology, settlement):
    indicator_results = {
        ("GEO", "height"): _result(methodology, "GEO", "height", 3000),
        ("GEO", "slope"): _result(methodology, "GEO", "slope", 15),
        ("ACC", "time_to_raion"): _result(methodology, "ACC", "time_to_raion", 90),
        ("ACC", "distance_to_road"): _result(methodology, "ACC", "distance_to_road", 25),
        ("ACC", "time_to_raion_winter"): _result(methodology, "ACC", "time_to_raion_winter", 150),
        ("DEM", "population"): _result(methodology, "DEM", "population", 850),
        ("DEM", "depopulation_pct"): _result(methodology, "DEM", "depopulation_pct", -15),
        ("DEM", "net_migration"): _result(methodology, "DEM", "net_migration", -20),
        ("SERV", "school"): _result(methodology, "SERV", "school", "within_5km"),
        ("SERV", "fap"): _result(methodology, "SERV", "fap", "absent"),
        ("SERV", "kindergarten"): _result(methodology, "SERV", "kindergarten", "absent"),
        ("INFRA", "connectivity"): _result(methodology, "INFRA", "connectivity", "no_stable"),
        ("INFRA", "road_type"): _result(methodology, "INFRA", "road_type", "gravel_dirt"),
        ("INFRA", "seasonal_closure"): _result(methodology, "INFRA", "seasonal_closure", "regular_long"),
        ("INFRA", "water_access"): _result(methodology, "INFRA", "water_access", "delivered"),
        ("ECO", "landslide_risk"): _result(methodology, "ECO", "landslide_risk", "documented_present"),
        ("ECO", "seismicity"): _result(methodology, "ECO", "seismicity", "above_7"),
        ("ECON", "tzhs_share"): _result(methodology, "ECON", "tzhs_share", 15),
        ("ECON", "irrigated_land_per_capita"): _result(methodology, "ECON", "irrigated_land_per_capita", 0),
        ("ECON", "business_density"): _result(methodology, "ECON", "business_density", 3),
    }
    result = aggregate_index_result(methodology, settlement, indicator_results)
    assert result.value == pytest.approx(2.83, abs=1e-6)
    assert result.category == "критично уязвимый"
    assert not result.has_assumptions


def test_aggregate_partial_data_renormalizes(methodology, settlement):
    indicator_results = {
        ("GEO", "height"): _result(methodology, "GEO", "height", 3000),
        # slope отсутствует полностью
    }
    result = aggregate_index_result(methodology, settlement, indicator_results)
    geo = result.component("GEO")
    assert geo.value == pytest.approx(3.0)  # единственный доступный показатель


def test_aggregate_missing_indicator_marked_in_component(methodology, settlement):
    missing = IndicatorResult(
        key="slope", title="x", component_key="GEO", weight_within_component=0.2,
        data=DataValue(raw_value=None, source_name="-", source_kind="missing"), score=None,
    )
    present = _result(methodology, "GEO", "height", 3000)
    indicator_results = {("GEO", "height"): present, ("GEO", "slope"): missing}
    result = aggregate_index_result(methodology, settlement, indicator_results)
    geo = result.component("GEO")
    assert geo.value == pytest.approx(3.0)
    assert any(i.is_missing for i in geo.indicators)

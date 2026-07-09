"""Тесты коннекторов источников данных и цепочки fallback (раздел 5.9,
5.10 ТЗ)."""

from pathlib import Path

import pandas as pd
import pytest
import requests

from vulnerability_index.datasources import (
    DataNotAvailable,
    DataSourceChain,
    ManualInputSource,
    NscOpenDataSource,
    OpenElevationSource,
    RestApiDataSource,
    TableDataSource,
)
from vulnerability_index.methodology import MethodologyRepository
from vulnerability_index.models import Settlement


@pytest.fixture(scope="module")
def methodology():
    return MethodologyRepository().latest()


@pytest.fixture
def settlement():
    return Settlement(code="KG-001", name="Тестовое", district="Тест. район", region="Тест. область", lat=40.0, lon=74.0)


def test_table_data_source_csv(tmp_path, methodology, settlement):
    path = tmp_path / "export.csv"
    pd.DataFrame({"code": ["KG-001", "KG-002"], "height_m": [2500, 1200]}).to_csv(path, index=False)
    source = TableDataSource(path, column_map={("GEO", "height"): "height_m"})
    value = source.fetch(settlement, "GEO", "height", methodology.indicator("GEO", "height"))
    assert value.raw_value == 2500
    assert value.source_kind == "file"


def test_table_data_source_missing_row_raises(tmp_path, methodology, settlement):
    path = tmp_path / "export.csv"
    pd.DataFrame({"code": ["KG-999"], "height_m": [2500]}).to_csv(path, index=False)
    source = TableDataSource(path, column_map={("GEO", "height"): "height_m"})
    with pytest.raises(DataNotAvailable):
        source.fetch(settlement, "GEO", "height", methodology.indicator("GEO", "height"))


def test_table_data_source_missing_file_raises(methodology, settlement):
    source = TableDataSource(Path("/nonexistent/file.csv"), column_map={("GEO", "height"): "height_m"})
    with pytest.raises(DataNotAvailable):
        source.fetch(settlement, "GEO", "height", methodology.indicator("GEO", "height"))


def test_table_data_source_unmapped_indicator_raises(tmp_path, methodology, settlement):
    path = tmp_path / "export.csv"
    pd.DataFrame({"code": ["KG-001"], "height_m": [2500]}).to_csv(path, index=False)
    source = TableDataSource(path, column_map={("GEO", "height"): "height_m"})
    with pytest.raises(DataNotAvailable):
        source.fetch(settlement, "GEO", "slope", methodology.indicator("GEO", "slope"))


def test_manual_input_source_numeric(methodology, settlement):
    answers = iter(["2500", ""])
    source = ManualInputSource(input_func=lambda _: next(answers), print_func=lambda *_: None)
    value = source.fetch(settlement, "GEO", "height", methodology.indicator("GEO", "height"))
    assert value.raw_value == 2500.0
    assert value.source_kind == "manual"


def test_manual_input_source_option(methodology, settlement):
    answers = iter(["4", "документ №1"])  # 4-й вариант = "absent"
    source = ManualInputSource(input_func=lambda _: next(answers), print_func=lambda *_: None)
    value = source.fetch(settlement, "SERV", "school", methodology.indicator("SERV", "school"))
    assert value.raw_value == "absent"
    assert value.comment == "документ №1"


def test_manual_input_source_empty_raises(methodology, settlement):
    answers = iter([""])
    source = ManualInputSource(input_func=lambda _: next(answers), print_func=lambda *_: None)
    with pytest.raises(DataNotAvailable):
        source.fetch(settlement, "GEO", "height", methodology.indicator("GEO", "height"))


def test_rest_api_data_source_success(monkeypatch, methodology, settlement):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": {"value": 42}}

    def fake_request(self, method, url, **kwargs):
        assert "KG-001" in url
        return FakeResponse()

    monkeypatch.setattr(requests.Session, "request", fake_request)
    source = RestApiDataSource(
        name="Демо-платформа",
        endpoints={("ECON", "business_density"): {"url": "https://example.kg/{code}", "json_path": "data.value"}},
    )
    value = source.fetch(settlement, "ECON", "business_density", methodology.indicator("ECON", "business_density"))
    assert value.raw_value == 42
    assert value.source_kind == "api"


def test_rest_api_data_source_network_error(monkeypatch, methodology, settlement):
    def fake_request(self, method, url, **kwargs):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr(requests.Session, "request", fake_request)
    source = RestApiDataSource(
        name="Демо-платформа",
        endpoints={("ECON", "business_density"): {"url": "https://example.kg/{code}", "json_path": "data.value"}},
    )
    with pytest.raises(DataNotAvailable):
        source.fetch(settlement, "ECON", "business_density", methodology.indicator("ECON", "business_density"))


def test_nsc_source_falls_back_to_local_file(monkeypatch, tmp_path, methodology, settlement):
    fallback = tmp_path / "nsc_demo.csv"
    pd.DataFrame({"code": ["KG-001"], "population": [850]}).to_csv(fallback, index=False)

    def fake_get(self, url, timeout=None):
        raise requests.ConnectionError("stat.kg unreachable in sandbox")

    monkeypatch.setattr(requests.Session, "get", fake_get)
    source = NscOpenDataSource(
        export_url="https://stat.kg/export.csv",
        column_map={("DEM", "population"): "population"},
        local_fallback_path=fallback,
    )
    value = source.fetch(settlement, "DEM", "population", methodology.indicator("DEM", "population"))
    assert value.raw_value == 850
    assert value.source_kind == "nsc"


def test_nsc_source_no_fallback_raises(monkeypatch, methodology, settlement):
    def fake_get(self, url, timeout=None):
        raise requests.ConnectionError("unreachable")

    monkeypatch.setattr(requests.Session, "get", fake_get)
    source = NscOpenDataSource(
        export_url="https://stat.kg/export.csv",
        column_map={("DEM", "population"): "population"},
    )
    with pytest.raises(DataNotAvailable):
        source.fetch(settlement, "DEM", "population", methodology.indicator("DEM", "population"))


def test_open_elevation_source_success(monkeypatch, methodology, settlement):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [{"elevation": 3123.4}]}

    def fake_get(self, url, params=None, timeout=None):
        assert params["locations"] == f"{settlement.lat},{settlement.lon}"
        return FakeResponse()

    monkeypatch.setattr(requests.Session, "get", fake_get)
    source = OpenElevationSource()
    value = source.fetch(settlement, "GEO", "height", methodology.indicator("GEO", "height"))
    assert value.raw_value == 3123.4
    assert value.source_kind == "web"


def test_open_elevation_source_wrong_indicator_raises(methodology, settlement):
    source = OpenElevationSource()
    with pytest.raises(DataNotAvailable):
        source.fetch(settlement, "GEO", "slope", methodology.indicator("GEO", "slope"))


def test_open_elevation_source_missing_coords_raises(methodology):
    settlement_no_coords = Settlement(code="X", name="N", district="D", region="R")
    source = OpenElevationSource()
    with pytest.raises(DataNotAvailable):
        source.fetch(settlement_no_coords, "GEO", "height", methodology.indicator("GEO", "height"))


# ---------------------------------------------------------------------------
# DataSourceChain: fallback между несколькими источниками
# ---------------------------------------------------------------------------

class _AlwaysFails:
    name = "Источник А (недоступен)"
    kind = "api"

    def fetch(self, *args, **kwargs):
        raise DataNotAvailable("источник А недоступен")


class _AlwaysSucceeds:
    name = "Источник Б (файл)"
    kind = "file"

    def __init__(self, value):
        self._value = value

    def fetch(self, settlement, component_key, indicator_key, indicator_spec):
        from vulnerability_index.models import DataValue

        return DataValue(raw_value=self._value, source_name=self.name, source_kind=self.kind)


def test_chain_falls_back_to_second_source(methodology, settlement):
    chain = DataSourceChain([_AlwaysFails(), _AlwaysSucceeds(2500)])
    outcome = chain.fetch(settlement, "GEO", "height", methodology.indicator("GEO", "height"))
    assert outcome.succeeded
    assert outcome.value.raw_value == 2500
    assert outcome.value.source_name == "Источник Б (файл)"
    assert len(outcome.attempts) == 2
    assert outcome.attempts[0].success is False
    assert outcome.attempts[1].success is True


def test_chain_all_sources_fail(methodology, settlement):
    chain = DataSourceChain([_AlwaysFails(), _AlwaysFails()])
    outcome = chain.fetch(settlement, "GEO", "height", methodology.indicator("GEO", "height"))
    assert not outcome.succeeded
    assert outcome.value is None
    assert len(outcome.attempts) == 2
    assert all(a.success is False for a in outcome.attempts)


def test_chain_empty_sources():
    chain = DataSourceChain([])
    outcome = chain.fetch(None, "GEO", "height", None)
    assert not outcome.succeeded
    assert outcome.attempts == []

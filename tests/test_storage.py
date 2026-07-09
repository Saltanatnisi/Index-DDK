"""Тесты хранения результатов расчёта и истории (п. 5.12, 6.1 ТЗ)."""

from datetime import datetime, timezone

import pytest

from vulnerability_index.methodology import MethodologyRepository
from vulnerability_index.models import (
    ComponentResult,
    DataValue,
    IndexResult,
    IndicatorResult,
    Settlement,
    VerificationStatus,
)
from vulnerability_index.storage import ResultStore


@pytest.fixture(scope="module")
def methodology():
    return MethodologyRepository().latest()


def _make_result(settlement_code="KG-001") -> IndexResult:
    settlement = Settlement(code=settlement_code, name="Тест", district="Р", region="О")
    indicator = IndicatorResult(
        key="height", title="Высота", component_key="GEO", weight_within_component=0.8,
        data=DataValue(raw_value=2500, source_name="Тест-источник", source_kind="file"),
        score=3.0, matched_rule_label="2000 м и выше",
    )
    component = ComponentResult(key="GEO", title="Географическая уязвимость", weight=0.2, value=3.0, indicators=[indicator])
    return IndexResult(
        settlement=settlement, methodology_version="1.0",
        calculated_at=datetime.now(timezone.utc), components=[component], value=2.5,
        category="умеренно уязвимый",
    )


def test_save_and_load_roundtrip(tmp_path):
    store = ResultStore(base_dir=tmp_path)
    result = _make_result()
    path = store.save(result)
    assert path.exists()

    loaded = store.load(path)
    assert loaded.settlement.code == result.settlement.code
    assert loaded.value == pytest.approx(result.value)
    assert loaded.category == result.category
    assert loaded.components[0].indicators[0].data.raw_value == 2500
    assert loaded.verification_status == VerificationStatus.NOT_VERIFIED


def test_history_accumulates_and_latest_returns_most_recent(tmp_path):
    store = ResultStore(base_dir=tmp_path)
    r1 = _make_result()
    store.save(r1)

    r2 = _make_result()
    r2.value = 1.1
    r2.calculated_at = datetime.now(timezone.utc)
    store.save(r2)

    history = store.history("KG-001")
    assert len(history) == 2

    latest = store.latest("KG-001")
    assert latest.value == pytest.approx(1.1)


def test_update_verification_status(tmp_path):
    store = ResultStore(base_dir=tmp_path)
    result = _make_result()
    store.save(result)

    updated = store.update_verification(
        result, VerificationStatus.VERIFIED, comment="Проверено райадминистрацией"
    )
    assert updated.verification_status == VerificationStatus.VERIFIED

    latest = store.latest("KG-001")
    assert latest.verification_status == VerificationStatus.VERIFIED
    assert latest.verification_comment == "Проверено райадминистрацией"


def test_latest_returns_none_when_no_history(tmp_path):
    store = ResultStore(base_dir=tmp_path)
    assert store.latest("UNKNOWN") is None

"""Тесты неинтерактивного (батч/ETL) пересчёта Индекса (п. 4.10, 6.2 ТЗ)."""

import pytest

from vulnerability_index.batch import compute_index_for_settlement, recalculate_all
from vulnerability_index.methodology import MethodologyError, MethodologyRepository
from vulnerability_index.settlements import SettlementRepository
from vulnerability_index.source_factory import build_default_source_chains
from vulnerability_index.storage import ResultStore


@pytest.fixture(scope="module")
def methodology():
    return MethodologyRepository().latest()


@pytest.fixture(scope="module")
def settlement_repo():
    return SettlementRepository()


@pytest.fixture(scope="module")
def source_chains():
    # Использует локальные демо-выгрузки; сетевые НСК/REST-подключения
    # автоматически откатываются на локальный fallback-файл при отсутствии
    # сети в изолированной среде тестирования (см. source_factory).
    return build_default_source_chains()


def test_compute_index_for_settlement_uses_demo_sources(methodology, settlement_repo, source_chains):
    settlement = settlement_repo.get("KG-001")
    result = compute_index_for_settlement(methodology, settlement, source_chains)

    assert result.value == pytest.approx(2.83, abs=1e-6)
    assert result.category == "критично уязвимый"
    assert not any(
        indicator.is_missing for component in result.components for indicator in component.indicators
    )


def test_compute_index_for_settlement_kg004_lower_vulnerability(methodology, settlement_repo, source_chains):
    settlement = settlement_repo.get("KG-004")
    result = compute_index_for_settlement(methodology, settlement, source_chains)
    # KG-004 (Каджи-Сай) в демо-данных — наименее уязвимый населённый пункт.
    assert result.value < 2.0


def test_recalculate_all_settlements_and_saves_history(tmp_path, methodology, settlement_repo, source_chains):
    store = ResultStore(base_dir=tmp_path)
    results = recalculate_all(methodology, list(settlement_repo.all()), source_chains, result_store=store)
    assert len(results) == len(list(settlement_repo.all()))
    for settlement in settlement_repo.all():
        assert store.latest(settlement.code) is not None


def test_missing_all_source_chains_raises_when_index_cannot_be_computed(methodology, settlement_repo):
    settlement = settlement_repo.get("KG-001")
    # Без единого настроенного источника ни один показатель не может быть
    # получен автоматически — Индекс в принципе невозможно рассчитать, что
    # должно быть явной ошибкой, а не тихим "0"/None результатом.
    with pytest.raises(MethodologyError):
        compute_index_for_settlement(methodology, settlement, source_chains={})

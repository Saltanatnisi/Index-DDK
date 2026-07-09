"""Тесты диалогового модуля: сценарии авто-сбора, ручного ввода,
допущений и отметки «нет данных» (разделы 4.10, 5.9, 5.10 ТЗ)."""

import pytest

from vulnerability_index.datasources.base import DataNotAvailable, DataSource
from vulnerability_index.datasources.chain import DataSourceChain
from vulnerability_index.dialog import DialogIO, IndexDialog
from vulnerability_index.methodology import MethodologyRepository
from vulnerability_index.models import DataValue, VerificationStatus
from vulnerability_index.settlements import SettlementRepository


class _FixedValueSource(DataSource):
    kind = "file"

    def __init__(self, name, value):
        self.name = name
        self._value = value

    def fetch(self, settlement, component_key, indicator_key, indicator_spec):
        return DataValue(raw_value=self._value, source_name=self.name, source_kind=self.kind)


class _FailingSource(DataSource):
    kind = "api"
    name = "Недоступная демо-платформа"

    def fetch(self, settlement, component_key, indicator_key, indicator_spec):
        raise DataNotAvailable("демо-платформа временно недоступна")


DEMO_VALUES = {
    ("GEO", "height"): 3000,
    ("GEO", "slope"): 15,
    ("ACC", "time_to_raion"): 90,
    ("ACC", "distance_to_road"): 25,
    ("ACC", "time_to_raion_winter"): 150,
    ("DEM", "population"): 850,
    ("DEM", "depopulation_pct"): -15,
    ("DEM", "net_migration"): -20,
    ("SERV", "school"): "within_5km",
    ("SERV", "fap"): "absent",
    ("SERV", "kindergarten"): "absent",
    ("INFRA", "connectivity"): "no_stable",
    ("INFRA", "road_type"): "gravel_dirt",
    ("INFRA", "seasonal_closure"): "regular_long",
    ("INFRA", "water_access"): "delivered",
    ("ECO", "landslide_risk"): "documented_present",
    ("ECO", "seismicity"): "above_7",
    ("ECON", "tzhs_share"): 15,
    ("ECON", "irrigated_land_per_capita"): 0,
    ("ECON", "business_density"): 3,
}


def _build_fake_chains():
    return {
        key: DataSourceChain([_FixedValueSource(f"Демо-источник {key}", value)])
        for key, value in DEMO_VALUES.items()
    }


def _answer_queue(answers):
    it = iter(answers)

    def _input(prompt):
        return next(it)

    return _input


@pytest.fixture(scope="module")
def methodology():
    return MethodologyRepository().latest()


@pytest.fixture
def settlement_repo():
    return SettlementRepository()


def test_dialog_full_run_auto_sources_matches_batch_result(methodology, settlement_repo):
    settlement = settlement_repo.get("KG-001")
    chains = _build_fake_chains()
    # На каждый из 20 показателей — 2 ответа Enter: выбор "Авто" (по умолчанию)
    # и подтверждение полученного значения (по умолчанию — да).
    answers = [""] * (len(DEMO_VALUES) * 2)
    io = DialogIO(input_func=_answer_queue(answers), print_func=lambda *_: None)
    dialog = IndexDialog(
        methodology=methodology, settlement_repo=settlement_repo, source_chains=chains, io=io
    )
    result = dialog.run(settlement)

    assert result.value == pytest.approx(2.83, abs=1e-6)
    assert result.category == "критично уязвимый"
    assert result.verification_status == VerificationStatus.NOT_VERIFIED
    assert not result.has_assumptions
    assert result.component("GEO").value == pytest.approx(2.8)
    assert result.component("ACC").value == pytest.approx(3.0)


def test_dialog_auto_falls_back_and_notifies_on_source_failure(methodology, settlement_repo):
    settlement = settlement_repo.get("KG-002")
    component_spec = methodology.components["GEO"]
    indicator_spec = component_spec.indicators["height"]
    chain = DataSourceChain([_FailingSource(), _FixedValueSource("Резервный файл", 2800)])
    io = DialogIO(input_func=_answer_queue(["", ""]), print_func=lambda *_: None)
    dialog = IndexDialog(
        methodology=methodology,
        settlement_repo=settlement_repo,
        source_chains={("GEO", "height"): chain},
        io=io,
    )
    result = dialog._collect_indicator(settlement, component_spec, indicator_spec)
    assert result.data.raw_value == 2800
    assert result.data.source_name == "Резервный файл"
    assert result.score == 3.0


def test_dialog_manual_entry_when_no_chain_configured(methodology, settlement_repo):
    settlement = settlement_repo.get("KG-003")
    component_spec = methodology.components["SERV"]
    indicator_spec = component_spec.indicators["school"]
    # Без источников меню = [Ввести вручную, Нет данных]; по умолчанию — вручную.
    # Далее ManualInputSource запрашивает номер варианта (within_5km = №2) и
    # документ-основание.
    answers = iter(["", "2", "Акт обследования №5"])
    io = DialogIO(input_func=lambda _: next(answers), print_func=lambda *_: None)
    dialog = IndexDialog(
        methodology=methodology, settlement_repo=settlement_repo, source_chains={}, io=io
    )
    result = dialog._collect_indicator(settlement, component_spec, indicator_spec)
    assert result.data.raw_value == "within_5km"
    assert result.score == 1.0
    assert result.data.comment == "Акт обследования №5"
    assert result.data.source_kind == "manual"


def test_dialog_assumption_flow_marks_value_as_assumption(methodology, settlement_repo):
    settlement = settlement_repo.get("KG-004")
    component_spec = methodology.components["ECO"]
    indicator_spec = component_spec.indicators["seismicity"]
    # Меню без источников: [manual(1), assumption(2)] -> выбираем "2" (допущение).
    # Затем: причина допущения (3 = ГИС-анализ), вариант показателя (1 = up_to_7),
    # комментарий.
    answers = iter(["2", "3", "1", "Оценка по соседнему району"])
    io = DialogIO(input_func=lambda _: next(answers), print_func=lambda *_: None)
    dialog = IndexDialog(
        methodology=methodology, settlement_repo=settlement_repo, source_chains={}, io=io
    )
    result = dialog._collect_indicator(settlement, component_spec, indicator_spec)
    assert result.data.is_assumption is True
    assert result.data.assumption_reason == "Результаты геоинформационного анализа"
    assert result.data.raw_value == "up_to_7"
    assert result.score == 2.0
    assert result.data.comment == "Оценка по соседнему району"


def test_dialog_no_data_marks_indicator_missing_and_notifies(methodology, settlement_repo):
    settlement = settlement_repo.get("KG-005")
    component_spec = methodology.components["ECO"]
    indicator_spec = component_spec.indicators["landslide_risk"]
    notifications = []
    # Меню: [manual(1), assumption(2)] -> "2"; в под-меню допущения выбираем
    # последний пункт "Отказаться — показатель «нет данных»" (индекс 5:
    # 4 причины + 1 "отказаться").
    answers = iter(["2", "5"])
    io = DialogIO(
        input_func=lambda _: next(answers),
        print_func=lambda text="": notifications.append(text),
    )
    dialog = IndexDialog(
        methodology=methodology, settlement_repo=settlement_repo, source_chains={}, io=io
    )
    result = dialog._collect_indicator(settlement, component_spec, indicator_spec)
    assert result.is_missing
    assert result.score is None
    assert any("УВЕДОМЛЕНИЕ" in n for n in notifications)


def test_dialog_component_renormalizes_when_indicator_missing(methodology):
    component_spec = methodology.components["ECO"]
    # landslide_risk отсутствует, seismicity=above_7 (score 3) — компонент
    # должен рассчитаться только по доступному показателю.
    from vulnerability_index.models import IndicatorResult

    missing = IndicatorResult(
        key="landslide_risk", title="x", component_key="ECO",
        weight_within_component=0.5,
        data=DataValue(raw_value=None, source_name="-", source_kind="missing"),
        score=None,
    )
    present_score, _ = component_spec.indicators["seismicity"].score("above_7")
    present = IndicatorResult(
        key="seismicity", title="x", component_key="ECO",
        weight_within_component=0.5,
        data=DataValue(raw_value="above_7", source_name="-", source_kind="file"),
        score=present_score,
    )
    scores = {r.key: r.score for r in [missing, present] if r.score is not None}
    value = component_spec.compute(scores, allow_partial=True)
    assert value == pytest.approx(3.0)

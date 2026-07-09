"""Регрессионные тесты веб-приложения (диалоговое окно + дашборд) через
`streamlit.testing.v1.AppTest`. Приложение загружается через основную
точку входа `webapp/app.py` (с реальной регистрацией страниц через
`st.navigation`/`st.Page`), а переход между страницами выполняется через
`AppTest.switch_page`, чтобы корректно работали `st.page_link` и общая
навигация. Хранилище результатов/журнала перенаправляется во временный
каталог, чтобы тесты не писали в реальный `data/` репозитория.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from vulnerability_index.storage import RawDataLog, ResultStore

WEBAPP_DIR = Path(__file__).resolve().parent.parent / "webapp"
APP_ENTRY = str(WEBAPP_DIR / "app.py")


@pytest.fixture
def isolated_stores(tmp_path, monkeypatch):
    """Подменяет `webapp.common.get_result_store`/`get_raw_log`, чтобы
    веб-приложение при тестах писало результаты во временный каталог."""
    import webapp.common as common

    result_store = ResultStore(base_dir=tmp_path / "results")
    raw_log = RawDataLog(base_dir=tmp_path / "raw")
    monkeypatch.setattr(common, "get_result_store", lambda: result_store)
    monkeypatch.setattr(common, "get_raw_log", lambda: raw_log)
    return result_store, raw_log


def _app_on_page(page_path: str) -> AppTest:
    at = AppTest.from_file(APP_ENTRY)
    at.run(timeout=60)
    assert not at.exception, list(at.exception)
    if page_path != "views/overview.py":
        at.switch_page(page_path)
        at.run(timeout=60)
        assert not at.exception, list(at.exception)
    return at


def _progress_text(at) -> str:
    return at.get("progress")[0].proto.text


def test_overview_page_loads_and_recalculates(isolated_stores):
    at = _app_on_page("views/overview.py")

    recalc_button = [b for b in at.button if "пересчёт" in b.label][0]
    recalc_button.click().run(timeout=120)
    assert not at.exception
    metric_values = [m.value for m in at.metric]
    assert "5" in metric_values  # населённых пунктов в реестре
    assert any("/" in v for v in metric_values)  # "N / 5" рассчитано


def test_registry_page_loads(isolated_stores):
    at = _app_on_page("views/registry.py")
    assert any("Реестр" in t.value for t in at.title)


def test_methodology_page_loads_and_has_all_components(isolated_stores):
    at = _app_on_page("views/methodology_view.py")
    assert len(at.expander) == 7  # GEO, ACC, DEM, SERV, INFRA, ECO, ECON


def test_sources_page_initial_render(isolated_stores):
    _app_on_page("views/sources.py")


def test_verification_page_loads(isolated_stores):
    _app_on_page("views/verification.py")


def test_dashboard_page_loads_without_results(isolated_stores):
    _app_on_page("views/dashboard.py")


def test_dashboard_page_shows_detail_after_recalc(isolated_stores):
    result_store, raw_log = isolated_stores
    from vulnerability_index.batch import recalculate_all
    from vulnerability_index.methodology import MethodologyRepository
    from vulnerability_index.settlements import SettlementRepository
    from vulnerability_index.source_factory import build_default_source_chains

    methodology = MethodologyRepository().latest()
    settlement_repo = SettlementRepository()
    chains = build_default_source_chains()
    recalculate_all(methodology, list(settlement_repo.all()), chains, result_store=result_store, raw_log=raw_log)

    at = _app_on_page("views/dashboard.py")
    assert any("2.83" in m.value or "2.830" in m.value for m in at.metric)


def test_dialog_wizard_prefill_and_save(isolated_stores):
    at = _app_on_page("views/dialog_wizard.py")

    prefill_btn = [b for b in at.button if "Автозаполнить" in b.label][0]
    prefill_btn.click().run(timeout=120)
    assert not at.exception
    assert any("2.83" in m.value for m in at.metric)

    save_btn = [b for b in at.button if "Сохранить результат" in b.label][0]
    save_btn.click().run(timeout=30)
    assert not at.exception


def test_dialog_wizard_reset_clears_progress(isolated_stores):
    at = _app_on_page("views/dialog_wizard.py")
    prefill_btn = [b for b in at.button if "Автозаполнить" in b.label][0]
    prefill_btn.click().run(timeout=120)
    assert "20 / 20" in _progress_text(at)

    reset_btn = [b for b in at.button if "Сбросить расчёт" in b.label][0]
    reset_btn.click().run(timeout=30)
    assert not at.exception
    assert "0 / 20" in _progress_text(at)


def test_dialog_wizard_open_indicator_shows_source_options(isolated_stores):
    at = _app_on_page("views/dialog_wizard.py")
    open_buttons = [b for b in at.button if b.label == "Открыть"]
    assert len(open_buttons) == 20  # 20 показателей методики

    open_buttons[0].click().run(timeout=60)
    assert not at.exception
    radios = at.radio
    assert len(radios) == 1
    assert "Способ получения данных" in radios[0].label
    assert "Ввести вручную" in radios[0].options
    assert "Допущение / нет данных" in radios[0].options

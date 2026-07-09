"""Состояние диалогового сбора показателей в session_state Streamlit.

В отличие от CLI-модуля (`vulnerability_index.dialog`, построенного на
блокирующих `input()`/`print()`), веб-версия работает в модели
"перерисовка при каждом взаимодействии": состояние собранных показателей
хранится в ``st.session_state`` и изменяется через модальные диалоговые
окна (``st.dialog``) — см. `webapp/views/dialog_wizard.py`.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from vulnerability_index.models import DataValue, IndicatorResult

ASSUMPTION_REASONS: list[str] = [
    "Использование ближайших доступных значений",
    "Данные смежных территорий",
    "Результаты геоинформационного анализа",
    "Экспертная оценка",
]


def _state_key(methodology_version: str, settlement_code: str) -> str:
    return f"iu_results::{methodology_version}::{settlement_code}"


def get_indicator_results(
    methodology_version: str, settlement_code: str
) -> dict[tuple[str, str], IndicatorResult]:
    key = _state_key(methodology_version, settlement_code)
    if key not in st.session_state:
        st.session_state[key] = {}
    return st.session_state[key]


def reset_indicator_results(methodology_version: str, settlement_code: str) -> None:
    st.session_state[_state_key(methodology_version, settlement_code)] = {}


def get_result(
    methodology_version: str, settlement_code: str, component_key: str, indicator_key: str
) -> Optional[IndicatorResult]:
    return get_indicator_results(methodology_version, settlement_code).get(
        (component_key, indicator_key)
    )


def finalize_indicator(
    methodology_version: str,
    settlement_code: str,
    component_key: str,
    indicator_key: str,
    indicator_spec,
    data_value: DataValue,
) -> IndicatorResult:
    score, label = indicator_spec.score(data_value.raw_value)
    result = IndicatorResult(
        key=indicator_key,
        title=indicator_spec.title,
        component_key=component_key,
        weight_within_component=indicator_spec.weight,
        data=data_value,
        score=score,
        matched_rule_label=label,
    )
    get_indicator_results(methodology_version, settlement_code)[
        (component_key, indicator_key)
    ] = result
    return result


def mark_missing(
    methodology_version: str,
    settlement_code: str,
    component_key: str,
    indicator_key: str,
    indicator_spec,
) -> IndicatorResult:
    data_value = DataValue(
        raw_value=None, source_name="—", source_kind="missing",
        unit=indicator_spec.unit, comment="Нет данных",
    )
    result = IndicatorResult(
        key=indicator_key,
        title=indicator_spec.title,
        component_key=component_key,
        weight_within_component=indicator_spec.weight,
        data=data_value,
        score=None,
    )
    get_indicator_results(methodology_version, settlement_code)[
        (component_key, indicator_key)
    ] = result
    return result


def clear_indicator(
    methodology_version: str, settlement_code: str, component_key: str, indicator_key: str
) -> None:
    get_indicator_results(methodology_version, settlement_code).pop(
        (component_key, indicator_key), None
    )


def status_badge(result: Optional[IndicatorResult]) -> str:
    if result is None:
        return "⚪ не заполнено"
    if result.is_missing:
        return "🔴 нет данных"
    if result.data.is_assumption:
        return "🟠 допущение"
    return "🟢 заполнено"


def progress(methodology, methodology_version: str, settlement_code: str) -> tuple[int, int]:
    total = sum(len(c.indicators) for c in methodology.components.values())
    done = len(get_indicator_results(methodology_version, settlement_code))
    return done, total

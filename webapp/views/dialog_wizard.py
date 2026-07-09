"""Диалоговое окно расчёта Индекса уязвимости.

Для каждого из 17 исходных показателей методики открывается модальное
диалоговое окно (`st.dialog`), где оператор выбирает способ получения
данных — автоматически по цепочке источников, из конкретного источника,
вручную или как документируемое допущение / «нет данных» (п. 4.10,
5.9 ТЗ) — и сразу видит, какой балл будет присвоен.
"""

from __future__ import annotations

import streamlit as st

from vulnerability_index.aggregate import aggregate_index_result
from vulnerability_index.datasources.base import DataNotAvailable
from vulnerability_index.datasources.chain import DataSourceChain
from vulnerability_index.models import DataValue
from webapp.common import (
    get_latest_methodology,
    get_raw_log,
    get_result_store,
    get_settlement_repo,
    get_source_chains,
    settlement_options,
)
from webapp.logic import (
    ASSUMPTION_REASONS,
    clear_indicator,
    finalize_indicator,
    get_indicator_results,
    get_result,
    mark_missing,
    reset_indicator_results,
    status_badge,
)
from webapp.render import render_breakdown, render_component_chart, render_summary

st.title("🧮 Диалоговый расчёт Индекса уязвимости")
st.caption(
    "Заполните все показатели ниже — по каждому откроется диалоговое окно "
    "выбора способа получения данных. Показатели можно заполнять в любом "
    "порядке и изменять после заполнения."
)

methodology = get_latest_methodology()
settlement_repo = get_settlement_repo()
source_chains = get_source_chains()
result_store = get_result_store()
raw_log = get_raw_log()

options = settlement_options()
selected_code = st.selectbox(
    "Населённый пункт",
    options=list(options.keys()),
    format_func=lambda code: options[code],
    key="dialog_settlement_code",
)
settlement = settlement_repo.get(selected_code)

top_cols = st.columns([1, 1, 4])
with top_cols[0]:
    if st.button("↺ Сбросить расчёт", width="stretch"):
        reset_indicator_results(methodology.version, settlement.code)
        st.rerun()
with top_cols[1]:
    prefill = st.button("⚡ Автозаполнить всё", width="stretch",
                         help="Пройти по цепочкам источников для всех показателей без диалога")

if prefill:
    with st.spinner("Сбор данных по всем показателям..."):
        for component_key, component_spec in methodology.components.items():
            for indicator_key, indicator_spec in component_spec.indicators.items():
                if get_result(methodology.version, settlement.code, component_key, indicator_key) is not None:
                    continue  # не перезаписываем уже заполненные (в т.ч. вручную/допущением) значения
                chain = source_chains.get((component_key, indicator_key))
                if chain is None:
                    continue
                outcome = chain.fetch(settlement, component_key, indicator_key, indicator_spec)
                raw_log.log_fetch(settlement.code, component_key, indicator_key, outcome)
                if outcome.succeeded:
                    finalize_indicator(
                        methodology.version, settlement.code, component_key, indicator_key,
                        indicator_spec, outcome.value,
                    )
    st.rerun()

indicator_results = get_indicator_results(methodology.version, settlement.code)
total = sum(len(c.indicators) for c in methodology.components.values())
done = len(indicator_results)
st.progress(done / total if total else 0, text=f"Заполнено показателей: {done} / {total}")

st.divider()


@st.dialog("Заполнение показателя", width="large")
def indicator_dialog(component_key: str, indicator_key: str) -> None:
    component_spec = methodology.components[component_key]
    indicator_spec = component_spec.indicators[indicator_key]
    chain = source_chains.get((component_key, indicator_key))
    sources = chain.sources if chain else []

    st.subheader(f"{indicator_spec.title}")
    st.caption(
        f"Компонент {component_key} — {component_spec.title}. "
        f"Вес показателя внутри компонента: {indicator_spec.weight:g}."
        + (f" Единица измерения: {indicator_spec.unit}." if indicator_spec.unit else "")
    )
    if indicator_spec.notes:
        st.caption(f"Примечание методики: {indicator_spec.notes}")

    existing = get_result(methodology.version, settlement.code, component_key, indicator_key)
    if existing is not None:
        st.info(
            f"Текущее значение: **{existing.data.raw_value}** "
            f"(балл {existing.score if existing.score is not None else '—'}, "
            f"источник: {existing.data.source_name})"
        )

    method_options = ["Ввести вручную", "Допущение / нет данных"]
    if sources:
        method_options = ["Авто (по цепочке источников)"] + [
            f"Источник напрямую: {s.name}" for s in sources
        ] + method_options
    method = st.radio("Способ получения данных", method_options, key=f"method_{component_key}_{indicator_key}")

    outcome_key = f"pending_outcome_{component_key}_{indicator_key}"

    if method == "Авто (по цепочке источников)":
        if st.button("📡 Получить данные по цепочке источников"):
            outcome = DataSourceChain(sources).fetch(settlement, component_key, indicator_key, indicator_spec)
            raw_log.log_fetch(settlement.code, component_key, indicator_key, outcome)
            st.session_state[outcome_key] = outcome
        outcome = st.session_state.get(outcome_key)
        if outcome is not None:
            with st.expander("Журнал попыток", expanded=not outcome.succeeded):
                for attempt in outcome.attempts:
                    icon = "✅" if attempt.success else "❌"
                    st.write(f"{icon} {attempt.source_name} ({attempt.source_kind})"
                             + (f" — {attempt.error}" if attempt.error else ""))
            if outcome.succeeded:
                st.success(f"Получено значение: **{outcome.value.raw_value}** "
                           f"(источник: {outcome.value.source_name})")
                col_a, col_b = st.columns(2)
                if col_a.button("✅ Принять значение", type="primary"):
                    finalize_indicator(
                        methodology.version, settlement.code, component_key, indicator_key,
                        indicator_spec, outcome.value,
                    )
                    del st.session_state[outcome_key]
                    st.rerun()
                if col_b.button("✖️ Отклонить, ввести иначе"):
                    del st.session_state[outcome_key]
                    st.rerun()
            else:
                st.error("Ни один источник не вернул данные — выберите другой способ ниже.")

    elif method.startswith("Источник напрямую:"):
        source_name = method.split(":", 1)[1].strip()
        source = next(s for s in sources if s.name == source_name)
        if st.button("📡 Запросить у выбранного источника"):
            try:
                value = source.fetch(settlement, component_key, indicator_key, indicator_spec)
                st.session_state[outcome_key] = value
            except DataNotAvailable as exc:
                st.session_state[outcome_key] = None
                st.error(f"Источник недоступен: {exc}")
        value = st.session_state.get(outcome_key)
        if isinstance(value, DataValue):
            st.success(f"Получено значение: **{value.raw_value}**")
            if st.button("✅ Принять значение", type="primary"):
                finalize_indicator(
                    methodology.version, settlement.code, component_key, indicator_key,
                    indicator_spec, value,
                )
                del st.session_state[outcome_key]
                st.rerun()

    elif method == "Ввести вручную":
        if indicator_spec.type == "options":
            choices = indicator_spec.option_choices()
            labels = [f"{label} (балл {score:g})" for _, label, score in choices]
            idx = st.selectbox("Значение показателя", options=range(len(choices)),
                                format_func=lambda i: labels[i], key=f"manual_opt_{component_key}_{indicator_key}")
            raw_value = choices[idx][0]
        else:
            raw_value = st.number_input(
                f"Значение показателя{' (' + indicator_spec.unit + ')' if indicator_spec.unit else ''}",
                key=f"manual_num_{component_key}_{indicator_key}", step=1.0, format="%.2f",
            )
        comment = st.text_input("Документ-основание (необязательно)", key=f"manual_doc_{component_key}_{indicator_key}")
        if st.button("💾 Сохранить значение", type="primary"):
            data_value = DataValue(
                raw_value=raw_value, source_name="Ручной ввод оператором", source_kind="manual",
                comment=comment or None, unit=indicator_spec.unit,
            )
            finalize_indicator(
                methodology.version, settlement.code, component_key, indicator_key,
                indicator_spec, data_value,
            )
            st.rerun()

    else:  # "Допущение / нет данных"
        no_data = st.checkbox("Показатель действительно недоступен — пометить «нет данных»",
                               key=f"nodata_{component_key}_{indicator_key}")
        if no_data:
            st.warning(
                "Ответственное лицо будет уведомлено об отсутствии данных по этому "
                "показателю (п. 4.10, 5.10 ТЗ)."
            )
            if st.button("🚫 Отметить «нет данных»", type="primary"):
                mark_missing(methodology.version, settlement.code, component_key, indicator_key, indicator_spec)
                st.rerun()
        else:
            reason = st.selectbox("Основание допущения (п. 4.10 методики)", ASSUMPTION_REASONS,
                                   key=f"reason_{component_key}_{indicator_key}")
            if indicator_spec.type == "options":
                choices = indicator_spec.option_choices()
                labels = [f"{label} (балл {score:g})" for _, label, score in choices]
                idx = st.selectbox("Допущенное значение", options=range(len(choices)),
                                    format_func=lambda i: labels[i],
                                    key=f"assume_opt_{component_key}_{indicator_key}")
                raw_value = choices[idx][0]
            else:
                raw_value = st.number_input(
                    f"Допущенное значение{' (' + indicator_spec.unit + ')' if indicator_spec.unit else ''}",
                    key=f"assume_num_{component_key}_{indicator_key}", step=1.0, format="%.2f",
                )
            comment = st.text_area("Комментарий к допущению", key=f"assume_comment_{component_key}_{indicator_key}")
            if st.button("💾 Сохранить допущение", type="primary"):
                data_value = DataValue(
                    raw_value=raw_value,
                    source_name=f"Допущение оператора/методолога ({reason})",
                    source_kind="assumption", is_assumption=True, assumption_reason=reason,
                    comment=comment or None, unit=indicator_spec.unit,
                )
                finalize_indicator(
                    methodology.version, settlement.code, component_key, indicator_key,
                    indicator_spec, data_value,
                )
                st.rerun()

    if existing is not None and st.button("🗑️ Очистить значение"):
        clear_indicator(methodology.version, settlement.code, component_key, indicator_key)
        st.rerun()


for component_key, component_spec in methodology.components.items():
    filled_in_component = sum(
        1 for ind_key in component_spec.indicators
        if get_result(methodology.version, settlement.code, component_key, ind_key) is not None
    )
    with st.expander(
        f"{component_key} — {component_spec.title} (вес {component_spec.weight:g}) "
        f"[{filled_in_component}/{len(component_spec.indicators)}]",
        expanded=True,
    ):
        if component_spec.notes:
            st.caption(component_spec.notes)
        for indicator_key, indicator_spec in component_spec.indicators.items():
            result = get_result(methodology.version, settlement.code, component_key, indicator_key)
            row = st.columns([3, 2, 2, 1])
            row[0].markdown(f"**{indicator_spec.title}**"
                             + (f" _{indicator_spec.unit}_" if indicator_spec.unit else ""))
            row[1].markdown(status_badge(result))
            if result is not None:
                score_str = f"{result.score:g}" if result.score is not None else "—"
                row[2].markdown(f"{result.data.raw_value} → балл {score_str}")
            else:
                row[2].markdown("—")
            if row[3].button("Открыть", key=f"open_{component_key}_{indicator_key}"):
                indicator_dialog(component_key, indicator_key)

st.divider()

if done == 0:
    st.info("Заполните хотя бы один показатель, чтобы увидеть предварительный расчёт.")
else:
    result = aggregate_index_result(methodology, settlement, indicator_results)
    st.subheader("Предварительный результат")
    render_summary(result, methodology)
    render_component_chart(result, methodology.value_range)
    render_breakdown(result)

    save_cols = st.columns([1, 3])
    with save_cols[0]:
        if st.button("💾 Сохранить результат", type="primary", width="stretch"):
            result_store.save(result)
            st.success(f"Результат сохранён для {settlement.name} ({result.calculated_at:%Y-%m-%d %H:%M} UTC).")
    with save_cols[1]:
        st.caption(
            "Результат сохраняется со статусом «не верифицировано» — статус "
            "верификации можно изменить на странице «Верификация»."
        )

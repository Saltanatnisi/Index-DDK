"""Общие функции отображения результата расчёта — используются на
странице диалогового расчёта и на дашборде, чтобы детализация ИУ
выглядела одинаково везде."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from vulnerability_index.models import IndexResult


def render_summary(result: IndexResult, methodology) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Индекс уязвимости (ИУ)", f"{result.value:.3f}",
        help=f"Диапазон {methodology.value_range[0]:g}–{methodology.value_range[1]:g}",
    )
    col2.metric("Категория уязвимости", result.category or "не определена")
    col3.metric("Статус верификации", result.verification_status.value)
    if result.has_assumptions:
        st.info(
            "⚠️ В расчёте использованы допущенные (не первичные) значения по "
            "отдельным показателям — см. детализацию ниже.",
            icon="⚠️",
        )
    if any(i.is_missing for c in result.components for i in c.indicators):
        st.error(
            "⚠️ По части показателей нет данных — их вес перенормирован среди "
            "остальных показателей компонента. Рекомендуется дособрать данные.",
            icon="⚠️",
        )
    if not methodology.categories_approved():
        st.caption(
            "Пороговые значения категорий уязвимости пока не утверждены "
            "уполномоченным органом — показанная категория рассчитана по "
            "временным значениям (см. страницу «Методика»)."
        )


def render_component_chart(result: IndexResult, value_range: tuple[float, float] = (0.0, 3.0)) -> None:
    order = [c.key for c in result.components]
    comp_df = pd.DataFrame(
        [
            {
                "Компонент": c.key,
                "Название": c.title,
                "Значение": c.value if c.value is not None else 0.0,
                "Есть данные": c.value is not None,
            }
            for c in result.components
        ]
    )
    chart = (
        alt.Chart(comp_df)
        .mark_bar()
        .encode(
            x=alt.X("Компонент:N", sort=order, title=None),
            y=alt.Y("Значение:Q", scale=alt.Scale(domain=list(value_range)), title="Балл компонента"),
            color=alt.condition(
                alt.datum["Есть данные"], alt.value("#2b6cb0"), alt.value("#a0aec0")
            ),
            tooltip=[
                alt.Tooltip("Название:N", title="Компонент"),
                alt.Tooltip("Значение:Q", title="Значение", format=".3f"),
            ],
        )
        .properties(height=280)
    )
    st.altair_chart(chart, width="stretch")


def render_breakdown(result: IndexResult) -> None:
    for component in result.components:
        value_str = f"{component.value:.3f}" if component.value is not None else "нет данных"
        with st.expander(f"{component.key} — {component.title} (вес {component.weight:g}): {value_str}"):
            if not component.indicators:
                st.caption("Нет собранных показателей.")
                continue
            rows = [
                {
                    "Показатель": indicator.title,
                    "Значение": indicator.data.raw_value,
                    "Балл": indicator.score,
                    "Источник": indicator.data.source_name,
                    "Особенность": (
                        "нет данных" if indicator.is_missing
                        else ("допущение" if indicator.data.is_assumption else "")
                    ),
                    "Комментарий": indicator.data.comment or "",
                }
                for indicator in component.indicators
            ]
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def result_to_export_rows(result: IndexResult) -> list[dict]:
    rows = []
    for component in result.components:
        for indicator in component.indicators:
            rows.append(
                {
                    "Населённый пункт": result.settlement.name,
                    "Код": result.settlement.code,
                    "Компонент": component.key,
                    "Показатель": indicator.title,
                    "Значение": indicator.data.raw_value,
                    "Балл": indicator.score,
                    "Источник": indicator.data.source_name,
                    "Допущение": indicator.data.is_assumption,
                    "Дата получения": indicator.data.obtained_at.isoformat(),
                    "Значение компонента": component.value,
                    "ИУ": result.value,
                    "Категория": result.category,
                    "Версия методики": result.methodology_version,
                    "Дата расчёта": result.calculated_at.isoformat(),
                }
            )
    return rows

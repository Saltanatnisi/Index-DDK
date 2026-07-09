"""Просмотр действующей методики: компоненты, веса, балльные шкалы,
версии, пороги категорий (раздел 4 ТЗ)."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from webapp.common import get_methodology_repo

st.title("📐 Методика расчёта Индекса")

repo = get_methodology_repo()
versions = repo.all_versions()

version_labels = {m.version: f"{m.version} (действует с {m.effective_date})" for m in versions}
selected_version = st.selectbox(
    "Версия методики", options=list(version_labels.keys()), format_func=lambda v: version_labels[v],
    index=len(versions) - 1,
)
methodology = repo.get_by_version(selected_version)

st.markdown(f"### {methodology.title}")
st.write(
    f"**Версия:** {methodology.version} · **Действует с:** {methodology.effective_date} · "
    f"**Диапазон значений ИУ:** {methodology.value_range[0]:g}–{methodology.value_range[1]:g}"
)
if methodology.approved_by:
    st.write(f"**Утверждена:** {methodology.approved_by}")
else:
    st.warning("Реквизиты утверждения методики не заполнены в конфигурации.")

st.markdown(
    "**ИУ = 0,20·GEO + 0,30·ACC + 0,10·DEM + 0,10·SERV + 0,10·INFRA + 0,10·ECO + 0,10·ECON**"
)

weight_df = pd.DataFrame(
    [{"Компонент": k, "Название": c.title, "Вес в ИУ": c.weight} for k, c in methodology.components.items()]
)
st.bar_chart(weight_df.set_index("Компонент")["Вес в ИУ"])

for component_key, component_spec in methodology.components.items():
    with st.expander(f"{component_key} — {component_spec.title} (вес {component_spec.weight:g})"):
        if component_spec.notes:
            st.caption(component_spec.notes)
        for indicator_key, indicator_spec in component_spec.indicators.items():
            st.markdown(
                f"**{indicator_spec.title}** (вес {indicator_spec.weight:g} внутри {component_key})"
                + (f" — единица: {indicator_spec.unit}" if indicator_spec.unit else "")
            )
            if indicator_spec.notes:
                st.caption(indicator_spec.notes)
            if indicator_spec.type == "numeric_thresholds":
                scale_rows = [
                    {"Интервал": rule.get("label", ""), "Балл": rule["score"]}
                    for rule in indicator_spec.rules or []
                ]
            else:
                scale_rows = [
                    {"Интервал": label, "Балл": score}
                    for _, label, score in indicator_spec.option_choices()
                ]
            st.table(pd.DataFrame(scale_rows))

st.divider()
st.subheader("Категоризация населённых пунктов по уровню уязвимости")
st.write(f"Пороги утверждены: {'да' if methodology.categories_approved() else '⚠️ нет — временная заглушка'}")
threshold_rows = []
for rule in methodology.category_thresholds():
    parts = []
    if "gt" in rule:
        parts.append(f"> {rule['gt']}")
    if "gte" in rule:
        parts.append(f">= {rule['gte']}")
    if "lt" in rule:
        parts.append(f"< {rule['lt']}")
    if "lte" in rule:
        parts.append(f"<= {rule['lte']}")
    threshold_rows.append({"Условие по ИУ": " и ".join(parts), "Категория": rule["category"]})
st.table(pd.DataFrame(threshold_rows))

st.divider()
st.subheader("Пересчёт по дате: какая версия действовала")
picked_date = st.date_input("Дата", value=date.today())
try:
    applicable = repo.get_for_date(picked_date)
    st.success(f"На {picked_date} действовала версия методики **{applicable.version}** "
               f"(с {applicable.effective_date}).")
except Exception as exc:  # noqa: BLE001
    st.error(str(exc))

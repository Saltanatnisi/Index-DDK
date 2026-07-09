"""Эталонный реестр населённых пунктов (п. 5.11, 6.1 ТЗ)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from webapp.common import get_result_store, get_settlement_repo

st.title("🗂️ Реестр населённых пунктов")
st.caption(
    "Единый эталонный справочник, к которому привязываются все исходные "
    "показатели и результаты расчёта Индекса (п. 5.11 ТЗ). Текущий источник: "
    "`data/reference/settlements.csv` — демонстрационный набор из 5 населённых "
    "пунктов; в промышленной эксплуатации заменяется полным реестром."
)

settlement_repo = get_settlement_repo()
result_store = get_result_store()
settlements = list(settlement_repo.all())

rows = []
for s in settlements:
    latest = result_store.latest(s.code)
    rows.append(
        {
            "Код": s.code,
            "Название": s.name,
            "Район": s.district,
            "Область": s.region,
            "Широта": s.lat,
            "Долгота": s.lon,
            "Категория территории": ", ".join(s.categories) or "—",
            "Последний ИУ": round(latest.value, 3) if latest else None,
            "Количество расчётов в истории": len(result_store.history(s.code)),
        }
    )
df = pd.DataFrame(rows)

query = st.text_input("Поиск по названию / району / области / коду")
if query:
    matches = {s.code for s in settlement_repo.search(query)}
    df = df[df["Код"].isin(matches)]

st.dataframe(df, width="stretch", hide_index=True)
st.download_button(
    "⬇️ Скачать реестр (CSV)",
    data=df.to_csv(index=False).encode("utf-8-sig"),
    file_name="settlements_registry.csv",
    mime="text/csv",
)

st.divider()
st.subheader("Карта")
map_df = pd.DataFrame([{"lat": s.lat, "lon": s.lon} for s in settlements if s.lat and s.lon])
if not map_df.empty:
    st.map(map_df, latitude="lat", longitude="lon")

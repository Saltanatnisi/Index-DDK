"""Дашборд: текущее значение Индекса, динамика, разбивка по компонентам,
агрегация на уровень района/области, карта, экспорт (раздел 6.3 ТЗ)."""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from webapp.common import get_latest_methodology, get_result_store, get_settlement_repo
from webapp.render import render_breakdown, render_component_chart, render_summary, result_to_export_rows

st.title("📊 Дашборд Индекса уязвимости")

methodology = get_latest_methodology()
settlement_repo = get_settlement_repo()
result_store = get_result_store()
settlements = list(settlement_repo.all())

latest_by_code = {s.code: result_store.latest(s.code) for s in settlements}

overview_rows = []
for s in settlements:
    r = latest_by_code[s.code]
    overview_rows.append(
        {
            "Код": s.code,
            "Населённый пункт": s.name,
            "Район": s.district,
            "Область": s.region,
            "Категория территории": ", ".join(s.categories) or "—",
            "ИУ": round(r.value, 3) if r else None,
            "Категория уязвимости": r.category if r else None,
            "Статус верификации": r.verification_status.value if r else "—",
            "Есть допущения": (r.has_assumptions if r else False),
            "Дата расчёта": r.calculated_at if r else None,
        }
    )
overview_df = pd.DataFrame(overview_rows)

st.subheader("Фильтры")
f1, f2, f3 = st.columns(3)
regions = f1.multiselect("Область", sorted(overview_df["Область"].unique()))
districts_pool = overview_df[overview_df["Область"].isin(regions)] if regions else overview_df
districts = f2.multiselect("Район", sorted(districts_pool["Район"].unique()))
categories = f3.multiselect(
    "Категория уязвимости", sorted([c for c in overview_df["Категория уязвимости"].dropna().unique()])
)

filtered = overview_df.copy()
if regions:
    filtered = filtered[filtered["Область"].isin(regions)]
if districts:
    filtered = filtered[filtered["Район"].isin(districts)]
if categories:
    filtered = filtered[filtered["Категория уязвимости"].isin(categories)]

st.subheader(f"Населённые пункты ({len(filtered)} из {len(overview_df)})")
st.dataframe(filtered, width="stretch", hide_index=True)

csv_bytes = filtered.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "⬇️ Экспорт таблицы (CSV)", data=csv_bytes, file_name="index_uyazvimosti_svod.csv", mime="text/csv"
)

st.divider()

st.subheader("Агрегация по территориям (п. 6.2 ТЗ)")
agg_level = st.radio("Уровень агрегации", ["Район", "Область"], horizontal=True)
computed = filtered.dropna(subset=["ИУ"])
if computed.empty:
    st.info("Нет рассчитанных значений Индекса для отображения агрегации по выбранным фильтрам.")
else:
    agg = (
        computed.groupby(agg_level)["ИУ"]
        .agg(["mean", "median", "count"])
        .rename(columns={"mean": "Среднее", "median": "Медиана", "count": "Кол-во н.п."})
        .sort_values("Среднее", ascending=False)
    )
    col_a, col_b = st.columns(2)
    with col_a:
        st.dataframe(agg.round(3), width="stretch")
    with col_b:
        st.bar_chart(agg["Среднее"])

    st.caption("Доля населённых пунктов по категории уязвимости, %")
    category_share = (
        computed.groupby([agg_level, "Категория уязвимости"]).size().unstack(fill_value=0)
    )
    category_share_pct = category_share.div(category_share.sum(axis=1), axis=0) * 100
    st.bar_chart(category_share_pct)

st.divider()

st.subheader("Карта населённых пунктов")
map_df = pd.DataFrame(
    [{"lat": s.lat, "lon": s.lon, "Населённый пункт": s.name} for s in settlements if s.lat and s.lon]
)
if not map_df.empty:
    st.map(map_df, latitude="lat", longitude="lon", size=200)
else:
    st.info("Для населённых пунктов реестра не заданы координаты.")

st.divider()

st.subheader("Детализация и динамика по населённому пункту")
code_options = {s.code: str(s) for s in settlements}
selected_code = st.selectbox(
    "Населённый пункт", options=list(code_options.keys()), format_func=lambda c: code_options[c]
)
result = latest_by_code[selected_code]

if result is None:
    st.warning(
        "Для этого населённого пункта пока нет сохранённого расчёта — выполните "
        "расчёт на странице «Диалоговый расчёт» или запустите полный пересчёт на "
        "странице «Обзор»."
    )
else:
    render_summary(result, methodology)
    render_component_chart(result, methodology.value_range)
    render_breakdown(result)

    history_entries = result_store.history(selected_code)
    if len(history_entries) > 1:
        st.markdown("**Динамика Индекса по периодам расчёта**")
        hist_df = pd.DataFrame(history_entries)
        hist_df["calculated_at"] = pd.to_datetime(hist_df["calculated_at"])
        hist_df = hist_df.sort_values("calculated_at").set_index("calculated_at")
        st.line_chart(hist_df["value"].rename("ИУ"))
    else:
        st.caption("Пока сохранён только один расчёт — динамика появится после повторного пересчёта.")

    export_rows = result_to_export_rows(result)
    export_df = pd.DataFrame(export_rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Детализация ИУ")
    st.download_button(
        "⬇️ Экспорт детализации (XLSX)",
        data=buf.getvalue(),
        file_name=f"iu_{selected_code}_detail.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

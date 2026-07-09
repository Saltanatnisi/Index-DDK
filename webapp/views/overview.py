"""Обзорная страница: ключевые показатели, статус расчётов, быстрые
действия (полный пересчёт по реестру)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from vulnerability_index.batch import recalculate_all
from webapp.common import (
    get_latest_methodology,
    get_raw_log,
    get_result_store,
    get_settlement_repo,
    get_source_chains,
)

st.title("🏔️ Индекс уязвимости высокогорных, отдалённых и приграничных населённых пунктов КР")
st.caption(
    "Диалоговый модуль расчёта Индекса с автоматизированным сбором данных из "
    "государственных информационных систем, портала Нацстаткомитета КР и "
    "открытых источников — по «Методике расчёта Индекса уязвимости...»."
)

methodology = get_latest_methodology()
settlement_repo = get_settlement_repo()
result_store = get_result_store()
settlements = list(settlement_repo.all())

latest_results = {s.code: result_store.latest(s.code) for s in settlements}
computed = [r for r in latest_results.values() if r is not None]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Населённых пунктов в реестре", len(settlements))
col2.metric("Рассчитано (есть история)", f"{len(computed)} / {len(settlements)}")
col3.metric(
    "Средний ИУ (по последним расчётам)",
    f"{(sum(r.value for r in computed) / len(computed)):.2f}" if computed else "—",
)
col4.metric("Версия методики", f"{methodology.version} (с {methodology.effective_date})")

if not methodology.categories_approved():
    st.warning(
        "Пороговые значения категорий уязвимости пока не утверждены уполномоченным "
        "органом (раздел 4.9, приложение 5 ТЗ) — используются временные значения. "
        "Отредактируйте `vulnerability_index/config/methodology_v1.yaml`, когда "
        "пороги будут утверждены."
    )

st.divider()

left, right = st.columns([2, 1])

with left:
    st.subheader("Статус по населённым пунктам")
    rows = []
    for s in settlements:
        r = latest_results[s.code]
        rows.append(
            {
                "Код": s.code,
                "Населённый пункт": s.name,
                "Район": s.district,
                "Область": s.region,
                "ИУ": round(r.value, 3) if r else None,
                "Категория": r.category if r else "не рассчитан",
                "Статус верификации": r.verification_status.value if r else "—",
                "Дата расчёта": r.calculated_at.strftime("%Y-%m-%d %H:%M") if r else "—",
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)

with right:
    st.subheader("Распределение по категориям")
    if computed:
        counts = pd.Series([r.category for r in computed]).value_counts()
        st.bar_chart(counts)
    else:
        st.info("Пока нет ни одного расчёта.")

    st.subheader("Быстрые действия")
    st.caption(
        "Полный автоматический пересчёт по всем населённым пунктам "
        "(п. 4.10, 6.2 ТЗ) — без вопросов оператору; недостающие показатели "
        "помечаются «нет данных» и требуют уточнения через диалоговый расчёт."
    )
    if st.button("🔄 Запустить полный пересчёт", type="primary", width="stretch"):
        with st.spinner("Выполняется сбор данных из всех источников и расчёт Индекса..."):
            source_chains = get_source_chains()
            raw_log = get_raw_log()
            recalculate_all(
                methodology, settlements, source_chains, result_store=result_store, raw_log=raw_log
            )
        st.success("Пересчёт завершён.")
        st.rerun()

st.divider()
st.page_link("views/dialog_wizard.py", label="➡️ Открыть диалоговый расчёт для одного населённого пункта", icon="🧮")
st.page_link("views/dashboard.py", label="➡️ Открыть дашборд с детализацией и динамикой", icon="📊")

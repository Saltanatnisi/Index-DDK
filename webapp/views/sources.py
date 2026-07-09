"""Источники данных: настроенные цепочки, проверка доступности, журнал
запросов/ответов (раздел 5.9, 5.10 ТЗ)."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from webapp.common import (
    get_latest_methodology,
    get_raw_log,
    get_settlement_repo,
    get_source_chains,
)

st.title("🔌 Источники данных")
st.caption(
    "Для каждого показателя настроена цепочка источников с приоритетом: "
    "ведомственные выгрузки, REST API существующих автоматизированных "
    "платформ, портал Национального статистического комитета КР, открытые "
    "интернет-геосервисы. При недоступности источника модуль автоматически "
    "переходит к следующему в цепочке (п. 5.9, 5.10 ТЗ)."
)

methodology = get_latest_methodology()
source_chains = get_source_chains()
settlement_repo = get_settlement_repo()
raw_log = get_raw_log()

st.subheader("Настроенные цепочки источников")
rows = []
for component_key, component_spec in methodology.components.items():
    for indicator_key, indicator_spec in component_spec.indicators.items():
        chain = source_chains.get((component_key, indicator_key))
        chain_str = " → ".join(f"{s.name} [{s.kind}]" for s in chain.sources) if chain else "не настроено"
        rows.append(
            {
                "Компонент": component_key,
                "Показатель": indicator_spec.title,
                "Цепочка источников (по приоритету)": chain_str,
            }
        )
st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

st.divider()
st.subheader("Проверка доступности источников")
options = {s.code: str(s) for s in settlement_repo.all()}
selected_code = st.selectbox("Населённый пункт для проверки", options=list(options.keys()), format_func=lambda c: options[c])
settlement = settlement_repo.get(selected_code)

if st.button("▶️ Проверить все источники для этого населённого пункта"):
    check_rows = []
    with st.spinner("Обращение к источникам..."):
        for component_key, component_spec in methodology.components.items():
            for indicator_key, indicator_spec in component_spec.indicators.items():
                chain = source_chains.get((component_key, indicator_key))
                if chain is None:
                    continue
                for source in chain.sources:
                    try:
                        value = source.fetch(settlement, component_key, indicator_key, indicator_spec)
                        check_rows.append(
                            {
                                "Компонент.Показатель": f"{component_key}.{indicator_key}",
                                "Источник": source.name,
                                "Тип": source.kind,
                                "Статус": "✅ доступен",
                                "Значение": str(value.raw_value),
                            }
                        )
                    except Exception as exc:  # noqa: BLE001 — показываем любую ошибку коннектора оператору
                        check_rows.append(
                            {
                                "Компонент.Показатель": f"{component_key}.{indicator_key}",
                                "Источник": source.name,
                                "Тип": source.kind,
                                "Статус": "❌ недоступен",
                                "Значение": str(exc),
                            }
                        )
    st.dataframe(pd.DataFrame(check_rows), width="stretch", hide_index=True)

st.divider()
st.subheader("Журнал запросов и ответов (аудит ETL)")
log_path = raw_log.base_dir / f"{selected_code}.jsonl"
if log_path.exists():
    lines = log_path.read_text(encoding="utf-8").splitlines()
    st.caption(f"Последние {min(50, len(lines))} записей из {len(lines)}")
    records = [json.loads(line) for line in lines[-50:]]
    log_rows = [
        {
            "Время": r["timestamp"],
            "Показатель": f"{r['component']}.{r['indicator']}",
            "Успех": "да" if r["succeeded"] else "нет",
            "Попытки": len(r["attempts"]),
            "Значение": str(r["value"]["raw_value"]) if r["value"] else "нет данных",
        }
        for r in reversed(records)
    ]
    st.dataframe(pd.DataFrame(log_rows), width="stretch", hide_index=True)
    with st.expander("Полные записи (JSON)"):
        st.json(list(reversed(records)))
else:
    st.info("Для этого населённого пункта пока нет записей в журнале — выполните проверку или расчёт.")

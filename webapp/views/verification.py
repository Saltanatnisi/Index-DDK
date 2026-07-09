"""Верификация расчётов (п. 5.12 ТЗ): районные администрации и органы
местного самоуправления совместно с уполномоченным органом подтверждают
результаты сбора данных и расчёта Индекса."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from vulnerability_index.models import VerificationStatus
from webapp.common import get_result_store, get_settlement_repo

st.title("✅ Верификация результатов расчёта")
st.caption(
    "Каждый расчёт хранится со статусом верификации: «не верифицировано» / "
    "«на верификации» / «верифицировано», с возможностью зафиксировать "
    "замечания верифицирующей стороны."
)

settlement_repo = get_settlement_repo()
result_store = get_result_store()
settlements = list(settlement_repo.all())

rows = []
for s in settlements:
    r = result_store.latest(s.code)
    rows.append(
        {
            "Код": s.code,
            "Населённый пункт": s.name,
            "ИУ": round(r.value, 3) if r else None,
            "Статус верификации": r.verification_status.value if r else "—",
            "Комментарий": (r.verification_comment or "") if r else "",
            "Дата расчёта": r.calculated_at if r else None,
        }
    )
df = pd.DataFrame(rows)
st.dataframe(df, width="stretch", hide_index=True)

st.divider()
st.subheader("Изменить статус верификации")
options = {s.code: str(s) for s in settlements}
selected_code = st.selectbox("Населённый пункт", options=list(options.keys()), format_func=lambda c: options[c])

result = result_store.latest(selected_code)
if result is None:
    st.info("Для этого населённого пункта пока нет расчёта.")
else:
    st.write(f"Текущий статус: **{result.verification_status.value}**")
    status_labels = {s: s.value for s in VerificationStatus}
    new_status = st.selectbox(
        "Новый статус", options=list(status_labels.keys()), format_func=lambda s: status_labels[s],
        index=list(status_labels.keys()).index(result.verification_status),
    )
    comment = st.text_area("Замечания верифицирующей стороны", value=result.verification_comment or "")
    if st.button("💾 Сохранить статус", type="primary"):
        result_store.update_verification(result, new_status, comment or None)
        st.success("Статус верификации обновлён.")
        st.rerun()

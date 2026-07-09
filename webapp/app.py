"""Точка входа веб-приложения.

Запуск:

    streamlit run webapp/app.py

Собирает страницы (диалоговый расчёт, дашборд, реестр, источники
данных, методика, верификация) через современный API `st.navigation`,
что даёт полный контроль над заголовками/иконками разделов независимо
от имён файлов.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit добавляет в sys.path только каталог главного скрипта
# (webapp/), а не корень репозитория — без этого не резолвятся импорты
# `webapp.*` и `vulnerability_index.*` при запуске `streamlit run
# webapp/app.py` из произвольного рабочего каталога.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from webapp.common import APP_TITLE  # noqa: E402

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = [
    st.Page("views/overview.py", title="Обзор", icon="🏠", default=True),
    st.Page("views/dialog_wizard.py", title="Диалоговый расчёт", icon="🧮"),
    st.Page("views/dashboard.py", title="Дашборд", icon="📊"),
    st.Page("views/registry.py", title="Реестр населённых пунктов", icon="🗂️"),
    st.Page("views/sources.py", title="Источники данных", icon="🔌"),
    st.Page("views/methodology_view.py", title="Методика", icon="📐"),
    st.Page("views/verification.py", title="Верификация", icon="✅"),
]

st.sidebar.title("🏔️ Индекс уязвимости")
st.sidebar.caption("Высокогорные, отдалённые и приграничные населённые пункты КР")

nav = st.navigation(pages)
nav.run()

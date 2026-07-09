"""Общие ресурсы веб-приложения: методика, реестр населённых пунктов,
цепочки источников данных, хранилища результатов/сырых данных.

Все функции обёрнуты в ``st.cache_resource``, чтобы дорогие объекты
(разбор YAML, чтение CSV-реестра, экземпляры коннекторов с их
внутренними pandas-кэшами) создавались один раз на сессию Streamlit,
а не при каждом перерисовывании страницы.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from vulnerability_index.methodology import Methodology, MethodologyRepository
from vulnerability_index.settlements import SettlementRepository
from vulnerability_index.source_factory import build_default_source_chains
from vulnerability_index.storage import RawDataLog, ResultStore

APP_TITLE = "Индекс уязвимости высокогорных, отдалённых и приграничных населённых пунктов КР"


@st.cache_resource(show_spinner=False)
def get_methodology_repo() -> MethodologyRepository:
    return MethodologyRepository()


def get_latest_methodology() -> Methodology:
    return get_methodology_repo().latest()


@st.cache_resource(show_spinner=False)
def get_settlement_repo() -> SettlementRepository:
    return SettlementRepository()


@st.cache_resource(show_spinner=False)
def get_source_chains():
    return build_default_source_chains()


@st.cache_resource(show_spinner=False)
def get_result_store() -> ResultStore:
    return ResultStore()


@st.cache_resource(show_spinner=False)
def get_raw_log() -> RawDataLog:
    return RawDataLog()


def settlement_options() -> dict[str, str]:
    """Словарь код -> подпись для выпадающих списков выбора н.п."""
    repo = get_settlement_repo()
    return {s.code: str(s) for s in repo.all()}

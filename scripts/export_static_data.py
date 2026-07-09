"""Экспорт методики и демо-данных в JSON для статической (Netlify)
версии диалогового окна и дашборда.

Гарантирует, что клиентский JS-движок скоринга и статический демо-набор
данных полностью соответствуют серверному Python-ядру
(`vulnerability_index/`), протестированному в `tests/`. Запускать при
любом изменении `methodology_v1.yaml`, `data/reference/settlements.csv`
или `data/demo/*.csv`:

    python3 scripts/export_static_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "netlify-site" / "data"

import sys

sys.path.insert(0, str(ROOT))

from vulnerability_index.methodology import MethodologyRepository  # noqa: E402
from vulnerability_index.settlements import SettlementRepository  # noqa: E402
from vulnerability_index.source_factory import build_default_source_chains  # noqa: E402


def export_methodology() -> None:
    repo = MethodologyRepository()
    methodology = repo.latest()

    components = {}
    for comp_key, comp in methodology.components.items():
        indicators = {}
        for ind_key, ind in comp.indicators.items():
            indicators[ind_key] = {
                "title": ind.title,
                "unit": ind.unit,
                "weight": ind.weight,
                "type": ind.type,
                "notes": ind.notes,
                "rules": ind.rules,
                "options": ind.options,
            }
        components[comp_key] = {
            "title": comp.title,
            "weight": comp.weight,
            "notes": comp.notes,
            "indicators": indicators,
        }

    payload = {
        "version": methodology.version,
        "effectiveDate": str(methodology.effective_date),
        "title": methodology.title,
        "approvedBy": methodology.approved_by,
        "valueRange": list(methodology.value_range),
        "components": components,
        "categories": {
            "approved": methodology.categories_approved(),
            "approach": methodology.category_approach(),
            "thresholds": methodology.category_thresholds(),
        },
    }
    (OUT_DIR / "methodology.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {OUT_DIR / 'methodology.json'}")


def export_settlements() -> None:
    repo = SettlementRepository()
    rows = [
        {
            "code": s.code,
            "name": s.name,
            "district": s.district,
            "region": s.region,
            "lat": s.lat,
            "lon": s.lon,
            "categories": list(s.categories),
        }
        for s in repo.all()
    ]
    (OUT_DIR / "settlements.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {OUT_DIR / 'settlements.json'} ({len(rows)} settlements)")


def export_demo_sources() -> None:
    """Строит demoSources[code][component.indicator] = {value, sourceName,
    sourceKind}, используя ту же цепочку источников, что и
    `source_factory.build_default_source_chains`, чтобы автозаполнение в
    статической версии показывало те же значения и названия источников,
    что и в Python/веб-версии (по демо-данным)."""
    settlement_repo = SettlementRepository()
    chains = build_default_source_chains()
    methodology = MethodologyRepository().latest()

    result: dict[str, dict[str, dict]] = {}
    for settlement in settlement_repo.all():
        per_settlement: dict[str, dict] = {}
        for comp_key, comp in methodology.components.items():
            for ind_key, ind_spec in comp.indicators.items():
                chain = chains.get((comp_key, ind_key))
                if chain is None:
                    continue
                outcome = chain.fetch(settlement, comp_key, ind_key, ind_spec)
                if not outcome.succeeded:
                    continue
                value = outcome.value
                raw = value.raw_value
                # numpy-скаляры (из pandas) не сериализуются в JSON напрямую
                if hasattr(raw, "item"):
                    raw = raw.item()
                per_settlement[f"{comp_key}.{ind_key}"] = {
                    "value": raw,
                    "sourceName": value.source_name,
                    "sourceKind": value.source_kind,
                }
        result[settlement.code] = per_settlement

    (OUT_DIR / "demo_sources.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {OUT_DIR / 'demo_sources.json'}")


def export_sources_overview() -> None:
    """Список настроенных цепочек источников по каждому показателю (для
    страницы «Источники данных»)."""
    chains = build_default_source_chains()
    methodology = MethodologyRepository().latest()
    rows = []
    for comp_key, comp in methodology.components.items():
        for ind_key, ind_spec in comp.indicators.items():
            chain = chains.get((comp_key, ind_key))
            rows.append(
                {
                    "component": comp_key,
                    "indicator": ind_key,
                    "title": ind_spec.title,
                    "chain": [
                        {"name": s.name, "kind": s.kind} for s in (chain.sources if chain else [])
                    ],
                }
            )
    (OUT_DIR / "sources_overview.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {OUT_DIR / 'sources_overview.json'}")


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    export_methodology()
    export_settlements()
    export_demo_sources()
    export_sources_overview()

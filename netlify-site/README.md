# Статическая демо-версия (Netlify)

Полностью статический (HTML/CSS/JS, без сборки и без сервера) клон
диалогового окна и дашборда из `webapp/` (Streamlit), пригодный для
хостинга на Netlify. Использует тот же расчётный движок методики (порт
`vulnerability_index/methodology.py` → `js/methodology.js`) и те же
демонстрационные данные, экспортированные в JSON скриптом
[`scripts/export_static_data.py`](../scripts/export_static_data.py) из
Python-ядра — поэтому расчёты в этой версии численно совпадают с
Python/CLI/Streamlit-версией (проверено вручную и совпадает с
результатами тестов `tests/test_methodology.py`, `tests/test_batch.py`).

## Отличия от полной версии

Так как Netlify — статический хостинг без постоянно работающего
сервера (Streamlit требует постоянного процесса с WebSocket-соединениями,
что Netlify не поддерживает), эта версия:

- хранит состояние диалога и историю расчётов в `localStorage`
  браузера (а не в файлах на сервере) — данные не расшариваются между
  устройствами/пользователями;
- источник «Авто» в диалоговом окне использует не реальные сетевые
  запросы к ведомственным ИС/НСК, а предварительно посчитанные тем же
  Python-коннектором значения из `data/demo_sources.json` (реальные
  запросы к серверам ведомств/НСК с фронтенда браузера были бы
  невозможны из-за отсутствия публичных API и CORS-ограничений);
- страница «Источники данных» показывает конфигурацию цепочек и
  зафиксированные демо-значения, а не результат живой проверки
  доступности.

## Структура

```
netlify-site/
  index.html        — HTML-шелл (сайдбар + область контента)
  css/styles.css     — стили
  js/
    app.js            — роутер (хеш-навигация) + инициализация
    methodology.js     — расчётный движок (порт methodology.py)
    store.js            — состояние в localStorage
    data.js              — загрузка JSON-данных
    render.js             — общие функции отображения (графики/таблицы)
    modal.js               — модальное диалоговое окно
    views/                 — 7 страниц (overview, dialog, dashboard,
                              registry, sources, methodologyView, verification)
  data/
    methodology.json   — экспорт методики
    settlements.json    — экспорт реестра населённых пунктов
    demo_sources.json    — предрасчитанные демо-значения по источникам
    sources_overview.json — конфигурация цепочек источников
```

## Обновление данных

При изменении `vulnerability_index/config/methodology_v1.yaml`,
`data/reference/settlements.csv` или `data/demo/*.csv` пересоздайте
JSON-экспорт и закоммитьте изменения:

```bash
python3 scripts/export_static_data.py
```

## Локальный запуск

```bash
cd netlify-site && python3 -m http.server 8000
```

## Деплой на Netlify

См. `netlify.toml` в корне репозитория (`base = "netlify-site"`,
без build-команды — сайт уже полностью статический).

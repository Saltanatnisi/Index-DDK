/**
 * Страница «Источники данных» — аналог `webapp/views/sources.py`.
 * В статической версии реального сетевого обращения к внешним ИС нет
 * (браузер + отсутствие сервера) — используется предварительно
 * зафиксированный результат работы тех же коннекторов
 * (`data/demo_sources.json`, сформированный Python-ядром).
 */

window.Views = window.Views || {};

window.Views.sources = function sourcesView(root) {
  const { esc } = window.RenderUtils;
  const methodology = AppData.methodology;

  function render() {
    const options = AppData.settlements;
    root.innerHTML = `
      <h1>🔌 Источники данных</h1>
      <p class="caption">Для каждого показателя настроена цепочка источников с приоритетом: ведомственные выгрузки,
      REST API существующих автоматизированных платформ, портал Национального статистического комитета КР, открытые
      интернет-геосервисы. При недоступности источника модуль автоматически переходит к следующему в цепочке
      (п. 5.9, 5.10 ТЗ). <b>В статической демо-версии</b> показаны значения, уже полученные этими коннекторами в
      Python-ядре по демонстрационным данным.</p>

      <h2>Настроенные цепочки источников</h2>
      <table class="data-table">
        <thead><tr><th>Компонент</th><th>Показатель</th><th>Цепочка источников (по приоритету)</th></tr></thead>
        <tbody>${AppData.sourcesOverview.map((row) => `<tr>
          <td>${esc(row.component)}</td><td>${esc(row.title)}</td>
          <td>${row.chain.length ? esc(row.chain.map((s) => `${s.name} [${s.kind}]`).join(' → ')) : 'не настроено'}</td>
        </tr>`).join('')}</tbody>
      </table>

      <hr/>
      <h2>Значения по демонстрационным данным</h2>
      <label>Населённый пункт</label>
      <select id="src-settlement">${options.map((s) => `<option value="${s.code}">${esc(s.name)} [${s.code}]</option>`).join('')}</select>
      <div id="src-values"></div>
    `;

    document.getElementById('src-settlement').addEventListener('change', (e) => renderValues(e.target.value));
    renderValues(options[0].code);
  }

  function renderValues(code) {
    const demo = AppData.demoSources[code] || {};
    const rows = [];
    for (const compKey of methodology.componentKeys()) {
      for (const indKey of methodology.indicatorKeys(compKey)) {
        const key = `${compKey}.${indKey}`;
        const entry = demo[key];
        rows.push({
          key, title: methodology.indicator(compKey, indKey).title,
          value: entry ? entry.value : null,
          source: entry ? entry.sourceName : null,
        });
      }
    }
    document.getElementById('src-values').innerHTML = `<table class="data-table">
      <thead><tr><th>Показатель</th><th>Статус</th><th>Значение</th><th>Источник</th></tr></thead>
      <tbody>${rows.map((r) => `<tr>
        <td>${esc(r.title)}</td>
        <td>${r.value !== null ? '✅ доступен' : '❌ недоступен'}</td>
        <td>${esc(r.value)}</td><td>${esc(r.source)}</td>
      </tr>`).join('')}</tbody>
    </table>`;
  }

  render();
};

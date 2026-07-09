/**
 * Страница «Обзор» — аналог `webapp/views/overview.py`.
 */

window.Views = window.Views || {};

window.Views.overview = function overviewView(root) {
  const { esc } = window.RenderUtils;
  const methodology = AppData.methodology;

  function render() {
    const settlements = AppData.settlements;
    const latestByCode = {};
    settlements.forEach((s) => { latestByCode[s.code] = Store.getLatest(s.code); });
    const computed = Object.values(latestByCode).filter(Boolean);
    const avg = computed.length ? (computed.reduce((s, r) => s + r.value, 0) / computed.length).toFixed(2) : '—';

    root.innerHTML = `
      <h1>🏔️ Индекс уязвимости высокогорных, отдалённых и приграничных населённых пунктов КР</h1>
      <p class="caption">Диалоговый модуль расчёта Индекса с автоматизированным сбором данных из государственных
      информационных систем, портала Нацстаткомитета КР и открытых источников — по «Методике расчёта Индекса
      уязвимости...». <b>Статическая демо-версия для Netlify</b>: расчёт выполняется в браузере по демонстрационным
      данным (см. страницу «Источники данных»).</p>

      <div class="metrics-row">
        ${window.RenderUtils.metricCard('Населённых пунктов в реестре', settlements.length)}
        ${window.RenderUtils.metricCard('Рассчитано (есть история)', `${computed.length} / ${settlements.length}`)}
        ${window.RenderUtils.metricCard('Средний ИУ (по последним расчётам)', avg)}
        ${window.RenderUtils.metricCard('Версия методики', `${methodology.version} (с ${methodology.effectiveDate})`)}
      </div>

      ${!methodology.categoriesApproved() ? `<div class="alert alert-warning">Пороговые значения категорий уязвимости пока не утверждены уполномоченным органом (раздел 4.9, приложение 5 ТЗ) — используются временные значения.</div>` : ''}

      <div class="two-col">
        <div>
          <h2>Статус по населённым пунктам</h2>
          <table class="data-table">
            <thead><tr><th>Код</th><th>Населённый пункт</th><th>Район</th><th>Область</th><th>ИУ</th><th>Категория</th><th>Статус верификации</th><th>Дата расчёта</th></tr></thead>
            <tbody>
              ${settlements.map((s) => {
                const r = latestByCode[s.code];
                return `<tr>
                  <td>${esc(s.code)}</td><td>${esc(s.name)}</td><td>${esc(s.district)}</td><td>${esc(s.region)}</td>
                  <td>${r ? r.value.toFixed(3) : ''}</td>
                  <td>${r ? esc(r.category) : 'не рассчитан'}</td>
                  <td>${r ? esc(r.verificationStatus) : '—'}</td>
                  <td>${r ? new Date(r.calculatedAt).toLocaleString('ru-RU') : '—'}</td>
                </tr>`;
              }).join('')}
            </tbody>
          </table>
        </div>
        <div>
          <h2>Распределение по категориям</h2>
          <canvas id="category-chart" height="180"></canvas>
          <h2>Быстрые действия</h2>
          <p class="caption">Полный автоматический пересчёт по всем населённым пунктам (демо-данные, без вопросов оператору).</p>
          <button id="recalc-btn" class="btn btn-primary">🔄 Запустить полный пересчёт</button>
        </div>
      </div>
    `;

    renderCategoryChart(computed);
    document.getElementById('recalc-btn').addEventListener('click', () => {
      recalcAll();
      render();
    });
  }

  function renderCategoryChart(computed) {
    const canvas = document.getElementById('category-chart');
    const counts = {};
    computed.forEach((r) => { counts[r.category] = (counts[r.category] || 0) + 1; });
    if (canvas._chartInstance) canvas._chartInstance.destroy();
    if (Object.keys(counts).length === 0) {
      canvas.parentElement.insertAdjacentHTML('beforeend', '<p class="caption">Пока нет ни одного расчёта.</p>');
      return;
    }
    canvas._chartInstance = new Chart(canvas, {
      type: 'bar',
      data: { labels: Object.keys(counts), datasets: [{ data: Object.values(counts), backgroundColor: '#2b6cb0' }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { ticks: { precision: 0 } } } },
    });
  }

  function recalcAll() {
    const settlements = AppData.settlements;
    for (const s of settlements) {
      const demo = AppData.demoSources[s.code] || {};
      const results = {};
      for (const compKey of methodology.componentKeys()) {
        for (const indKey of methodology.indicatorKeys(compKey)) {
          const draftKey = `${compKey}.${indKey}`;
          const entry = demo[draftKey];
          if (!entry) continue;
          try {
            const { score, label } = methodology.scoreIndicator(compKey, indKey, entry.value);
            results[draftKey] = {
              rawValue: entry.value, score, matchedRuleLabel: label,
              sourceName: entry.sourceName, sourceKind: entry.sourceKind,
              isAssumption: false, isMissing: false, comment: null,
            };
          } catch (e) { /* показатель без данных пропускается */ }
        }
      }
      const result = aggregateIndexResult(methodology, results);
      Store.saveResult(s.code, { settlementCode: s.code, ...result });
    }
  }

  render();
};

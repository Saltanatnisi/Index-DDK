/**
 * Страница «Методика» — аналог `webapp/views/methodology_view.py`.
 */

window.Views = window.Views || {};

window.Views.methodology = function methodologyView(root) {
  const { esc } = window.RenderUtils;
  const methodology = AppData.methodology;

  function render() {
    root.innerHTML = `
      <h1>📐 Методика расчёта Индекса</h1>
      <h3>${esc(methodology.title)}</h3>
      <p><b>Версия:</b> ${esc(methodology.version)} · <b>Действует с:</b> ${esc(methodology.effectiveDate)} ·
        <b>Диапазон значений ИУ:</b> ${methodology.valueRange[0]}–${methodology.valueRange[1]}</p>
      ${methodology.approvedBy ? `<p><b>Утверждена:</b> ${esc(methodology.approvedBy)}</p>`
        : '<div class="alert alert-warning">Реквизиты утверждения методики не заполнены в конфигурации.</div>'}
      <p><b>ИУ = 0,20·GEO + 0,30·ACC + 0,10·DEM + 0,10·SERV + 0,10·INFRA + 0,10·ECO + 0,10·ECON</b></p>
      <canvas id="weights-chart" height="140"></canvas>
      <div id="components-block"></div>
      <hr/>
      <h2>Категоризация населённых пунктов по уровню уязвимости</h2>
      <p>Пороги утверждены: ${methodology.categoriesApproved() ? 'да' : '⚠️ нет — временная заглушка'}</p>
      <table class="data-table">
        <thead><tr><th>Условие по ИУ</th><th>Категория</th></tr></thead>
        <tbody>${(methodology.categories.thresholds || []).map((rule) => `<tr>
          <td>${describeRule(rule)}</td><td>${esc(rule.category)}</td>
        </tr>`).join('')}</tbody>
      </table>
    `;

    renderWeightsChart();
    renderComponents();
  }

  function describeRule(rule) {
    const parts = [];
    if ('gt' in rule) parts.push(`&gt; ${rule.gt}`);
    if ('gte' in rule) parts.push(`&gt;= ${rule.gte}`);
    if ('lt' in rule) parts.push(`&lt; ${rule.lt}`);
    if ('lte' in rule) parts.push(`&lt;= ${rule.lte}`);
    return parts.join(' и ');
  }

  function renderWeightsChart() {
    const canvas = document.getElementById('weights-chart');
    const keys = methodology.componentKeys();
    new Chart(canvas, {
      type: 'bar',
      data: { labels: keys, datasets: [{ data: keys.map((k) => methodology.components[k].weight), backgroundColor: '#2b6cb0' }] },
      options: { plugins: { legend: { display: false } } },
    });
  }

  function renderComponents() {
    const container = document.getElementById('components-block');
    container.innerHTML = methodology.componentKeys().map((compKey) => {
      const comp = methodology.components[compKey];
      const indRows = Object.entries(comp.indicators).map(([indKey, ind]) => {
        let scaleRows;
        if (ind.type === 'numeric_thresholds') {
          scaleRows = (ind.rules || []).map((r) => `<tr><td>${esc(r.label)}</td><td>${r.score}</td></tr>`).join('');
        } else {
          scaleRows = Object.values(ind.options || {}).map((o) => `<tr><td>${esc(o.label)}</td><td>${o.score}</td></tr>`).join('');
        }
        return `<p><b>${esc(ind.title)}</b> (вес ${ind.weight} внутри ${compKey})${ind.unit ? ` — единица: ${esc(ind.unit)}` : ''}</p>
          ${ind.notes ? `<p class="caption">${esc(ind.notes)}</p>` : ''}
          <table class="data-table"><thead><tr><th>Интервал</th><th>Балл</th></tr></thead><tbody>${scaleRows}</tbody></table>`;
      }).join('');
      return `<details class="component-block">
        <summary>${compKey} — ${esc(comp.title)} (вес ${comp.weight})</summary>
        ${comp.notes ? `<p class="caption">${esc(comp.notes)}</p>` : ''}
        ${indRows}
      </details>`;
    }).join('');
  }

  render();
};

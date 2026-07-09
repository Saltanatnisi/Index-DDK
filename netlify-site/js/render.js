/**
 * Общие функции отображения результата расчёта — аналог `webapp/render.py`
 * из полной (Streamlit) версии, но на клиентском JS + Chart.js.
 */

function esc(value) {
  if (value === null || value === undefined) return '';
  return String(value).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function fmtScore(v) {
  return v === null || v === undefined ? '—' : String(v);
}

function renderSummary(container, result, methodology) {
  const parts = [];
  parts.push('<div class="metrics-row">');
  parts.push(metricCard('Индекс уязвимости (ИУ)', result.value.toFixed(3),
    `Диапазон ${methodology.valueRange[0]}–${methodology.valueRange[1]}`));
  parts.push(metricCard('Категория уязвимости', result.category || 'не определена'));
  parts.push(metricCard('Статус верификации', result.verificationStatus || 'не верифицировано'));
  parts.push('</div>');

  if (result.hasAssumptions) {
    parts.push('<div class="alert alert-warning">⚠️ В расчёте использованы допущенные (не первичные) значения по отдельным показателям — см. детализацию ниже.</div>');
  }
  if (result.hasMissing) {
    parts.push('<div class="alert alert-error">⚠️ По части показателей нет данных — их вес перенормирован среди остальных показателей компонента. Рекомендуется дособрать данные.</div>');
  }
  if (!methodology.categoriesApproved()) {
    parts.push('<p class="caption">Пороговые значения категорий уязвимости пока не утверждены уполномоченным органом — показанная категория рассчитана по временным значениям (см. раздел «Методика»).</p>');
  }
  container.innerHTML = parts.join('\n');
}

function metricCard(label, value, help) {
  return `<div class="metric">
    <div class="metric-label">${esc(label)}</div>
    <div class="metric-value">${esc(value)}</div>
    ${help ? `<div class="metric-help">${esc(help)}</div>` : ''}
  </div>`;
}

function renderComponentChart(canvas, result, valueRange) {
  const labels = result.components.map((c) => c.key);
  const values = result.components.map((c) => (c.value !== null ? Number(c.value.toFixed(3)) : 0));
  const colors = result.components.map((c) => (c.value !== null ? '#2b6cb0' : '#a0aec0'));
  const titles = result.components.map((c) => c.title);

  if (canvas._chartInstance) canvas._chartInstance.destroy();
  canvas._chartInstance = new Chart(canvas, {
    type: 'bar',
    data: { labels, datasets: [{ label: 'Балл компонента', data: values, backgroundColor: colors }] },
    options: {
      scales: { y: { min: valueRange[0], max: valueRange[1], title: { display: true, text: 'Балл компонента' } } },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { title: (items) => titles[items[0].dataIndex] } },
      },
    },
  });
}

function renderBreakdown(container, result) {
  container.innerHTML = result.components.map((c) => {
    const valueStr = c.value !== null ? c.value.toFixed(3) : 'нет данных';
    const rows = c.indicators.length
      ? c.indicators.map((i) => `
        <tr>
          <td>${esc(i.title)}</td>
          <td>${esc(i.rawValue)}</td>
          <td>${fmtScore(i.score)}</td>
          <td>${esc(i.sourceName)}</td>
          <td>${i.isMissing ? 'нет данных' : (i.isAssumption ? 'допущение' : '')}</td>
          <td>${esc(i.comment)}</td>
        </tr>`).join('')
      : '<tr><td colspan="6">Нет собранных показателей.</td></tr>';
    return `<details class="component-details">
      <summary>${esc(c.key)} — ${esc(c.title)} (вес ${c.weight}): ${valueStr}</summary>
      <table class="data-table">
        <thead><tr><th>Показатель</th><th>Значение</th><th>Балл</th><th>Источник</th><th>Особенность</th><th>Комментарий</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </details>`;
  }).join('\n');
}

function downloadCSV(filename, rows) {
  if (!rows.length) return;
  const headers = Object.keys(rows[0]);
  const escCsv = (v) => {
    const s = v === null || v === undefined ? '' : String(v);
    return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = [headers.join(';'), ...rows.map((r) => headers.map((h) => escCsv(r[h])).join(';'))].join('\n');
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

window.RenderUtils = { esc, fmtScore, renderSummary, renderComponentChart, renderBreakdown, downloadCSV, metricCard };

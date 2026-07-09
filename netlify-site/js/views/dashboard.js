/**
 * Страница «Дашборд» — аналог `webapp/views/dashboard.py`.
 */

window.Views = window.Views || {};

window.Views.dashboard = function dashboardView(root, ctx) {
  const { esc, renderSummary, renderComponentChart, renderBreakdown, downloadCSV } = window.RenderUtils;
  const methodology = AppData.methodology;
  let filters = { region: '', district: '', category: '' };
  let selectedCode = ctx.dashboardSettlement || AppData.settlements[0].code;
  let aggLevel = 'district';
  let map = null;

  function overviewRows() {
    return AppData.settlements.map((s) => {
      const r = Store.getLatest(s.code);
      return {
        code: s.code, name: s.name, district: s.district, region: s.region,
        territoryCategory: s.categories.join(', ') || '—',
        value: r ? r.value : null,
        category: r ? r.category : null,
        verification: r ? r.verificationStatus : '—',
        hasAssumptions: r ? r.hasAssumptions : false,
        calculatedAt: r ? r.calculatedAt : null,
      };
    });
  }

  function filteredRows() {
    return overviewRows().filter((row) => {
      if (filters.region && row.region !== filters.region) return false;
      if (filters.district && row.district !== filters.district) return false;
      if (filters.category && row.category !== filters.category) return false;
      return true;
    });
  }

  function render() {
    ctx.dashboardSettlement = selectedCode;
    const all = overviewRows();
    const regions = [...new Set(all.map((r) => r.region))].sort();
    const districts = [...new Set(all.filter((r) => !filters.region || r.region === filters.region).map((r) => r.district))].sort();
    const categories = [...new Set(all.map((r) => r.category).filter(Boolean))].sort();
    const rows = filteredRows();

    root.innerHTML = `
      <h1>📊 Дашборд Индекса уязвимости</h1>
      <h2>Фильтры</h2>
      <div class="filters-row">
        <div><label>Область</label><select id="f-region"><option value="">Все</option>${regions.map((r) => `<option ${filters.region === r ? 'selected' : ''}>${esc(r)}</option>`).join('')}</select></div>
        <div><label>Район</label><select id="f-district"><option value="">Все</option>${districts.map((d) => `<option ${filters.district === d ? 'selected' : ''}>${esc(d)}</option>`).join('')}</select></div>
        <div><label>Категория уязвимости</label><select id="f-category"><option value="">Все</option>${categories.map((c) => `<option ${filters.category === c ? 'selected' : ''}>${esc(c)}</option>`).join('')}</select></div>
      </div>

      <h2>Населённые пункты (${rows.length} из ${all.length})</h2>
      <table class="data-table">
        <thead><tr><th>Код</th><th>Населённый пункт</th><th>Район</th><th>Область</th><th>Категория территории</th><th>ИУ</th><th>Категория</th><th>Статус верификации</th></tr></thead>
        <tbody>${rows.map((r) => `<tr>
          <td>${esc(r.code)}</td><td>${esc(r.name)}</td><td>${esc(r.district)}</td><td>${esc(r.region)}</td>
          <td>${esc(r.territoryCategory)}</td><td>${r.value !== null ? r.value.toFixed(3) : ''}</td>
          <td>${esc(r.category)}</td><td>${esc(r.verification)}</td>
        </tr>`).join('')}</tbody>
      </table>
      <button id="export-csv-btn" class="btn">⬇️ Экспорт таблицы (CSV)</button>
      <hr/>

      <h2>Агрегация по территориям (п. 6.2 ТЗ)</h2>
      <div class="radio-group inline">
        <label><input type="radio" name="agg-level" value="district" ${aggLevel === 'district' ? 'checked' : ''}> Район</label>
        <label><input type="radio" name="agg-level" value="region" ${aggLevel === 'region' ? 'checked' : ''}> Область</label>
      </div>
      <div class="two-col">
        <div id="agg-table"></div>
        <canvas id="agg-chart" height="220"></canvas>
      </div>
      <p class="caption">Доля населённых пунктов по категории уязвимости, %</p>
      <canvas id="agg-share-chart" height="220"></canvas>
      <hr/>

      <h2>Карта населённых пунктов</h2>
      <div id="map" style="height:360px;border-radius:8px;"></div>
      <hr/>

      <h2>Детализация и динамика по населённому пункту</h2>
      <label>Населённый пункт</label>
      <select id="detail-select">${AppData.settlements.map((s) => `<option value="${s.code}" ${s.code === selectedCode ? 'selected' : ''}>${esc(s.name)} (${esc(s.district)}, ${esc(s.region)}) [${s.code}]</option>`).join('')}</select>
      <div id="detail-section"></div>
    `;

    document.getElementById('f-region').addEventListener('change', (e) => { filters.region = e.target.value; filters.district = ''; render(); });
    document.getElementById('f-district').addEventListener('change', (e) => { filters.district = e.target.value; render(); });
    document.getElementById('f-category').addEventListener('change', (e) => { filters.category = e.target.value; render(); });
    document.getElementById('export-csv-btn').addEventListener('click', () => {
      downloadCSV('index_uyazvimosti_svod.csv', rows.map((r) => ({
        'Код': r.code, 'Населённый пункт': r.name, 'Район': r.district, 'Область': r.region,
        'ИУ': r.value, 'Категория': r.category, 'Статус верификации': r.verification,
      })));
    });
    document.querySelectorAll('input[name="agg-level"]').forEach((el) => el.addEventListener('change', (e) => {
      aggLevel = e.target.value;
      renderAggregation(rows);
    }));
    document.getElementById('detail-select').addEventListener('change', (e) => {
      selectedCode = e.target.value;
      renderDetail();
    });

    renderAggregation(rows);
    renderMap(all);
    renderDetail();
  }

  function renderAggregation(rows) {
    const computed = rows.filter((r) => r.value !== null);
    const tableEl = document.getElementById('agg-table');
    const chartCanvas = document.getElementById('agg-chart');
    const shareCanvas = document.getElementById('agg-share-chart');
    if (computed.length === 0) {
      tableEl.innerHTML = '<p class="alert alert-info">Нет рассчитанных значений Индекса для отображения агрегации по выбранным фильтрам.</p>';
      if (chartCanvas._chartInstance) chartCanvas._chartInstance.destroy();
      if (shareCanvas._chartInstance) shareCanvas._chartInstance.destroy();
      return;
    }
    const key = aggLevel === 'district' ? 'district' : 'region';
    const groups = {};
    computed.forEach((r) => {
      const k = r[key];
      groups[k] = groups[k] || [];
      groups[k].push(r);
    });
    const aggRows = Object.entries(groups).map(([name, items]) => {
      const values = items.map((i) => i.value).sort((a, b) => a - b);
      const mean = values.reduce((s, v) => s + v, 0) / values.length;
      const median = values.length % 2 ? values[(values.length - 1) / 2]
        : (values[values.length / 2 - 1] + values[values.length / 2]) / 2;
      return { name, mean, median, count: items.length };
    }).sort((a, b) => b.mean - a.mean);

    tableEl.innerHTML = `<table class="data-table">
      <thead><tr><th>${aggLevel === 'district' ? 'Район' : 'Область'}</th><th>Среднее</th><th>Медиана</th><th>Кол-во н.п.</th></tr></thead>
      <tbody>${aggRows.map((r) => `<tr><td>${esc(r.name)}</td><td>${r.mean.toFixed(3)}</td><td>${r.median.toFixed(3)}</td><td>${r.count}</td></tr>`).join('')}</tbody>
    </table>`;

    if (chartCanvas._chartInstance) chartCanvas._chartInstance.destroy();
    chartCanvas._chartInstance = new Chart(chartCanvas, {
      type: 'bar',
      data: { labels: aggRows.map((r) => r.name), datasets: [{ data: aggRows.map((r) => r.mean), backgroundColor: '#2b6cb0' }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { min: 0, max: methodology.valueRange[1] } } },
    });

    const categories = [...new Set(computed.map((r) => r.category))];
    const palette = ['#e53e3e', '#ed8936', '#ecc94b', '#48bb78', '#4299e1', '#805ad5'];
    const shareDatasets = categories.map((cat, idx) => ({
      label: cat,
      backgroundColor: palette[idx % palette.length],
      data: aggRows.map((r) => {
        const items = groups[r.name];
        const inCat = items.filter((i) => i.category === cat).length;
        return (inCat / items.length) * 100;
      }),
    }));
    if (shareCanvas._chartInstance) shareCanvas._chartInstance.destroy();
    shareCanvas._chartInstance = new Chart(shareCanvas, {
      type: 'bar',
      data: { labels: aggRows.map((r) => r.name), datasets: shareDatasets },
      options: { scales: { x: { stacked: true }, y: { stacked: true, min: 0, max: 100 } } },
    });
  }

  function renderMap(all) {
    const withCoords = all.filter((r) => AppData.settlementByCode(r.code).lat);
    if (withCoords.length === 0) return;
    if (map) { map.remove(); map = null; }
    map = L.map('map');
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);
    const markers = withCoords.map((r) => {
      const s = AppData.settlementByCode(r.code);
      const marker = L.marker([s.lat, s.lon]).addTo(map);
      marker.bindPopup(`<b>${esc(s.name)}</b><br/>${esc(s.district)}, ${esc(s.region)}${r.value !== null ? `<br/>ИУ: ${r.value.toFixed(3)} (${esc(r.category)})` : ''}`);
      return marker;
    });
    map.fitBounds(L.featureGroup(markers).getBounds(), { padding: [30, 30] });
  }

  function renderDetail() {
    const container = document.getElementById('detail-section');
    const result = Store.getLatest(selectedCode);
    if (!result) {
      container.innerHTML = '<p class="alert alert-warning">Для этого населённого пункта пока нет сохранённого расчёта — выполните расчёт на странице «Диалоговый расчёт» или запустите полный пересчёт на странице «Обзор».</p>';
      return;
    }
    container.innerHTML = `
      <div id="detail-summary"></div>
      <canvas id="detail-chart" height="100"></canvas>
      <div id="detail-breakdown"></div>
      <p class="caption"><b>Динамика Индекса по периодам расчёта</b></p>
      <canvas id="history-chart" height="120"></canvas>
      <button id="export-detail-btn" class="btn">⬇️ Экспорт детализации (CSV)</button>
    `;
    renderSummary(document.getElementById('detail-summary'), result, methodology);
    renderComponentChart(document.getElementById('detail-chart'), result, methodology.valueRange);
    renderBreakdown(document.getElementById('detail-breakdown'), result);

    const history = Store.getHistory(selectedCode);
    const histCanvas = document.getElementById('history-chart');
    if (histCanvas._chartInstance) histCanvas._chartInstance.destroy();
    if (history.length > 1) {
      histCanvas._chartInstance = new Chart(histCanvas, {
        type: 'line',
        data: {
          labels: history.map((h) => new Date(h.calculatedAt).toLocaleString('ru-RU')),
          datasets: [{ label: 'ИУ', data: history.map((h) => h.value), borderColor: '#2b6cb0', tension: 0.2 }],
        },
        options: { scales: { y: { min: methodology.valueRange[0], max: methodology.valueRange[1] } } },
      });
    } else {
      histCanvas.parentElement.insertAdjacentHTML('beforeend', '<p class="caption">Пока сохранён только один расчёт — динамика появится после повторного пересчёта.</p>');
    }

    document.getElementById('export-detail-btn').addEventListener('click', () => {
      const exportRows = [];
      result.components.forEach((c) => c.indicators.forEach((i) => exportRows.push({
        'Населённый пункт': AppData.settlementByCode(selectedCode).name,
        'Код': selectedCode, 'Компонент': c.key, 'Показатель': i.title,
        'Значение': i.rawValue, 'Балл': i.score, 'Источник': i.sourceName,
        'Значение компонента': c.value, 'ИУ': result.value, 'Категория': result.category,
      })));
      downloadCSV(`iu_${selectedCode}_detail.csv`, exportRows);
    });
  }

  render();
};

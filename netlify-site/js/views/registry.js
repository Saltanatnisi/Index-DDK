/**
 * Страница «Реестр населённых пунктов» — аналог `webapp/views/registry.py`.
 */

window.Views = window.Views || {};

window.Views.registry = function registryView(root) {
  const { esc, downloadCSV } = window.RenderUtils;
  let query = '';
  let map = null;

  function render() {
    const rows = AppData.settlements
      .filter((s) => {
        if (!query) return true;
        const q = query.toLowerCase();
        return [s.name, s.district, s.region, s.code].some((v) => v.toLowerCase().includes(q));
      })
      .map((s) => {
        const history = Store.getHistory(s.code);
        const latest = Store.getLatest(s.code);
        return { s, history, latest };
      });

    root.innerHTML = `
      <h1>🗂️ Реестр населённых пунктов</h1>
      <p class="caption">Единый эталонный справочник, к которому привязываются все исходные показатели и результаты
      расчёта Индекса (п. 5.11 ТЗ). Демонстрационный набор из 5 населённых пунктов.</p>
      <label>Поиск по названию / району / области / коду</label>
      <input type="text" id="search-input" value="${esc(query)}" />
      <table class="data-table">
        <thead><tr><th>Код</th><th>Название</th><th>Район</th><th>Область</th><th>Широта</th><th>Долгота</th>
          <th>Категория территории</th><th>Последний ИУ</th><th>Расчётов в истории</th></tr></thead>
        <tbody>${rows.map(({ s, history, latest }) => `<tr>
          <td>${esc(s.code)}</td><td>${esc(s.name)}</td><td>${esc(s.district)}</td><td>${esc(s.region)}</td>
          <td>${s.lat ?? ''}</td><td>${s.lon ?? ''}</td><td>${esc(s.categories.join(', ') || '—')}</td>
          <td>${latest ? latest.value.toFixed(3) : ''}</td><td>${history.length}</td>
        </tr>`).join('')}</tbody>
      </table>
      <button id="export-btn" class="btn">⬇️ Скачать реестр (CSV)</button>
      <hr/>
      <h2>Карта</h2>
      <div id="registry-map" style="height:360px;border-radius:8px;"></div>
    `;

    document.getElementById('search-input').addEventListener('input', (e) => { query = e.target.value; render(); });
    document.getElementById('export-btn').addEventListener('click', () => {
      downloadCSV('settlements_registry.csv', rows.map(({ s, latest, history }) => ({
        'Код': s.code, 'Название': s.name, 'Район': s.district, 'Область': s.region,
        'Широта': s.lat, 'Долгота': s.lon, 'Категория территории': s.categories.join(', '),
        'Последний ИУ': latest ? latest.value : '', 'Количество расчётов в истории': history.length,
      })));
    });

    renderMap(rows.map((r) => r.s));
  }

  function renderMap(settlements) {
    const withCoords = settlements.filter((s) => s.lat);
    if (withCoords.length === 0) return;
    if (map) { map.remove(); map = null; }
    map = L.map('registry-map');
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);
    const markers = withCoords.map((s) => L.marker([s.lat, s.lon]).addTo(map).bindPopup(esc(s.name)));
    map.fitBounds(L.featureGroup(markers).getBounds(), { padding: [30, 30] });
  }

  render();
};

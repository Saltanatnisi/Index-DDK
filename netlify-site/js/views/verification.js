/**
 * Страница «Верификация» — аналог `webapp/views/verification.py`.
 */

window.Views = window.Views || {};

window.Views.verification = function verificationView(root) {
  const { esc } = window.RenderUtils;
  const STATUSES = ['не верифицировано', 'на верификации', 'верифицировано'];
  let selectedCode = AppData.settlements[0].code;

  function render() {
    const rows = AppData.settlements.map((s) => ({ s, r: Store.getLatest(s.code) }));

    root.innerHTML = `
      <h1>✅ Верификация результатов расчёта</h1>
      <p class="caption">Каждый расчёт хранится со статусом верификации: «не верифицировано» / «на верификации» /
      «верифицировано», с возможностью зафиксировать замечания верифицирующей стороны (п. 5.12 ТЗ).</p>

      <table class="data-table">
        <thead><tr><th>Код</th><th>Населённый пункт</th><th>ИУ</th><th>Статус верификации</th><th>Комментарий</th><th>Дата расчёта</th></tr></thead>
        <tbody>${rows.map(({ s, r }) => `<tr>
          <td>${esc(s.code)}</td><td>${esc(s.name)}</td>
          <td>${r ? r.value.toFixed(3) : ''}</td>
          <td>${r ? esc(r.verificationStatus) : '—'}</td>
          <td>${r ? esc(r.verificationComment) : ''}</td>
          <td>${r ? new Date(r.calculatedAt).toLocaleString('ru-RU') : ''}</td>
        </tr>`).join('')}</tbody>
      </table>
      <hr/>
      <h2>Изменить статус верификации</h2>
      <label>Населённый пункт</label>
      <select id="verify-settlement">${AppData.settlements.map((s) => `<option value="${s.code}" ${s.code === selectedCode ? 'selected' : ''}>${esc(s.name)} [${s.code}]</option>`).join('')}</select>
      <div id="verify-form"></div>
    `;

    document.getElementById('verify-settlement').addEventListener('change', (e) => {
      selectedCode = e.target.value;
      renderForm();
    });
    renderForm();
  }

  function renderForm() {
    const container = document.getElementById('verify-form');
    const result = Store.getLatest(selectedCode);
    if (!result) {
      container.innerHTML = '<p class="alert alert-info">Для этого населённого пункта пока нет расчёта.</p>';
      return;
    }
    container.innerHTML = `
      <p>Текущий статус: <b>${esc(result.verificationStatus)}</b></p>
      <label>Новый статус</label>
      <select id="new-status">${STATUSES.map((s) => `<option ${s === result.verificationStatus ? 'selected' : ''}>${esc(s)}</option>`).join('')}</select>
      <label>Замечания верифицирующей стороны</label>
      <textarea id="verify-comment">${esc(result.verificationComment || '')}</textarea>
      <button id="save-status-btn" class="btn btn-primary">💾 Сохранить статус</button>
    `;
    document.getElementById('save-status-btn').addEventListener('click', () => {
      const status = document.getElementById('new-status').value;
      const comment = document.getElementById('verify-comment').value;
      Store.updateVerification(selectedCode, result.id, status, comment);
      render();
    });
  }

  render();
};

/**
 * Страница «Диалоговый расчёт» — статический аналог `webapp/views/dialog_wizard.py`.
 * Для каждого показателя открывается модальное диалоговое окно с выбором
 * способа получения данных: авто (по демо-цепочке источников), вручную,
 * или как документируемое допущение / «нет данных» (п. 4.10 ТЗ).
 */

window.Views = window.Views || {};

window.Views.dialog = function dialogView(root, ctx) {
  const { esc, fmtScore, renderSummary, renderComponentChart, renderBreakdown } = window.RenderUtils;
  const methodology = AppData.methodology;
  let currentCode = ctx.dialogSettlement || AppData.settlements[0].code;

  function totalIndicators() {
    return methodology.componentKeys()
      .reduce((sum, k) => sum + methodology.indicatorKeys(k).length, 0);
  }

  function render() {
    ctx.dialogSettlement = currentCode;
    const settlement = AppData.settlementByCode(currentCode);
    const results = Store.getIndicatorResults(currentCode);
    const total = totalIndicators();
    const done = Object.keys(results).length;

    root.innerHTML = `
      <h1>🧮 Диалоговый расчёт Индекса уязвимости</h1>
      <p class="caption">Заполните все показатели ниже — по каждому откроется диалоговое окно выбора способа
      получения данных. Показатели можно заполнять в любом порядке и изменять после заполнения.</p>

      <label for="settlement-select">Населённый пункт</label>
      <select id="settlement-select">
        ${AppData.settlements.map((s) => `<option value="${s.code}" ${s.code === currentCode ? 'selected' : ''}>${esc(s.name)} (${esc(s.district)}, ${esc(s.region)}) [${s.code}]</option>`).join('')}
      </select>

      <div class="button-row">
        <button id="reset-btn" class="btn">↺ Сбросить расчёт</button>
        <button id="autofill-btn" class="btn btn-primary">⚡ Автозаполнить всё</button>
      </div>

      <div class="progress-track"><div class="progress-fill" style="width:${total ? (done / total * 100) : 0}%"></div></div>
      <p class="caption">Заполнено показателей: ${done} / ${total}</p>
      <hr/>
      <div id="components-list"></div>
      <hr/>
      <div id="result-section"></div>
    `;

    document.getElementById('settlement-select').addEventListener('change', (e) => {
      currentCode = e.target.value;
      render();
    });
    document.getElementById('reset-btn').addEventListener('click', () => {
      Store.resetIndicatorResults(currentCode);
      render();
    });
    document.getElementById('autofill-btn').addEventListener('click', () => {
      autofillRemaining();
      render();
    });

    renderComponentsList(settlement, results);
    renderResultSection(settlement, results);
  }

  function autofillRemaining() {
    const demo = AppData.demoSources[currentCode] || {};
    const results = Store.getIndicatorResults(currentCode);
    for (const compKey of methodology.componentKeys()) {
      for (const indKey of methodology.indicatorKeys(compKey)) {
        const draftKey = `${compKey}.${indKey}`;
        if (results[draftKey]) continue; // не перезаписываем уже заполненные показатели
        const demoEntry = demo[draftKey];
        if (!demoEntry) continue;
        try {
          const { score, label } = methodology.scoreIndicator(compKey, indKey, demoEntry.value);
          Store.setIndicatorResult(currentCode, compKey, indKey, {
            rawValue: demoEntry.value,
            score,
            matchedRuleLabel: label,
            sourceName: demoEntry.sourceName,
            sourceKind: demoEntry.sourceKind,
            isAssumption: false,
            isMissing: false,
            comment: null,
          });
        } catch (e) {
          console.warn('autofill: не удалось оценить показатель', draftKey, e);
        }
      }
    }
  }

  function renderComponentsList(settlement, results) {
    const container = document.getElementById('components-list');
    container.innerHTML = methodology.componentKeys().map((compKey) => {
      const comp = methodology.components[compKey];
      const indKeys = Object.keys(comp.indicators);
      const filled = indKeys.filter((k) => results[`${compKey}.${k}`]).length;
      const rows = indKeys.map((indKey) => {
        const spec = comp.indicators[indKey];
        const entry = results[`${compKey}.${indKey}`];
        const badge = Store.statusBadge(entry);
        const valueScore = entry ? `${esc(entry.rawValue)} → балл ${fmtScore(entry.score)}` : '—';
        return `<div class="indicator-row">
          <div class="indicator-title">${esc(spec.title)}${spec.unit ? ` <em>${esc(spec.unit)}</em>` : ''}</div>
          <div class="indicator-status">${badge}</div>
          <div class="indicator-value">${valueScore}</div>
          <button class="btn btn-sm btn-open" data-comp="${compKey}" data-ind="${indKey}">Открыть</button>
        </div>`;
      }).join('');
      return `<details class="component-block" open>
        <summary>${compKey} — ${esc(comp.title)} (вес ${comp.weight}) [${filled}/${indKeys.length}]</summary>
        ${comp.notes ? `<p class="caption">${esc(comp.notes)}</p>` : ''}
        <div class="indicator-list">${rows}</div>
      </details>`;
    }).join('');

    container.querySelectorAll('.btn-open').forEach((btn) => {
      btn.addEventListener('click', () => {
        openIndicatorDialog(btn.dataset.comp, btn.dataset.ind, settlement);
      });
    });
  }

  function openIndicatorDialog(compKey, indKey, settlement) {
    const spec = methodology.indicator(compKey, indKey);
    const draftKey = `${compKey}.${indKey}`;
    const demoEntry = (AppData.demoSources[currentCode] || {})[draftKey];
    const overview = AppData.sourcesOverview.find((r) => r.component === compKey && r.indicator === indKey);
    const chainNames = overview ? overview.chain.map((s) => s.name) : [];

    const body = Modal.open('Заполнение показателя');
    let existing = Store.getIndicatorResults(currentCode)[draftKey];
    let pendingAuto = null; // {rawValue, sourceName, sourceKind} — предпросмотр перед принятием

    function draw() {
      body.innerHTML = `
        <h4>${esc(spec.title)}</h4>
        <p class="caption">Компонент ${compKey} — ${esc(methodology.components[compKey].title)}.
          Вес показателя внутри компонента: ${spec.weight}.${spec.unit ? ` Единица измерения: ${esc(spec.unit)}.` : ''}</p>
        ${spec.notes ? `<p class="caption">Примечание методики: ${esc(spec.notes)}</p>` : ''}
        ${existing ? `<div class="alert alert-info">Текущее значение: <b>${esc(existing.rawValue)}</b>
          (балл ${fmtScore(existing.score)}, источник: ${esc(existing.sourceName)})</div>` : ''}

        <label>Способ получения данных</label>
        <div class="radio-group" id="method-group">
          ${demoEntry ? `<label><input type="radio" name="method" value="auto" checked> Авто (по цепочке источников${chainNames.length ? `: ${esc(chainNames.join(' → '))}` : ''})</label>` : ''}
          <label><input type="radio" name="method" value="manual" ${!demoEntry ? 'checked' : ''}> Ввести вручную</label>
          <label><input type="radio" name="method" value="assumption"> Допущение / нет данных</label>
        </div>
        <div id="method-body"></div>
      `;
      body.querySelectorAll('input[name="method"]').forEach((r) => r.addEventListener('change', drawMethodBody));
      drawMethodBody();
    }

    function currentMethod() {
      const checked = body.querySelector('input[name="method"]:checked');
      return checked ? checked.value : 'manual';
    }

    function drawMethodBody() {
      const method = currentMethod();
      const methodBody = body.querySelector('#method-body');
      if (method === 'auto') {
        methodBody.innerHTML = `
          <button class="btn" id="fetch-btn">📡 Получить данные по цепочке источников</button>
          <div id="fetch-result"></div>
        `;
        methodBody.querySelector('#fetch-btn').addEventListener('click', () => {
          pendingAuto = { rawValue: demoEntry.value, sourceName: demoEntry.sourceName, sourceKind: demoEntry.sourceKind };
          drawFetchResult();
        });
      } else if (method === 'manual') {
        methodBody.innerHTML = renderValueInput('manual') + `
          <label>Документ-основание (необязательно)</label>
          <input type="text" id="manual-comment" />
          <button class="btn btn-primary" id="manual-save">💾 Сохранить значение</button>
        `;
        methodBody.querySelector('#manual-save').addEventListener('click', () => {
          const rawValue = readValueInput('manual');
          if (rawValue === null) return;
          saveEntry({
            rawValue,
            sourceName: 'Ручной ввод оператором',
            sourceKind: 'manual',
            isAssumption: false,
            isMissing: false,
            comment: methodBody.querySelector('#manual-comment').value || null,
          });
        });
      } else {
        methodBody.innerHTML = `
          <label><input type="checkbox" id="nodata-checkbox"> Показатель действительно недоступен — пометить «нет данных»</label>
          <div id="assumption-fields">
            <label>Основание допущения (п. 4.10 методики)</label>
            <select id="assumption-reason">
              ${Store.ASSUMPTION_REASONS.map((r) => `<option>${esc(r)}</option>`).join('')}
            </select>
            ${renderValueInput('assumption')}
            <label>Комментарий к допущению</label>
            <textarea id="assumption-comment"></textarea>
            <button class="btn btn-primary" id="assumption-save">💾 Сохранить допущение</button>
          </div>
          <div id="nodata-fields" style="display:none">
            <p class="alert alert-warning">Ответственное лицо будет уведомлено об отсутствии данных по этому показателю (п. 4.10, 5.10 ТЗ).</p>
            <button class="btn btn-primary" id="nodata-save">🚫 Отметить «нет данных»</button>
          </div>
        `;
        const checkbox = methodBody.querySelector('#nodata-checkbox');
        const assumptionFields = methodBody.querySelector('#assumption-fields');
        const nodataFields = methodBody.querySelector('#nodata-fields');
        checkbox.addEventListener('change', () => {
          assumptionFields.style.display = checkbox.checked ? 'none' : '';
          nodataFields.style.display = checkbox.checked ? '' : 'none';
        });
        methodBody.querySelector('#assumption-save').addEventListener('click', () => {
          const rawValue = readValueInput('assumption');
          if (rawValue === null) return;
          const reason = methodBody.querySelector('#assumption-reason').value;
          saveEntry({
            rawValue,
            sourceName: `Допущение оператора/методолога (${reason})`,
            sourceKind: 'assumption',
            isAssumption: true,
            assumptionReason: reason,
            isMissing: false,
            comment: methodBody.querySelector('#assumption-comment').value || null,
          });
        });
        methodBody.querySelector('#nodata-save').addEventListener('click', () => {
          saveMissing();
        });
      }
    }

    function renderValueInput(scope) {
      if (spec.type === 'options') {
        const choices = methodology.optionChoices(compKey, indKey);
        return `<label>Значение показателя</label>
          <select id="${scope}-value">
            ${choices.map((c) => `<option value="${esc(c.key)}">${esc(c.label)} (балл ${c.score})</option>`).join('')}
          </select>`;
      }
      return `<label>Значение показателя${spec.unit ? ` (${esc(spec.unit)})` : ''}</label>
        <input type="number" step="any" id="${scope}-value" value="0" />`;
    }

    function readValueInput(scope) {
      const el = body.querySelector(`#${scope}-value`);
      if (!el) return null;
      if (spec.type === 'options') return el.value;
      const num = parseFloat(el.value);
      return Number.isNaN(num) ? null : num;
    }

    function drawFetchResult() {
      const el = body.querySelector('#fetch-result');
      if (!pendingAuto) {
        el.innerHTML = '';
        return;
      }
      el.innerHTML = `
        <div class="alert alert-success">Получено значение: <b>${esc(pendingAuto.rawValue)}</b> (источник: ${esc(pendingAuto.sourceName)})</div>
        <button class="btn btn-primary" id="accept-btn">✅ Принять значение</button>
        <button class="btn" id="reject-btn">✖️ Отклонить, ввести иначе</button>
      `;
      el.querySelector('#accept-btn').addEventListener('click', () => {
        saveEntry({
          rawValue: pendingAuto.rawValue,
          sourceName: pendingAuto.sourceName,
          sourceKind: pendingAuto.sourceKind,
          isAssumption: false,
          isMissing: false,
          comment: null,
        });
      });
      el.querySelector('#reject-btn').addEventListener('click', () => {
        pendingAuto = null;
        drawFetchResult();
      });
    }

    function saveEntry(partial) {
      try {
        const { score, label } = methodology.scoreIndicator(compKey, indKey, partial.rawValue);
        Store.setIndicatorResult(currentCode, compKey, indKey, { ...partial, score, matchedRuleLabel: label });
        Modal.close();
        render();
      } catch (e) {
        alert(`Не удалось рассчитать балл: ${e.message}`);
      }
    }

    function saveMissing() {
      Store.setIndicatorResult(currentCode, compKey, indKey, {
        rawValue: null, score: null, sourceName: '—', sourceKind: 'missing',
        isAssumption: false, isMissing: true, comment: 'Нет данных',
      });
      Modal.close();
      render();
    }

    draw();
  }

  function renderResultSection(settlement, results) {
    const container = document.getElementById('result-section');
    const done = Object.keys(results).length;
    if (done === 0) {
      container.innerHTML = '<p class="alert alert-info">Заполните хотя бы один показатель, чтобы увидеть предварительный расчёт.</p>';
      return;
    }
    const result = aggregateIndexResult(methodology, results);
    container.innerHTML = `
      <h2>Предварительный результат</h2>
      <div id="summary-block"></div>
      <canvas id="component-chart" height="90"></canvas>
      <div id="breakdown-block"></div>
      <div class="button-row">
        <button id="save-btn" class="btn btn-primary">💾 Сохранить результат</button>
        <span class="caption">Результат сохраняется со статусом «не верифицировано» — статус можно изменить на странице «Верификация».</span>
      </div>
    `;
    renderSummary(document.getElementById('summary-block'), result, methodology);
    renderComponentChart(document.getElementById('component-chart'), result, methodology.valueRange);
    renderBreakdown(document.getElementById('breakdown-block'), result);

    document.getElementById('save-btn').addEventListener('click', () => {
      Store.saveResult(currentCode, { settlementCode: currentCode, ...result });
      alert(`Результат сохранён для ${settlement.name} (${new Date().toLocaleString('ru-RU')}).`);
      render();
    });
  }

  render();
};

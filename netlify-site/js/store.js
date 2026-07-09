/**
 * Хранилище состояния статической версии (localStorage вместо БД,
 * т.к. Netlify — статический хостинг без сервера). Аналог
 * `webapp/logic.py` (состояние диалога) и `vulnerability_index/storage.py`
 * (история расчётов, статус верификации) из полной Python-версии.
 */

const LS_PREFIX = 'iu_static_v1';

function lsKey(...parts) {
  return [LS_PREFIX, ...parts].join('::');
}

function readJSON(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (e) {
    console.warn('store: не удалось прочитать', key, e);
    return fallback;
  }
}

function writeJSON(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

const Store = {
  ASSUMPTION_REASONS: [
    'Использование ближайших доступных значений',
    'Данные смежных территорий',
    'Результаты геоинформационного анализа',
    'Экспертная оценка',
  ],

  getIndicatorResults(settlementCode) {
    return readJSON(lsKey('draft', settlementCode), {});
  },

  setIndicatorResult(settlementCode, componentKey, indicatorKey, entry) {
    const all = this.getIndicatorResults(settlementCode);
    all[`${componentKey}.${indicatorKey}`] = entry;
    writeJSON(lsKey('draft', settlementCode), all);
  },

  clearIndicatorResult(settlementCode, componentKey, indicatorKey) {
    const all = this.getIndicatorResults(settlementCode);
    delete all[`${componentKey}.${indicatorKey}`];
    writeJSON(lsKey('draft', settlementCode), all);
  },

  resetIndicatorResults(settlementCode) {
    writeJSON(lsKey('draft', settlementCode), {});
  },

  statusBadge(entry) {
    if (!entry) return '⚪ не заполнено';
    if (entry.isMissing) return '🔴 нет данных';
    if (entry.isAssumption) return '🟠 допущение';
    return '🟢 заполнено';
  },

  // --- Сохранённые расчёты (история) ---------------------------------
  getHistory(settlementCode) {
    return readJSON(lsKey('history', settlementCode), []);
  },

  saveResult(settlementCode, result) {
    const history = this.getHistory(settlementCode);
    const record = {
      id: `${settlementCode}-${Date.now()}`,
      settlementCode,
      calculatedAt: new Date().toISOString(),
      verificationStatus: 'не верифицировано',
      verificationComment: null,
      ...result,
    };
    history.push(record);
    writeJSON(lsKey('history', settlementCode), history);
    return record;
  },

  getLatest(settlementCode) {
    const history = this.getHistory(settlementCode);
    if (history.length === 0) return null;
    return history[history.length - 1];
  },

  updateVerification(settlementCode, recordId, status, comment) {
    const history = this.getHistory(settlementCode);
    const idx = history.findIndex((r) => r.id === recordId);
    if (idx === -1) return null;
    history[idx].verificationStatus = status;
    history[idx].verificationComment = comment || null;
    writeJSON(lsKey('history', settlementCode), history);
    return history[idx];
  },

  clearAll() {
    Object.keys(localStorage)
      .filter((k) => k.startsWith(LS_PREFIX))
      .forEach((k) => localStorage.removeItem(k));
  },
};

window.Store = Store;

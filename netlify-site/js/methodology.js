/**
 * JS-движок методики — прямой порт правил скоринга из
 * `vulnerability_index/methodology.py`, работающий над JSON-экспортом
 * (`data/methodology.json`), сгенерированным `scripts/export_static_data.py`
 * из той же YAML-конфигурации, что и серверное ядро.
 *
 * Это клиентская (статическая, Netlify) версия расчётного движка —
 * логика скоринга и агрегации формул полностью совпадает с Python-ядром
 * (см. tests/test_methodology.py и tests/test_aggregate.py для эталонных
 * значений), чтобы избежать расхождений между версиями.
 */

function ruleMatches(rule, value) {
  if ('eq' in rule && value !== rule.eq) return false;
  if ('lt' in rule && !(value < rule.lt)) return false;
  if ('lte' in rule && !(value <= rule.lte)) return false;
  if ('gt' in rule && !(value > rule.gt)) return false;
  if ('gte' in rule && !(value >= rule.gte)) return false;
  return true;
}

class Methodology {
  constructor(raw) {
    this.raw = raw;
    this.version = raw.version;
    this.effectiveDate = raw.effectiveDate;
    this.title = raw.title;
    this.approvedBy = raw.approvedBy;
    this.valueRange = raw.valueRange;
    this.components = raw.components;
    this.categories = raw.categories;
  }

  componentKeys() {
    return Object.keys(this.components);
  }

  indicatorKeys(componentKey) {
    return Object.keys(this.components[componentKey].indicators);
  }

  indicator(componentKey, indicatorKey) {
    return this.components[componentKey].indicators[indicatorKey];
  }

  /** Возвращает {score, label} либо бросает Error, как score_indicator() в Python. */
  scoreIndicator(componentKey, indicatorKey, rawValue) {
    const spec = this.indicator(componentKey, indicatorKey);
    if (spec.type === 'numeric_thresholds') {
      if (rawValue === null || rawValue === undefined || Number.isNaN(rawValue)) {
        throw new Error(`Показатель '${indicatorKey}': значение отсутствует`);
      }
      const numeric = Number(rawValue);
      for (const rule of spec.rules || []) {
        if (ruleMatches(rule, numeric)) {
          return { score: rule.score, label: rule.label };
        }
      }
      throw new Error(`Показатель '${indicatorKey}': значение ${numeric} не подходит ни под один интервал методики`);
    }
    if (spec.type === 'options') {
      const option = (spec.options || {})[rawValue];
      if (!option) {
        throw new Error(`Показатель '${indicatorKey}': неизвестная опция '${rawValue}'`);
      }
      return { score: option.score, label: option.label };
    }
    throw new Error(`Показатель '${indicatorKey}': неизвестный тип '${spec.type}'`);
  }

  optionChoices(componentKey, indicatorKey) {
    const spec = this.indicator(componentKey, indicatorKey);
    if (spec.type !== 'options') return [];
    return Object.entries(spec.options).map(([key, v]) => ({ key, label: v.label, score: v.score }));
  }

  /** indicatorScores: { indicatorKey: score|null } -> component value (renormalized over available), or null if none available. */
  computeComponent(componentKey, indicatorScores) {
    const spec = this.components[componentKey];
    const keys = Object.keys(spec.indicators);
    const totalWeight = keys.reduce((sum, k) => sum + spec.indicators[k].weight, 0);
    if (Math.abs(totalWeight - 1.0) > 1e-6) {
      throw new Error(`Компонент '${componentKey}': сумма весов показателей = ${totalWeight}, ожидалось 1.0`);
    }
    const present = keys.filter((k) => indicatorScores[k] !== null && indicatorScores[k] !== undefined);
    if (present.length === 0) return null;
    const weightSum = present.reduce((sum, k) => sum + spec.indicators[k].weight, 0);
    const weighted = present.reduce((sum, k) => sum + spec.indicators[k].weight * indicatorScores[k], 0);
    return weighted / weightSum;
  }

  /** componentValues: { componentKey: value|null } -> итоговый ИУ. */
  computeIndex(componentValues) {
    const keys = this.componentKeys();
    const present = keys.filter((k) => componentValues[k] !== null && componentValues[k] !== undefined);
    if (present.length === 0) {
      throw new Error('Нет ни одного рассчитанного компонента');
    }
    const weightSum = present.reduce((sum, k) => sum + this.components[k].weight, 0);
    const weighted = present.reduce((sum, k) => sum + this.components[k].weight * componentValues[k], 0);
    return weighted / weightSum;
  }

  categorize(indexValue) {
    for (const rule of this.categories.thresholds || []) {
      if (ruleMatches(rule, indexValue)) return rule.category;
    }
    return null;
  }

  categoriesApproved() {
    return Boolean(this.categories.approved);
  }
}

/**
 * Собирает итоговый результат (компоненты + индекс + категория) из
 * набора уже полученных значений показателей — аналог
 * `vulnerability_index.aggregate.aggregate_index_result`.
 *
 * @param {Methodology} methodology
 * @param {Object} indicatorResults - { "COMP.indicator": {rawValue, score, label, sourceName, sourceKind, isAssumption, assumptionReason, comment, isMissing} }
 */
function aggregateIndexResult(methodology, indicatorResults) {
  const components = [];
  for (const componentKey of methodology.componentKeys()) {
    const spec = methodology.components[componentKey];
    const indicatorKeys = Object.keys(spec.indicators);
    const indicators = [];
    const scores = {};
    for (const indKey of indicatorKeys) {
      const entry = indicatorResults[`${componentKey}.${indKey}`];
      if (!entry) continue;
      indicators.push({ key: indKey, componentKey, ...entry });
      if (entry.score !== null && entry.score !== undefined) {
        scores[indKey] = entry.score;
      }
    }
    let value = null;
    if (Object.keys(scores).length > 0) {
      value = methodology.computeComponent(componentKey, scores);
    }
    components.push({
      key: componentKey,
      title: spec.title,
      weight: spec.weight,
      value,
      indicators,
    });
  }

  const componentValues = {};
  for (const c of components) {
    if (c.value !== null) componentValues[c.key] = c.value;
  }
  const indexValue = methodology.computeIndex(componentValues);
  const category = methodology.categorize(indexValue);
  const hasAssumptions = components.some((c) => c.indicators.some((i) => i.isAssumption));
  const hasMissing = components.some((c) => c.indicators.some((i) => i.isMissing));

  return { value: indexValue, category, components, hasAssumptions, hasMissing };
}

window.Methodology = Methodology;
window.aggregateIndexResult = aggregateIndexResult;

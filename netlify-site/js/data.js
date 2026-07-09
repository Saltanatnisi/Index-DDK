/**
 * Загрузка статических JSON-данных (методика, реестр, демо-источники),
 * сгенерированных `scripts/export_static_data.py` из того же ядра, что
 * и полная Python/веб-версия модуля.
 */

const AppData = {
  methodology: null,
  settlements: null,
  demoSources: null,
  sourcesOverview: null,

  async load() {
    const [methodologyRaw, settlements, demoSources, sourcesOverview] = await Promise.all([
      fetch('data/methodology.json').then((r) => r.json()),
      fetch('data/settlements.json').then((r) => r.json()),
      fetch('data/demo_sources.json').then((r) => r.json()),
      fetch('data/sources_overview.json').then((r) => r.json()),
    ]);
    this.methodology = new Methodology(methodologyRaw);
    this.settlements = settlements;
    this.demoSources = demoSources;
    this.sourcesOverview = sourcesOverview;
    return this;
  },

  settlementByCode(code) {
    return this.settlements.find((s) => s.code === code);
  },
};

window.AppData = AppData;

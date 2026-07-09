/**
 * Точка входа и роутер статического приложения (замена `webapp/app.py` +
 * `st.navigation` из Streamlit-версии, но на клиентском JS с
 * хеш-роутингом, подходящим для статического хостинга на Netlify).
 */

const NAV_ITEMS = [
  { hash: 'overview', label: 'Обзор', icon: '🏠', view: 'overview' },
  { hash: 'dialog', label: 'Диалоговый расчёт', icon: '🧮', view: 'dialog' },
  { hash: 'dashboard', label: 'Дашборд', icon: '📊', view: 'dashboard' },
  { hash: 'registry', label: 'Реестр населённых пунктов', icon: '🗂️', view: 'registry' },
  { hash: 'sources', label: 'Источники данных', icon: '🔌', view: 'sources' },
  { hash: 'methodology', label: 'Методика', icon: '📐', view: 'methodology' },
  { hash: 'verification', label: 'Верификация', icon: '✅', view: 'verification' },
];

// Общее состояние, переживающее переключение страниц (выбранный н.п. и т.п.)
const ctx = {};

function currentHash() {
  const h = (window.location.hash || '#overview').replace('#', '');
  return NAV_ITEMS.some((i) => i.hash === h) ? h : 'overview';
}

function renderNav() {
  const nav = document.getElementById('sidebar-nav');
  const active = currentHash();
  nav.innerHTML = NAV_ITEMS.map((item) => `
    <a href="#${item.hash}" class="nav-link ${item.hash === active ? 'active' : ''}">
      <span class="nav-icon">${item.icon}</span> ${item.label}
    </a>`).join('');
}

function renderCurrentView() {
  Modal.close();
  const hash = currentHash();
  const item = NAV_ITEMS.find((i) => i.hash === hash);
  renderNav();
  const root = document.getElementById('view-root');
  root.innerHTML = '';
  try {
    window.Views[item.view](root, ctx);
  } catch (e) {
    console.error(e);
    root.innerHTML = `<div class="alert alert-error">Ошибка отображения страницы: ${e.message}</div>`;
  }
}

window.addEventListener('hashchange', renderCurrentView);

async function boot() {
  try {
    await AppData.load();
  } catch (e) {
    document.getElementById('view-root').innerHTML =
      `<div class="alert alert-error">Не удалось загрузить данные приложения: ${e.message}</div>`;
    return;
  }
  renderCurrentView();
}

boot();

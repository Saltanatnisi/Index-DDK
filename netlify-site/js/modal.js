/**
 * Модальное диалоговое окно — используется страницей «Диалоговый
 * расчёт» для сбора показателей (аналог `st.dialog` в веб-версии на
 * Streamlit).
 */

const Modal = {
  _escHandler: null,

  open(titleHtml) {
    this.close();
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.id = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal-box" role="dialog" aria-modal="true">
        <div class="modal-header">
          <h3>${titleHtml}</h3>
          <button class="modal-close" aria-label="Закрыть">&times;</button>
        </div>
        <div class="modal-body"></div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.querySelector('.modal-close').addEventListener('click', () => this.close());
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) this.close();
    });
    this._escHandler = (e) => {
      if (e.key === 'Escape') this.close();
    };
    document.addEventListener('keydown', this._escHandler);
    return overlay.querySelector('.modal-body');
  },

  close() {
    const el = document.getElementById('modal-overlay');
    if (el) el.remove();
    if (this._escHandler) {
      document.removeEventListener('keydown', this._escHandler);
      this._escHandler = null;
    }
  },
};

window.Modal = Modal;

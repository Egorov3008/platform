export const Toast = {
    show(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const el = document.createElement('div');
        el.className = `toast ${type}`;
        const icons = { success: '✓', error: '✕', info: 'ℹ' };
        el.innerHTML = `<span style="font-weight:700;font-size:1.1rem">${icons[type] || icons.info}</span><span>${this._esc(message)}</span>`;
        container.appendChild(el);
        setTimeout(() => {
            el.style.transition = 'opacity 0.3s';
            el.style.opacity = '0';
            setTimeout(() => el.remove(), 300);
        }, 4000);
    },
    success(m) { this.show(m, 'success'); },
    error(m) { this.show(m, 'error'); },
    info(m) { this.show(m, 'info'); },
    _esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; },
};

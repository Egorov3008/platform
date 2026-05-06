import { Auth } from './auth.js?v=2';
import { Router } from './router.js?v=2';
import { Modal } from './modal.js?v=2';
import { Admin } from './admin.js?v=2';

document.addEventListener('DOMContentLoaded', async () => {
    // Theme initialization
    function initTheme() {
        const saved = localStorage.getItem('vpn-theme');
        const preferred = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        const theme = saved || preferred;
        document.documentElement.setAttribute('data-theme', theme);

        const btn = document.getElementById('themeToggle');
        if (btn) {
            btn.style.display = 'flex';
            btn.addEventListener('click', () => {
                const current = document.documentElement.getAttribute('data-theme');
                const next = current === 'dark' ? 'light' : 'dark';
                document.documentElement.setAttribute('data-theme', next);
                localStorage.setItem('vpn-theme', next);
            });
        }
    }
    initTheme();

    document.getElementById('hamburgerBtn').addEventListener('click', () => Router.openMenu());
    document.getElementById('navOverlay').addEventListener('click', () => Router.closeMenu());
    document.getElementById('modalOverlay').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) Modal.close();
    });

    await Auth.init();

    const hash = window.location.hash || '#/login';
    if (Auth.isLoggedIn() && hash === '#/login') {
        Router.navigate('#/dashboard');
    } else if (!Auth.isLoggedIn() && hash !== '#/login' && hash !== '#/tariffs') {
        Router.navigate('#/login');
    }

    Router.init();

    window.Admin = Admin;
    window.Modal = Modal;
    window.Router = Router;
});

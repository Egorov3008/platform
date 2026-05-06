import { Auth } from './auth.js?v=2';
import { Router } from './router.js?v=2';
import { Modal } from './modal.js?v=2';
import { Admin } from './admin.js?v=2';

document.addEventListener('DOMContentLoaded', async () => {
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

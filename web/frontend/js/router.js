import { Auth } from './auth.js';
import { Toast } from './toast.js';
import { Logger } from './logger.js';

export const Router = {
    routes: {
        '#/login': { page: 'login', auth: false },
        '#/code-login': { page: 'codeLogin', auth: false },
        '#/dashboard': { page: 'dashboard', auth: true },
        '#/tariffs': { page: 'tariffs', auth: false },
        '#/payments': { page: 'payments', auth: true },
        '#/admin': { page: 'admin', auth: true, admin: true },
    },

    init() {
        Logger.group('Router', 'init');
        Logger.log('Router', 'Текущий hash:', window.location.hash || '(пусто)');
        Logger.log('Router', 'Регистрация hashchange обработчика');
        window.addEventListener('hashchange', () => {
            Logger.log('Router', 'hashchange →', window.location.hash || '#/login');
            this.handle();
        });
        Logger.log('Router', 'Первичная обработка маршрута');
        this.handle();
        Logger.groupEnd();
    },

    navigate(hash) {
        Logger.log('Router', 'navigate →', hash);
        window.location.hash = hash;
    },

    async handle() {
        const { Pages } = await import('./pages.js?v=2');

        const hash = window.location.hash || '#/login';
        Logger.group('Router', 'handle: ' + hash);

        const route = this.routes[hash];

        if (!route) {
            Logger.warn('Router', '  ✗ Маршрут не найден — редирект на #/login');
            this.navigate('#/login');
            Logger.groupEnd();
            return;
        }

        Logger.log('Router', '  Маршрут найден: page=', route.page, '| auth=', route.auth, '| admin=', route.admin);

        if (route.auth && !Auth.isLoggedIn()) {
            Logger.warn('Router', '  ✗ Требуется авторизация, но пользователь не вошёл — редирект на #/login');
            Toast.error('Необходима авторизация');
            this.navigate('#/login');
            Logger.groupEnd();
            return;
        }

        if (route.admin && !Auth.isAdmin()) {
            Logger.warn('Router', '  ✗ Требуется админ, но пользователь не админ — редирект на #/dashboard');
            Toast.error('Доступ только для администраторов');
            this.navigate('#/dashboard');
            Logger.groupEnd();
            return;
        }

        Logger.log('Router', '  ✓ Проверки пройдены, рендер страницы:', route.page);
        this.render(route.page);
        this.updateNav(hash);
        Logger.groupEnd();
    },

    async render(page) {
        Logger.group('Router', 'render: ' + page);
        const main = document.getElementById('mainContent');
        if (!main) {
            Logger.error('Router', '  ✗ Элемент #mainContent не найден!');
            Logger.groupEnd();
            return;
        }
        const { Pages } = await import('./pages.js?v=2');
        const renderers = {
            login: Pages.login,
            codeLogin: Pages.codeLogin,
            dashboard: Pages.dashboard,
            tariffs: Pages.tariffs,
            payments: Pages.payments,
            admin: Pages.admin,
        };
        main.innerHTML = '';
        const renderer = renderers[page];
        if (renderer) {
            Logger.log('Router', '  Вызов рендера страницы:', page);
            renderer.call(Pages, main);
        } else {
            Logger.error('Router', '  ✗ Рендерер для страницы', page, 'не найден');
        }
        Logger.groupEnd();
    },

    updateNav(currentHash) {
        const nav = document.getElementById('mainNav');
        const links = [
            { hash: '#/dashboard', icon: 'dashboard', label: 'Мои ключи' },
            { hash: '#/tariffs', icon: 'tariffs', label: 'Тарифы' },
            { hash: '#/payments', icon: 'payments', label: 'Платежи' },
        ];
        if (Auth.isAdmin()) {
            links.push({ hash: '#/admin', icon: 'admin', label: 'Админ-панель' });
        }

        const isLoggedIn = Auth.isLoggedIn();
        let html = '<button class="nav-close" id="navClose">&times;</button>';
        if (isLoggedIn) {
            links.forEach(l => {
                const active = currentHash === l.hash ? 'active' : '';
                html += `<a href="${l.hash}" class="${active}" data-nav="${l.hash}">${this.iconSvg(l.icon)} ${l.label}</a>`;
            });
            html += `<div class="nav-user"><button class="btn btn-secondary btn-sm" id="logoutBtn" style="width:100%">Выйти</button></div>`;
        } else {
            html += `<a href="#/login" class="${currentHash === '#/login' ? 'active' : ''}" data-nav="#/login">${this.iconSvg('login')} Вход</a>`;
        }
        nav.innerHTML = html;

        // Re-bind close/logout
        document.getElementById('navClose')?.addEventListener('click', () => this.closeMenu());
        document.getElementById('logoutBtn')?.addEventListener('click', () => Auth.logout().catch(() => {}));
        const headerLogoutBtn = document.getElementById('headerLogoutBtn');
        if (headerLogoutBtn) {
            headerLogoutBtn.style.display = isLoggedIn ? '' : 'none';
            headerLogoutBtn.onclick = () => Auth.logout().catch(() => {});
        }
        nav.querySelectorAll('[data-nav]').forEach(a => {
            a.addEventListener('click', () => this.closeMenu());
        });
    },

    iconSvg(name) {
        const icons = {
            dashboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
            tariffs: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
            payments: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>',
            admin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
            login: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>',
            register: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></svg>',
        };
        return icons[name] || '';
    },

    openMenu() {
        document.getElementById('mainNav').classList.add('active');
        document.getElementById('navOverlay').classList.add('active');
    },
    closeMenu() {
        document.getElementById('mainNav').classList.remove('active');
        document.getElementById('navOverlay').classList.remove('active');
    },
};

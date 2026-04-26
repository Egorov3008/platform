import { API } from './api.js';

export const Auth = {
    _user: null,

    async init() {
        try {
            this._user = await API.get('/auth/me');
        } catch (_) {
            this._user = null;
        }
    },

    isLoggedIn() { return !!this._user; },
    isAdmin() { return this._user?.is_admin || false; },
    getUser() { return this._user; },

    async login(code) {
        await API.post('/auth/login', { code });
        await this.init();
    },

    async refresh() {
        try {
            await API.post('/auth/refresh');
            await this.init();
            return true;
        } catch (_) {
            this._user = null;
            return false;
        }
    },

    async logout() {
        try { await API.post('/auth/logout'); } catch (_) {}
        this._user = null;
        // Router import inside function to avoid circular deps
        const { Router } = await import('./router.js');
        Router.navigate('#/login');
    },
};

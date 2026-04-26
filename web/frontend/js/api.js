import { Logger } from './logger.js';

export const API = {
    _getCsrfToken() {
        const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
        return match ? decodeURIComponent(match[1]) : null;
    },

    async request(method, path, body = null) {
        // Import inside function to avoid circular dependency at module eval time
        const { Auth } = await import('./auth.js');
        const { Router } = await import('./router.js');

        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
        };
        if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
            const csrf = this._getCsrfToken();
            if (csrf) opts.headers['X-CSRF-Token'] = csrf;
        }
        if (body !== null) {
            opts.body = JSON.stringify(body);
        }

        const url = `/api/v1${path}`;
        let resp;
        try {
            resp = await fetch(url, opts);
        } catch (err) {
            throw new Error(`Сетевая ошибка: ${err.message}`);
        }

        if (resp.status === 401) {
            if (path === '/auth/refresh') {
                Auth._user = null;
                Router.navigate('#/login');
                throw new Error('Необходима авторизация');
            }
            const refreshed = await Auth.refresh();
            if (refreshed) {
                const csrf2 = this._getCsrfToken();
                if (csrf2) opts.headers['X-CSRF-Token'] = csrf2;
                const resp2 = await fetch(url, opts);
                return await this._handleResp(resp2);
            }
            Auth._user = null;
            Router.navigate('#/login');
            throw new Error('Необходима авторизация');
        }

        if (resp.status === 204) return null;
        return await this._handleResp(resp);
    },

    async _handleResp(resp) {
        if (!resp.ok) {
            let msg = `Ошибка ${resp.status}`;
            try {
                const data = await resp.json();
                if (data.detail) {
                    msg = Array.isArray(data.detail)
                        ? data.detail.map(d => d.msg).join(', ')
                        : data.detail;
                }
            } catch (_) {}
            throw new Error(msg);
        }
        return await resp.json();
    },

    get(path) { return this.request('GET', path); },
    post(path, body) { return this.request('POST', path, body); },
    patch(path, body) { return this.request('PATCH', path, body); },
    delete(path) { return this.request('DELETE', path); },
};

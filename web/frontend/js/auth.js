import { API } from './api.js';

export const Auth = {
    _user: null,
    __captchaToken: null,
    __captchaTimestamp: null,

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

    async initLoginPage() {
        // Load captcha and mount Telegram widget
        await this._loadCaptcha();
        const cfg = await API.get('/auth/config').catch(() => ({}));
        this._mountTelegramWidget(cfg.telegram_bot_username);
    },

    async _loadCaptcha() {
        try {
            const data = await API.get('/auth/captcha');
            this.__captchaToken = data.token;
            this.__captchaTimestamp = data.timestamp;
            const question = document.getElementById('captcha-question');
            if (question) {
                question.textContent = `${data.question} = ?`;
            }
            const answer = document.getElementById('captcha-answer');
            if (answer) {
                answer.value = '';
            }
        } catch (err) {
            console.error('Failed to load captcha:', err);
        }
    },

    _mountTelegramWidget(botUsername) {
        if (!botUsername) return;
        const container = document.getElementById('telegram-widget-container');
        if (!container) return;
        container.innerHTML = '';
        const script = document.createElement('script');
        script.async = true;
        script.src = 'https://telegram.org/js/telegram-widget.js?22';
        script.setAttribute('data-telegram-login', botUsername);
        script.setAttribute('data-size', 'large');
        script.setAttribute('data-onauth', 'onTelegramAuth');
        script.setAttribute('data-request-access', 'write');
        container.appendChild(script);
    },

    async loginViaTelegram(telegramData, captchaAnswer) {
        // POST to /telegram-callback with captcha and telegram data
        await API.post('/auth/telegram-callback', {
            telegram_data: telegramData,
            captcha_token: this.__captchaToken,
            captcha_timestamp: this.__captchaTimestamp,
            captcha_answer: captchaAnswer,
        });
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

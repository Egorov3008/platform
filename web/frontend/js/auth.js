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
        if (!botUsername) {
            console.error('Telegram bot username is not configured');
            const container = document.getElementById('telegram-widget-container');
            if (container) {
                container.innerHTML = '<div style="color: var(--error); text-align: center; padding: 16px;">Telegram авторизация недоступна</div>';
            }
            return;
        }
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
        await API.post('/auth/telegram-callback', {
            telegram_data: telegramData,
            captcha_token: this.__captchaToken,
            captcha_timestamp: this.__captchaTimestamp,
            captcha_answer: captchaAnswer,
        });
        await this.init();
    },

    async loginWithCode(code) {
        await API.post('/auth/login', { code });
        await this.init();
    },

    async loginViaTelegramNoCaptcha(telegramData) {
        await API.post('/auth/telegram-login', { telegram_data: telegramData });
        await this.init();
    },

    async initCodeLoginPage() {
        const cfg = await API.get('/auth/config').catch(() => ({}));
        this._mountTelegramWidgetTo('tg-widget-strip', cfg.telegram_bot_username, 'onTelegramAuthStrip');

        const form = document.getElementById('code-login-form');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const codeInput = document.getElementById('login-code-input');
                const errorEl = document.getElementById('code-login-error');
                const code = (codeInput.value || '').trim().toUpperCase();
                if (!code || code.length !== 8) {
                    errorEl.textContent = 'Введите 8-значный код';
                    errorEl.style.display = '';
                    return;
                }
                errorEl.style.display = 'none';
                try {
                    await this.loginWithCode(code);
                    const { Router } = await import('./router.js');
                    Router.navigate('#/dashboard');
                } catch (err) {
                    errorEl.textContent = err.message || 'Неверный или просроченный код';
                    errorEl.style.display = '';
                    codeInput.value = '';
                    codeInput.focus();
                }
            });
        }

        window.onTelegramAuthStrip = async (user) => {
            const errorEl = document.getElementById('tg-strip-error');
            try {
                await this.loginViaTelegramNoCaptcha(user);
                const { Router } = await import('./router.js');
                Router.navigate('#/dashboard');
            } catch (err) {
                if (errorEl) {
                    errorEl.textContent = err.message || 'Ошибка при входе через Telegram';
                    errorEl.style.display = '';
                }
            }
        };
    },

    _mountTelegramWidgetTo(containerId, botUsername, callbackName) {
        const container = document.getElementById(containerId);
        if (!container) return;
        if (!botUsername) {
            container.innerHTML = '<div style="color: var(--error); text-align: center; padding: 8px;">Telegram недоступен</div>';
            return;
        }
        container.innerHTML = '';
        const script = document.createElement('script');
        script.async = true;
        script.src = 'https://telegram.org/js/telegram-widget.js?22';
        script.setAttribute('data-telegram-login', botUsername);
        script.setAttribute('data-size', 'medium');
        script.setAttribute('data-onauth', callbackName);
        script.setAttribute('data-request-access', 'write');
        container.appendChild(script);
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

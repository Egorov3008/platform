import { API } from './api.js';
import { Auth } from './auth.js';
import { Toast } from './toast.js';
import { Modal } from './modal.js';

const _esc = function(s) {
    if (s === null || s === undefined) return '';
    const d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
};

const _periodStr = function(days) {
    if (!days) return '1 день';
    if (days === 1) return '1 день';
    if (days < 7) return `${days} ${_pluralize(days, 'день', 'дня', 'дней')}`;
    if (days === 7) return '7 дней';
    if (days < 30) return `${days} дней`;
    if (days === 30) return '30 дней';
    return `${days} дней`;
};

const _pluralize = function(n, one, few, many) {
    const mod10 = n % 10;
    const mod100 = n % 100;
    if (mod100 >= 11 && mod100 <= 19) return many;
    if (mod10 === 1) return one;
    if (mod10 >= 2 && mod10 <= 4) return few;
    return many;
};

const _calcPrice = function(amountPerMonth, months, discountPct) {
    const base = amountPerMonth * months;
    const hasDiscount = months >= 2 && discountPct > 0;
    const total = hasDiscount ? Math.round(base * (1 - discountPct / 100) * 100) / 100 : base;
    return { base, total, saving: Math.round((base - total) * 100) / 100, hasDiscount };
};

const PaymentModal = {
    _discountPct: null,
    _paymentId: null,
    _paymentUrl: null,

    async _fetchConfig() {
        if (this._discountPct !== null) return;
        try {
            const cfg = await API.get('/payments/config');
            this._discountPct = cfg.volume_discount_percent || 0;
        } catch (_) {
            this._discountPct = 0;
        }
    },

    async open({ tariffId, tariffName, amountPerMonth, renewClientId = null, onSuccess }) {
        await this._fetchConfig();
        this._paymentId = null;
        this._paymentUrl = null;

        const discountPct = this._discountPct;
        let months = 1;

        const renderSelection = () => {
            const price = _calcPrice(amountPerMonth, months, discountPct);
            const monthWord = _pluralize(months, 'месяц', 'месяца', 'месяцев');
            const dots = Array.from({ length: 6 }, (_, i) =>
                `<div style="width:10px;height:10px;border-radius:50%;background:${i < months ? 'var(--accent)' : 'var(--surface-2)'};"></div>`
            ).join('');

            let priceBlock;
            if (price.hasDiscount) {
                priceBlock = `
                    <div style="background:var(--surface-2);border-radius:10px;padding:12px 16px;margin-bottom:8px;">
                        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                            <span style="font-size:12px;color:var(--text-secondary);">${months} × ${amountPerMonth} ₽</span>
                            <span style="font-size:12px;color:var(--text-secondary);text-decoration:line-through;">${price.base} ₽</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                            <span style="font-size:12px;color:var(--success);">🔥 Скидка ${discountPct}%</span>
                            <span style="font-size:12px;color:var(--success);">−${price.saving} ₽</span>
                        </div>
                        <div style="border-top:1px solid var(--border);padding-top:8px;display:flex;justify-content:space-between;align-items:center;">
                            <span style="font-size:13px;color:var(--text-secondary);">Итого</span>
                            <span style="font-size:22px;font-weight:700;color:var(--text);">${price.total} ₽</span>
                        </div>
                    </div>`;
            } else {
                priceBlock = `
                    <div style="background:var(--surface-2);border-radius:10px;padding:12px 16px;margin-bottom:8px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span style="font-size:13px;color:var(--text-secondary);">Итого</span>
                            <span style="font-size:22px;font-weight:700;color:var(--text);">${price.total} ₽</span>
                        </div>
                    </div>`;
            }

            const hint = months === 6
                ? `<div style="font-size:14px;color:var(--text-secondary);text-align:center;margin-bottom:16px;">💡 Максимум 6 месяцев</div>`
                : months === 1 && discountPct > 0
                ? `<div style="font-size:14px;color:var(--text-secondary);text-align:center;margin-bottom:16px;font-weight:500;">🎁 Скидка ${discountPct}% при оплате от 2 месяцев</div>`
                : `<div style="height:16px;margin-bottom:16px;"></div>`;

            const counterColor = price.hasDiscount ? 'var(--accent)' : 'var(--text)';
            const minusStyle = `width:40px;height:40px;border-radius:50%;border:2px solid ${months > 1 ? 'var(--accent)' : 'var(--border)'};color:${months > 1 ? 'var(--accent)' : 'var(--text-tertiary)'};display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:300;background:transparent;cursor:${months > 1 ? 'pointer' : 'default'};`;
            const plusStyle = `width:40px;height:40px;border-radius:50%;border:2px solid ${months < 6 ? 'var(--accent)' : 'var(--border)'};color:${months < 6 ? 'var(--accent)' : 'var(--text-tertiary)'};display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:300;background:transparent;cursor:${months < 6 ? 'pointer' : 'default'};`;

            return `
                <div style="font-weight:700;font-size:16px;margin-bottom:4px;">💳 Оформление платежа</div>
                <div style="font-size:13px;color:var(--text-secondary);margin-bottom:20px;">Тариф: <b style="color:var(--text);">${_esc(tariffName)} · ${amountPerMonth} ₽/мес</b></div>
                <div style="text-align:center;margin-bottom:12px;">
                    <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;">Срок подписки</div>
                    <div style="display:flex;justify-content:center;align-items:center;gap:20px;">
                        <button id="pmMinus" style="${minusStyle}"${months === 1 ? ' disabled' : ''}>−</button>
                        <div style="text-align:center;">
                            <div style="font-size:42px;font-weight:700;line-height:1;color:${counterColor};">${months}</div>
                            <div style="font-size:12px;color:var(--text-secondary);">${monthWord}</div>
                        </div>
                        <button id="pmPlus" style="${plusStyle}"${months === 6 ? ' disabled' : ''}>+</button>
                    </div>
                </div>
                <div style="display:flex;justify-content:center;gap:8px;margin-bottom:16px;">${dots}</div>
                ${priceBlock}
                ${hint}
                <div style="display:grid;grid-template-columns:1fr 2fr;gap:8px;">
                    <button id="pmCancel" style="padding:12px;border:1px solid var(--border);border-radius:8px;font-size:14px;cursor:pointer;color:var(--text-secondary);background:transparent;font-weight:500;">Отмена</button>
                    <button id="pmConfirm" style="padding:14px;background:var(--primary);color:white;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;border:none;box-shadow:0 2px 8px rgba(13, 115, 119, 0.3);">Оплатить</button>
                </div>`;
        };

        const renderWaiting = () => {
            return `
                <div style="text-align:center;padding:20px 0;">
                    <div style="font-size:48px;margin-bottom:16px;">⏳</div>
                    <div style="font-weight:700;font-size:16px;margin-bottom:8px;">Ожидаем подтверждения платежа</div>
                    <div style="font-size:14px;color:var(--text-secondary);margin-bottom:24px;">Ссылка на оплату открыта в новой вкладке. Завершите платёж и нажмите кнопку ниже.</div>
                    <div style="display:grid;grid-template-columns:1fr;gap:8px;">
                        <button id="pmCheck" style="padding:14px;background:var(--primary);color:white;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;border:none;box-shadow:0 2px 8px rgba(13, 115, 119, 0.3);">✓ Проверить оплату</button>
                        <button id="pmOpenLink" style="padding:12px;border:1px solid var(--border);border-radius:8px;font-size:14px;cursor:pointer;color:var(--text-secondary);background:transparent;font-weight:500;">Открыть ссылку снова</button>
                        <button id="pmWaitCancel" style="padding:12px;border:1px solid var(--border);border-radius:8px;font-size:14px;cursor:pointer;color:var(--error);background:transparent;font-weight:500;">Отмена</button>
                    </div>
                </div>`;
        };

        const renderSuccess = () => {
            return `
                <div style="text-align:center;padding:40px 0;">
                    <div style="font-size:64px;margin-bottom:16px;animation:bounce 0.6s ease;animation-iteration-count:1;">✓</div>
                    <div style="font-weight:700;font-size:20px;color:var(--success);margin-bottom:8px;">Платёж успешно обработан!</div>
                    <div style="font-size:14px;color:var(--text-secondary);margin-bottom:24px;">Ваш ключ готов к использованию</div>
                    <div style="display:inline-block;padding:12px 20px;background:var(--success-bg);border-radius:8px;color:var(--success);font-size:14px;">🎉 Ключ создан успешно</div>
                </div>
                <style>
                    @keyframes bounce {
                        0%, 100% { transform: scale(0.3); opacity: 0; }
                        50% { transform: scale(1.1); }
                        100% { transform: scale(1); opacity: 1; }
                    }
                </style>`;
        };

        Modal.open(`<div id="pmContent">${renderSelection()}</div>`);

        const update = (state) => {
            const el = document.getElementById('pmContent');
            if (!el) return;
            if (state === 'selection') {
                el.innerHTML = renderSelection();
                bindSelection();
            } else if (state === 'waiting') {
                el.innerHTML = renderWaiting();
                bindWaiting();
            } else if (state === 'success') {
                el.innerHTML = renderSuccess();
                setTimeout(() => {
                    Modal.close();
                    if (onSuccess) onSuccess();
                }, 2000);
            }
        };

        const bindSelection = () => {
            const minus = document.getElementById('pmMinus');
            const plus = document.getElementById('pmPlus');
            const confirmBtn = document.getElementById('pmConfirm');
            const cancelBtn = document.getElementById('pmCancel');

            if (minus) minus.addEventListener('click', () => { if (months > 1) { months--; update('selection'); } });
            if (plus) plus.addEventListener('click', () => { if (months < 6) { months++; update('selection'); } });
            if (cancelBtn) cancelBtn.addEventListener('click', () => Modal.close());
            if (confirmBtn) confirmBtn.addEventListener('click', async () => {
                confirmBtn.disabled = true;
                confirmBtn.textContent = 'Загрузка…';
                try {
                    let res;
                    if (renewClientId) {
                        res = await API.post('/payments/renew', {
                            client_id: renewClientId,
                            tariff_id: tariffId,
                            number_of_months: months,
                        });
                    } else {
                        res = await API.post('/payments/create', {
                            tariff_id: tariffId,
                            number_of_months: months,
                        });
                    }
                    this._paymentUrl = res.payment_url;
                    this._paymentId = res.payment_id;
                    window.open(res.payment_url, '_blank');
                    update('waiting');
                } catch (err) {
                    Toast.error(err.message);
                    confirmBtn.disabled = false;
                    confirmBtn.textContent = 'Оплатить';
                }
            });
        };

        const bindWaiting = () => {
            const checkBtn = document.getElementById('pmCheck');
            const linkBtn = document.getElementById('pmOpenLink');
            const cancelBtn = document.getElementById('pmWaitCancel');

            if (checkBtn) {
                checkBtn.addEventListener('click', async () => {
                    checkBtn.disabled = true;
                    checkBtn.textContent = 'Проверка…';
                    try {
                        const status = await API.get(`/payments/${this._paymentId}/status`);
                        if (status.processed || status.status === 'succeeded') {
                            update('success');
                        } else {
                            Toast.show('Платёж ещё не обработан. Попробуйте позже.', 'warning');
                            checkBtn.disabled = false;
                            checkBtn.textContent = '✓ Проверить оплату';
                        }
                    } catch (err) {
                        Toast.error(err.message);
                        checkBtn.disabled = false;
                        checkBtn.textContent = '✓ Проверить оплату';
                    }
                });
            }
            if (linkBtn) {
                linkBtn.addEventListener('click', () => {
                    if (this._paymentUrl) {
                        window.open(this._paymentUrl, '_blank');
                    }
                });
            }
            if (cancelBtn) {
                cancelBtn.addEventListener('click', () => Modal.close());
            }
        };

        bindSelection();
    },
};

export const Pages = {
    _esc,
    _periodStr,
    _pluralize,

    async login(container) {
        const cfg = await API.get('/auth/config').catch(() => ({}));
        const botLink = cfg.telegram_bot_username ? `https://t.me/${cfg.telegram_bot_username}${cfg.invite_token ? `?start=${cfg.invite_token}` : ''}` : null;

        container.innerHTML = `
        <div class="auth-container">
            <div class="auth-card">
                <h1>Вход по коду</h1>
                ${botLink ? `<button type="button" id="bot-link-btn" class="btn btn-secondary" style="width: 100%; margin-bottom: 16px;">Получить код в Telegram-боте</button>` : '<p class="subtitle">Получите код в Telegram-боте командой /start</p>'}

                <form id="code-login-form" autocomplete="off">
                    <div style="margin-bottom: 16px;">
                        <input
                            type="text"
                            id="login-code-input"
                            placeholder="XXXXXXXX"
                            maxlength="8"
                            autocomplete="off"
                            spellcheck="false"
                            style="width: 100%; padding: 14px; border: 1px solid var(--border); border-radius: 8px;
                                   background: var(--background); color: var(--text); font-size: 22px;
                                   letter-spacing: 6px; text-align: center; text-transform: uppercase; font-weight: 600;"
                        >
                    </div>
                    <button type="submit" class="btn btn-primary" style="width: 100%;">Войти</button>
                </form>

                <p id="code-login-error" style="color: var(--error); display: none; text-align: center; margin-top: 12px; font-size: 14px;"></p>

                <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid var(--border); text-align: center;">
                    <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 12px;">Новый пользователь? Войдите через Telegram</p>
                    <div id="tg-widget-strip" style="display: flex; justify-content: center;"></div>
                    <p id="tg-strip-error" style="color: var(--error); display: none; text-align: center; margin-top: 8px; font-size: 14px;"></p>
                </div>
            </div>
        </div>`;

        if (botLink) {
            const botBtn = document.getElementById('bot-link-btn');
            if (botBtn) {
                botBtn.addEventListener('click', () => {
                    window.open(botLink, '_blank');
                });
            }
        }

        const codeInput = document.getElementById('login-code-input');
        if (codeInput) {
            codeInput.addEventListener('input', (e) => {
                e.target.value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
            });
            codeInput.focus();
        }

        await Auth.initCodeLoginPage();
    },

    async dashboard(container) {
        container.innerHTML = `<div class="loading-page page-loading"><div class="spinner"></div></div>`;

        try {
            const [keys, tariffs, user] = await Promise.all([
                API.get('/keys/').catch(() => []),
                API.get('/tariffs/').catch(() => []),
                API.get('/users/me').catch(() => null),
            ]);

            const now = Date.now() / 1000;
            let html = '';

            // Keys section
            if (keys && keys.length > 0) {
                html += `<div class="section-header"><h2>Мои ключи</h2></div>`;
                html += '<div class="keys-grid">';
                keys.forEach(k => {
                    const expiryDate = k.expiry_time ? new Date(k.expiry_time) : null;
                    const isExpired = expiryDate && expiryDate.getTime() / 1000 < now;
                    const isExpiring = expiryDate && !isExpired && (expiryDate.getTime() / 1000 - now) < 3 * 24 * 3600;
                    const badgeClass = isExpired ? 'expired' : (isExpiring ? 'expiring' : 'active');
                    const badgeText = isExpired ? 'Истёк' : (isExpiring ? 'Скоро истекает' : 'Активен');
                    const trafficStr = (k.used_traffic !== null && k.used_traffic !== undefined)
                        ? `${(k.used_traffic / 1073741824).toFixed(2)} ГБ`
                        : '—';

                    html += `
                    <div class="card key-card" data-client-id="${k.client_id}">
                        <div class="key-card-header">
                            <h3>${_esc(k.name_tariff || k.email || 'VPN ключ')}</h3>
                            ${k.is_trial ? '<span class="key-badge trial">Пробный</span>' : ''}
                            <span class="key-badge ${badgeClass}">${badgeText}</span>
                        </div>
                        <div class="key-meta">
                            <div class="key-meta-row">
                                <span>Тариф</span>
                                <strong>${_esc(k.name_tariff || '—')}</strong>
                            </div>
                            <div class="key-meta-row">
                                <span>Истекает</span>
                                <strong>${expiryDate ? expiryDate.toLocaleDateString('ru-RU') : '—'}</strong>
                            </div>
                        </div>
                        <div class="key-value">
                            <span class="key-value-text">${_esc(k.key || '—')}</span>
                            <button class="copy-btn" data-key="${_esc(k.key)}">Копировать</button>
                        </div>
                        <div class="key-actions">
                            <button class="btn btn-secondary btn-sm btn-renew" data-id="${k.email}" data-tariff="${k.tariff_id || ''}" data-client-id="${k.client_id}">Продлить</button>
                            <button class="btn btn-danger btn-sm btn-delete-key" data-id="${k.email}">Удалить</button>
                        </div>
                    </div>`;
                });
                html += '</div>';
                html += '<div style="height:24px;"></div>';
            }

            // Tariffs section
            if (tariffs && tariffs.length > 0) {
                html += `<div class="section-header"><h2>Доступные тарифы</h2></div>`;
                html += '<div class="tariffs-grid">';
                tariffs.forEach(t => {
                    html += `
                    <div class="card tariff-card">
                        <h3>${_esc(t.name_tariff)}</h3>
                        ${t.description ? `<p class="text-sm text-muted" style="margin-bottom:12px;">${_esc(t.description)}</p>` : ''}
                        <div class="tariff-price">${t.amount} ₽ <span>/ ${_periodStr(t.period)}</span></div>
                        <ul class="tariff-features">
                            <li>${t.limit_ip} ${_pluralize(t.limit_ip, 'подключение', 'подключения', 'подключений')}</li>
                            <li>${(t.traffic_limit > 0) ? (t.traffic_limit >= 1024 ? (t.traffic_limit / 1024).toFixed(0) + ' ТБ' : t.traffic_limit.toFixed(0) + ' ГБ') + ' трафика' : 'Безлимитный трафик'}</li>
                            <li>Срок: ${_periodStr(t.period)}</li>
                        </ul>
                        <button class="btn btn-primary btn-buy" data-id="${t.id}" data-name="${_esc(t.name_tariff)}" data-amount="${t.amount}">Купить</button>
                    </div>`;
                });
                html += '</div>';
            }

            if (!keys || keys.length === 0) {
                const trialTariff = tariffs ? tariffs.find(t => t.amount === 0) : null;
                const trialAvailable = user && user.trial === 0;

                let trialBlockHtml = '';
                if (trialAvailable) {
                    const period = trialTariff ? `${trialTariff.period} дней` : '30 дней';
                    const devices = trialTariff ? `${trialTariff.limit_ip} ${trialTariff.limit_ip === 1 ? 'устройство' : 'устройства'}` : '1 устройство';
                    const traffic = trialTariff
                        ? (trialTariff.traffic_limit >= 1024 ? `${(trialTariff.traffic_limit / 1024).toFixed(0)} ТБ` : trialTariff.traffic_limit > 0 ? `${trialTariff.traffic_limit} ГБ` : 'Безлимит')
                        : 'Безлимит';

                    trialBlockHtml = `
                    <div class="trial-block">
                        <div class="trial-block-header">
                            <span class="trial-avail-badge">🎁 Бесплатно</span>
                            <span class="trial-block-name">Пробный период</span>
                        </div>
                        <div class="trial-features">
                            <span class="trial-feat">${_esc(period)}</span>
                            <span class="trial-feat">${_esc(devices)}</span>
                            <span class="trial-feat">${_esc(traffic)}</span>
                        </div>
                        <button class="btn-trial" id="btn-get-trial">Получить пробный ключ</button>
                        <p class="trial-note">Доступно только один раз</p>
                    </div>`;
                }

                const emptyDesc = trialAvailable
                    ? 'Попробуйте VPN бесплатно — или выберите тариф ниже'
                    : 'Выберите тариф ниже, чтобы подключиться к VPN';

                html = `
                <div class="section-header"><h2>Мои ключи</h2></div>
                <div class="empty-card" style="margin-bottom:24px;">
                    <div class="empty-card-icon">🔑</div>
                    <div class="empty-card-title">У вас нет активных ключей</div>
                    <div class="empty-card-desc">${_esc(emptyDesc)}</div>
                    ${trialBlockHtml}
                </div>`;
            }
            container.innerHTML = html;

            // Bind trial key button
            const trialBtn = container.querySelector('#btn-get-trial');
            if (trialBtn) {
                trialBtn.addEventListener('click', async () => {
                    trialBtn.disabled = true;
                    trialBtn.textContent = 'Создаём…';
                    try {
                        await API.post('/keys/trial', {});
                        Toast.success('Пробный ключ создан!');
                        const { Router } = window.Router ? { Router: window.Router } : await import('./router.js');
                        Router.render('dashboard');
                    } catch (err) {
                        Toast.error(err.message || 'Ошибка при создании ключа');
                        trialBtn.disabled = false;
                        trialBtn.textContent = 'Получить пробный ключ';
                    }
                });
            }

            // Bind copy buttons
            container.querySelectorAll('.copy-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    navigator.clipboard.writeText(btn.dataset.key).then(() => {
                        Toast.success('Ключ скопирован');
                    }).catch(() => Toast.error('Не удалось скопировать'));
                });
            });

            // Bind delete buttons
            container.querySelectorAll('.btn-delete-key').forEach(btn => {
                btn.addEventListener('click', async () => {
                    if (!confirm('Удалить этот ключ?')) return;
                    try {
                        await API.delete(`/keys/${btn.dataset.id}`);
                        Toast.success('Ключ удалён');
                        const { Router } = window.Router ? { Router: window.Router } : await import('./router.js');
                        Router.render('dashboard');
                    } catch (err) {
                        Toast.error(err.message);
                    }
                });
            });

            // Bind renew buttons
            container.querySelectorAll('.btn-renew').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const tariffId = parseInt(btn.dataset.tariff);
                    if (!tariffId) {
                        Toast.error('Не удалось определить тариф');
                        return;
                    }
                    const tariff = tariffs.find(t => t.id === tariffId);
                    if (!tariff) {
                        Toast.error('Тариф не найден');
                        return;
                    }
                    if (tariff.amount > 0) {
                        await PaymentModal.open({
                            tariffId: tariffId,
                            tariffName: tariff.name_tariff,
                            amountPerMonth: tariff.amount,
                            renewClientId: btn.dataset.id,
                            onSuccess: async () => {
                                const { Router } = window.Router ? { Router: window.Router } : await import('./router.js');
                                Router.render('dashboard');
                            }
                        });
                    } else {
                        if (!confirm('Продлить ключ на бесплатный тариф?')) return;
                        try {
                            await API.post(`/keys/${btn.dataset.id}/renew`, { tariff_id: tariffId });
                            Toast.success('Ключ продлён!');
                            const { Router } = window.Router ? { Router: window.Router } : await import('./router.js');
                            Router.render('dashboard');
                        } catch (err) {
                            Toast.error(err.message);
                        }
                    }
                });
            });

            // Bind buy buttons
            container.querySelectorAll('.btn-buy').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const tariffId = parseInt(btn.dataset.id);
                    const tariffName = btn.dataset.name;
                    const amount = parseFloat(btn.dataset.amount);

                    await PaymentModal.open({
                        tariffId: tariffId,
                        tariffName: tariffName,
                        amountPerMonth: amount,
                        renewClientId: null,
                        onSuccess: async () => {
                            const { Router } = window.Router ? { Router: window.Router } : await import('./router.js');
                            Router.render('dashboard');
                        }
                    });
                });
            });

        } catch (err) {
            if (!Auth.isLoggedIn()) return;
            container.innerHTML = `<div class="empty-state"><h3>Ошибка загрузки</h3><p>${_esc(err.message)}</p><button class="btn btn-secondary mt-16" onclick="Router.render('dashboard')">Повторить</button></div>`;
        }
    },

    async payments(container) {
        container.innerHTML = `<div class="loading-page page-loading"><div class="spinner"></div></div>`;
        try {
            const payments = await API.get('/payments/');
            let html = `<div class="section-header"><h2>История платежей</h2></div>`;

            if (!payments || payments.length === 0) {
                html += `<div class="card"><div class="empty-state" style="padding:32px 16px">
                    <h3>Платежей пока нет</h3>
                    <p>После оплаты тарифа платежи появятся здесь.</p>
                    <button class="btn btn-secondary mt-16" onclick="Router.navigate('#/dashboard')">Выбрать тариф</button>
                </div></div>`;
            } else {
                const statusLabels = {
                    pending: 'Ожидание',
                    processing: 'Обработка',
                    succeeded: 'Успешно',
                    canceled: 'Отменён',
                    key_creation_failed: 'Ошибка ключа'
                };
                const statusClasses = {
                    succeeded: 'success',
                    canceled: 'error',
                    key_creation_failed: 'error',
                    pending: 'warning',
                    processing: 'warning'
                };
                html += `<div class="card"><div class="table-wrapper"><table class="table">
                    <thead><tr>
                        <th>Дата</th>
                        <th>Сумма</th>
                        <th>Тип</th>
                        <th>Статус</th>
                        <th></th>
                    </tr></thead><tbody>`;
                payments.forEach(p => {
                    const date = p.created_at
                        ? new Date(p.created_at).toLocaleString('ru-RU', {
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                            hour12: false
                        })
                        : '—';
                    const opLabel = (p.payment_type || '').startsWith('web_renew') ? 'Продление' : 'Новый ключ';
                    const stClass = statusClasses[p.status] || '';
                    const stLabel = statusLabels[p.status] || p.status;
                    html += `<tr>
                        <td>${date}</td>
                        <td><strong>${p.amount} ₽</strong></td>
                        <td>${opLabel}</td>
                        <td><span class="badge ${stClass}">${stLabel}</span></td>
                        <td>
                            ${p.status === 'pending' || p.status === 'processing'
                                ? `<button class="btn btn-sm btn-secondary btn-check-status" data-id="${p.payment_id}" style="margin:0">Проверить</button>`
                                : ''}
                        </td>
                    </tr>`;
                });
                html += `</tbody></table></div></div>`;
            }
            container.innerHTML = html;

            container.querySelectorAll('.btn-check-status').forEach(btn => {
                btn.addEventListener('click', async () => {
                    btn.disabled = true;
                    btn.textContent = '...';
                    try {
                        const result = await API.get(`/payments/${btn.dataset.id}/status`);
                        if (result.processed) {
                            Toast.success('Платёж обработан! Ключ обновлён.');
                            const { Router } = window.Router ? { Router: window.Router } : await import('./router.js');
                            Router.render('payments');
                        } else {
                            Toast.info(`Статус: ${result.status}`);
                            btn.textContent = 'Проверить';
                            btn.disabled = false;
                        }
                    } catch (err) {
                        Toast.error(err.message);
                        btn.textContent = 'Проверить';
                        btn.disabled = false;
                    }
                });
            });
        } catch (err) {
            container.innerHTML = `<div class="empty-state"><h3>Ошибка загрузки</h3><p>${_esc(err.message)}</p>
                <button class="btn btn-secondary mt-16" onclick="Router.render('payments')">Повторить</button></div>`;
        }
    },

    async admin(container) {
        container.innerHTML = `<div class="loading-page page-loading"><div class="spinner"></div></div>`;

        try {
            const stats = await API.get('/admin/stats');

            const s = stats || {};
            const mrrGrowth = s.mrr_growth != null
                ? (s.mrr_growth >= 0 ? `+${s.mrr_growth.toLocaleString('ru-RU')} ₽` : `${s.mrr_growth.toLocaleString('ru-RU')} ₽`)
                : '—';

            let html = `
                <div class="section-header">
                    <h2>Админ-панель</h2>
                </div>

                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">MRR (тек.)</div>
                        <div class="metric-value">${(s.mrr_current_month || 0).toLocaleString('ru-RU')} ₽</div>
                        <div class="metric-sub">Рост: ${mrrGrowth}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Плательщики</div>
                        <div class="metric-value">${s.paying_users_current || 0}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Новые за 30д</div>
                        <div class="metric-value">${s.total_new_users_30d || 0}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Истекают 72ч</div>
                        <div class="metric-value" style="color: var(--warning)">${s.total_expiring_72h || 0}</div>
                    </div>
                </div>

                <div class="metrics-grid mt-24">
                    <div class="metric-card">
                        <div class="metric-label">Конверсия в ключи</div>
                        <div class="metric-value">${(s.conversion_to_keys_pct || 0).toFixed(1)}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Конверсия в оплату</div>
                        <div class="metric-value">${(s.conversion_to_paid_pct || 0).toFixed(1)}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Успешные платежи</div>
                        <div class="metric-value">${s.total_succeeded || 0}</div>
                        <div class="metric-sub">${s.succeeded_pct ? s.succeeded_pct.toFixed(1) + '%' : '—'}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">MRR (пред.)</div>
                        <div class="metric-value">${(s.mrr_previous_month || 0).toLocaleString('ru-RU')} ₽</div>
                    </div>
                </div>

                <div class="tabs mt-24">
                    <button class="tab active" data-tab="users">Пользователи</button>
                    <button class="tab" data-tab="keys">Все ключи</button>
                </div>
                <div id="adminTabContent"></div>
            `;
            container.innerHTML = html;

            container.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    container.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');
                    this._loadAdminTab(tab.dataset.tab);
                });
            });

            this._loadAdminTab('users');

        } catch (err) {
            container.innerHTML = `<div class="empty-state"><h3>Ошибка загрузки</h3><p>${_esc(err.message)}</p></div>`;
        }
    },

    async _loadAdminTab(tab) {
        const content = document.getElementById('adminTabContent');
        if (!content) return;
        content.innerHTML = `<div class="loading-page page-loading" style="min-height:200px"><div class="spinner"></div></div>`;

        try {
            if (tab === 'users') {
                const users = await API.get('/admin/users?limit=100&offset=0');
                if (!users || users.length === 0) {
                    content.innerHTML = '<div class="card"><p class="text-muted">Нет пользователей</p></div>';
                    return;
                }
                let html = `<div class="card"><div class="table-wrapper"><table class="table">
                    <thead><tr><th>TG ID</th><th>Имя</th><th>Ключей</th><th>Роль</th><th>Статус</th><th>Действия</th></tr></thead>
                    <tbody>`;
                users.forEach(u => {
                    html += `<tr>
                        <td>${u.tg_id}</td>
                        <td>${_esc(u.username || u.first_name || '—')}</td>
                        <td>${u.keys_count || 0}</td>
                        <td>${u.is_admin ? '<span class="key-badge active">Админ</span>' : ''}</td>
                        <td>${u.is_blocked ? '<span class="key-badge expired">Заблокирован</span>' : '<span class="key-badge active">Активен</span>'}</td>
                        <td>
                            <button class="btn btn-sm ${u.is_blocked ? 'btn-secondary' : 'btn-danger'}" onclick="window.Admin.toggleBlock(${u.tg_id}, ${!u.is_blocked})">
                                ${u.is_blocked ? 'Разблокировать' : 'Блок'}
                            </button>
                            ${!u.is_admin ? `<button class="btn btn-sm btn-secondary" onclick="window.Admin.makeAdmin(${u.tg_id})" style="margin-left:4px">Админ</button>` : ''}
                        </td>
                    </tr>`;
                });
                html += '</tbody></table></div></div>';
                content.innerHTML = html;

            } else if (tab === 'keys') {
                const keys = await API.get('/admin/keys?limit=100&offset=0');
                if (!keys || keys.length === 0) {
                    content.innerHTML = '<div class="card"><p class="text-muted">Нет ключей</p></div>';
                    return;
                }
                const now = Date.now() / 1000;
                let html = `<div class="card">
                    <div style="margin-bottom:16px;">
                        <input type="text" id="keySearch" class="form-input" placeholder="Поиск по email..." style="width:100%">
                    </div>
                    <div class="table-wrapper"><table class="table">
                    <thead><tr><th>Client ID</th><th>Email</th><th>TG ID</th><th>Тариф</th><th>Истекает</th><th>Действия</th></tr></thead>
                    <tbody id="keysTableBody">`;

                const renderTable = (filteredKeys) => {
                    let tbody = '';
                    filteredKeys.forEach(k => {
                        const isExpired = k.expiry_time && new Date(k.expiry_time).getTime() / 1000 < now;
                        const expiryDate = k.expiry_time
                            ? new Date(k.expiry_time).toLocaleDateString('ru-RU')
                            : '—';
                        tbody += `<tr>
                            <td>${_esc(k.client_id || '—')}</td>
                            <td>${_esc(k.email || '—')}</td>
                            <td>${k.tg_id || '—'}</td>
                            <td>${_esc(k.name_tariff || '—')}</td>
                            <td><span class="key-badge ${isExpired ? 'expired' : 'active'}">${expiryDate}</span></td>
                            <td><button class="btn btn-sm btn-danger" onclick="window.Admin.deleteKey('${_esc(k.email)}')">Удалить</button></td>
                        </tr>`;
                    });
                    return tbody;
                };

                html += renderTable(keys);
                html += '</tbody></table></div></div>';
                content.innerHTML = html;

                document.getElementById('keySearch').addEventListener('input', (e) => {
                    const query = e.target.value.toLowerCase();
                    const filtered = keys.filter(k => (k.email || '').toLowerCase().includes(query));
                    document.getElementById('keysTableBody').innerHTML = renderTable(filtered);
                });
            }
        } catch (err) {
            content.innerHTML = `<div class="card"><p class="text-muted">${_esc(err.message)}</p></div>`;
        }
    },
};

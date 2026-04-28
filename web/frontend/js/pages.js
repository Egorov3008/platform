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

export const Pages = {
    _esc,
    _periodStr,
    _pluralize,

    async login(container) {
        let botUsername = '';
        let inviteToken = '';
        try {
            const cfg = await API.get('/auth/config');
            botUsername = cfg.telegram_bot_username || '';
            inviteToken = cfg.invite_token || '';
        } catch (_) {}

        const botLink = inviteToken
            ? `https://t.me/${_esc(botUsername)}?start=${_esc(inviteToken)}`
            : `https://t.me/${_esc(botUsername)}`;

        container.innerHTML = `
        <div class="auth-container">
            <div class="auth-card">
                <h1>Вход</h1>
                <p class="subtitle">Зарегистрируйтесь и получите код в Telegram-боте</p>
                ${botUsername ? `
                <div class="text-center mb-16">
                    <p style="color: var(--text-secondary); margin-bottom: 12px; font-size: 0.9rem;">Нет аккаунта? Перейдите в бот и создайте его</p>
                    <a href="${botLink}" target="_blank" rel="noopener" class="btn btn-primary">Перейти в Telegram бот</a>
                </div>
                ` : ''}
                <form id="loginForm">
                    <div class="form-group">
                        <label for="loginCode">Код из бота</label>
                        <input type="text" id="loginCode" class="form-input" placeholder="ABCD1234" required maxlength="8" autocomplete="off" style="text-transform:uppercase;letter-spacing:0.15em;font-size:1.2rem">
                    </div>
                    <button type="submit" class="btn btn-primary" id="loginBtn">Войти</button>
                </form>
            </div>
        </div>`;

        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('loginBtn');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span>';
            try {
                const code = document.getElementById('loginCode').value.trim().toUpperCase();
                await Auth.login(code);
                Toast.success('Вы успешно вошли!');
                const { Router } = await import('./router.js');
                Router.navigate('#/dashboard');
            } catch (err) {
                Toast.error(err.message);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Войти';
            }
        });
    },

    async dashboard(container) {
        container.innerHTML = `<div class="loading-page page-loading"><div class="spinner"></div></div>`;

        try {
            const [keys, tariffs] = await Promise.all([
                API.get('/keys/').catch(err => {
                    Toast.error('Не удалось загрузить ключи');
                    return [];
                }),
                API.get('/tariffs/').catch(err => {
                    Toast.error('Не удалось загрузить тарифы');
                    return [];
                }),
            ]);

            const userPayload = Auth.getUser();
            const hasTelegram = userPayload && userPayload.tg_id;

            const now = Date.now() / 1000;
            let keysHtml = '';

            if (!keys || keys.length === 0) {
                if (!hasTelegram) {
                    keysHtml = `
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="width:48px;height:48px">
                            <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
                        </svg>
                        <h3>Необходимо привязать Telegram</h3>
                        <p>Для создания VPN ключей нужно привязать Telegram аккаунт</p>
                    </div>`;
                } else {
                    keysHtml = `
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
                        </svg>
                        <h3>У вас пока нет ключей</h3>
                        <p>Создайте первый VPN-ключ, выбрав тариф</p>
                    </div>`;
                }
            } else {
                keysHtml = '<div class="keys-grid">';
                keys.forEach(k => {
                    const expiryDate = k.expiry_time ? new Date(k.expiry_time * 1000) : null;
                    const isExpired = expiryDate && expiryDate.getTime() / 1000 < now;
                    const isExpiring = expiryDate && !isExpired && (expiryDate.getTime() / 1000 - now) < 3 * 24 * 3600;
                    const badgeClass = isExpired ? 'expired' : (isExpiring ? 'expiring' : 'active');
                    const badgeText = isExpired ? 'Истёк' : (isExpiring ? 'Скоро истекает' : 'Активен');
                    const trafficStr = (k.used_traffic !== null && k.total_gb !== null)
                        ? `${(k.used_traffic / 1073741824).toFixed(2)} / ${k.total_gb.toFixed(1)} ГБ`
                        : 'Не ограничен';

                    keysHtml += `
                    <div class="card key-card" data-client-id="${k.client_id}">
                        <div class="key-card-header">
                            <h3>${_esc(k.name_tariff || k.email || 'VPN ключ')}</h3>
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
                            <div class="key-meta-row">
                                <span>Трафик</span>
                                <strong>${trafficStr}</strong>
                            </div>
                        </div>
                        <div class="key-value">
                            <span class="key-value-text">${_esc(k.key || '—')}</span>
                            <button class="copy-btn" data-key="${_esc(k.key)}">Копировать</button>
                        </div>
                        <div class="key-actions">
                            <button class="btn btn-secondary btn-sm btn-renew" data-id="${k.client_id}" data-tariff="${k.tariff_id || ''}">Продлить</button>
                            <button class="btn btn-danger btn-sm btn-delete-key" data-id="${k.client_id}">Удалить</button>
                        </div>
                    </div>`;
                });
                keysHtml += '</div>';
            }

            const tariffOptions = tariffs.map(t =>
                `<option value="${t.id}">${t.name_tariff} — ${t.amount} ₽ / ${_periodStr(t.period)}</option>`
            ).join('');

            container.innerHTML = `
                <div class="section-header">
                    <h2>Мои VPN ключи</h2>
                    ${hasTelegram ? '<button class="btn btn-primary btn-sm" id="createKeyBtn">+ Создать ключ</button>' : ''}
                </div>
                ${keysHtml}
                <div id="tariffOptions" class="hidden">${tariffOptions}</div>
            `;

            const createBtn = document.getElementById('createKeyBtn');
            if (createBtn) {
                createBtn.addEventListener('click', () => {
                    if (!tariffs.length) {
                        Toast.error('Нет доступных тарифов');
                        return;
                    }
                    Modal.open(`
                        <h2>Создать VPN ключ</h2>
                        <form id="createKeyForm">
                            <div class="form-group">
                                <label for="keyTariff">Тариф</label>
                                <select id="keyTariff" class="form-input" required>
                                    ${tariffs.map(t => `<option value="${t.id}">${t.name_tariff} — ${t.amount} ₽ (${_periodStr(t.period)})</option>`).join('')}
                                </select>
                            </div>
                            <button type="submit" class="btn btn-primary" id="createKeySubmitBtn">Создать</button>
                        </form>
                    `);
                    document.getElementById('createKeyForm').addEventListener('submit', async (e) => {
                        e.preventDefault();
                        const btn = document.getElementById('createKeySubmitBtn');
                        btn.disabled = true;
                        btn.innerHTML = '<span class="spinner"></span>';
                        try {
                            const tariffId = parseInt(document.getElementById('keyTariff').value);
                            await API.post('/keys/', { tariff_id: tariffId });
                            Toast.success('Ключ успешно создан!');
                            Modal.close();
                            const { Router } = await import('./router.js');
                            Router.render('dashboard');
                        } catch (err) {
                            Toast.error(err.message);
                        } finally {
                            btn.disabled = false;
                            btn.textContent = 'Создать';
                        }
                    });
                });
            }

            container.querySelectorAll('.copy-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    navigator.clipboard.writeText(btn.dataset.key).then(() => {
                        Toast.success('Ключ скопирован');
                    }).catch(() => Toast.error('Не удалось скопировать'));
                });
            });

            container.querySelectorAll('.btn-delete-key').forEach(btn => {
                btn.addEventListener('click', async () => {
                    if (!confirm('Удалить этот ключ?')) return;
                    try {
                        await API.delete(`/keys/${btn.dataset.id}`);
                        Toast.success('Ключ удалён');
                        const { Router } = await import('./router.js');
                        Router.render('dashboard');
                    } catch (err) {
                        Toast.error(err.message);
                    }
                });
            });

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
                    btn.disabled = true;
                    try {
                        if (tariff.amount > 0) {
                            if (!confirm('Продлить ключ? Будет создан платёж для оплаты.')) {
                                btn.disabled = false;
                                return;
                            }
                            const paymentData = await API.post('/payments/renew', {
                                client_id: btn.dataset.id,
                                tariff_id: tariffId
                            });
                            Toast.success('Платёж создан, переходим к оплате...');
                            window.open(paymentData.payment_url, '_blank');
                        } else {
                            if (!confirm('Продлить ключ на бесплатный тариф?')) {
                                btn.disabled = false;
                                return;
                            }
                            await API.post(`/keys/${btn.dataset.id}/renew`, { tariff_id: tariffId });
                            Toast.success('Ключ продлён!');
                        }
                        const { Router } = await import('./router.js');
                        Router.render('dashboard');
                    } catch (err) {
                        Toast.error(err.message);
                    } finally {
                        btn.disabled = false;
                    }
                });
            });

        } catch (err) {
            if (!Auth.isLoggedIn()) {
                return;
            }
            container.innerHTML = `<div class="empty-state"><h3>Ошибка загрузки</h3><p>${_esc(err.message)}</p><button class="btn btn-secondary mt-16" onclick="Router.render('dashboard')">Повторить</button></div>`;
        }
    },

    async tariffs(container) {
        container.innerHTML = `<div class="loading-page page-loading"><div class="spinner"></div></div>`;

        try {
            const tariffs = await API.get('/tariffs/');

            if (!tariffs || tariffs.length === 0) {
                container.innerHTML = `<div class="empty-state"><h3>Нет доступных тарифов</h3><p>Попробуйте позже</p></div>`;
                return;
            }

            let html = `
                <div class="section-header">
                    <h2>Тарифные планы</h2>
                </div>
                <div class="tariffs-grid">`;

            tariffs.forEach(t => {
                html += `
                <div class="card tariff-card">
                    <h3>${_esc(t.name_tariff)}</h3>
                    ${t.description ? `<p class="text-sm text-muted">${_esc(t.description)}</p>` : ''}
                    <div class="tariff-price">${t.amount} ₽ <span>/ ${_periodStr(t.period)}</span></div>
                    <ul class="tariff-features">
                        <li>${t.limit_ip} ${_pluralize(t.limit_ip, 'подключение', 'подключения', 'подключений')}</li>
                        <li>${t.traffic_limit >= 1024 ? (t.traffic_limit / 1024).toFixed(0) + ' ТБ' : t.traffic_limit.toFixed(0) + ' ГБ'} трафика</li>
                        <li>Срок: ${_periodStr(t.period)}</li>
                    </ul>
                    <button class="btn btn-primary btn-buy" data-id="${t.id}" data-name="${_esc(t.name_tariff)}" data-amount="${t.amount}">Купить</button>
                </div>`;
            });
            html += '</div>';
            container.innerHTML = html;

            container.querySelectorAll('.btn-buy').forEach(btn => {
                btn.addEventListener('click', async () => {
                    if (!Auth.isLoggedIn()) {
                        Toast.info('Для покупки необходимо войти');
                        const { Router } = await import('./router.js');
                        Router.navigate('#/login');
                        return;
                    }
                    const tariffId = parseInt(btn.dataset.id);
                    Modal.open(`
                        <h2>Оплата: ${btn.dataset.name}</h2>
                        <p class="text-muted mb-16">Сумма: <strong>${btn.dataset.amount} ₽</strong></p>
                        <p class="text-sm text-muted mb-16">После оплаты вы будете перенаправлены на страницу оплаты YooKassa.</p>
                        <button class="btn btn-primary" id="payNowBtn">Перейти к оплате</button>
                        <div class="modal-actions">
                            <button class="btn btn-secondary" onclick="Modal.close()">Отмена</button>
                        </div>
                    `);
                    document.getElementById('payNowBtn').addEventListener('click', async () => {
                        const payBtn = document.getElementById('payNowBtn');
                        payBtn.disabled = true;
                        payBtn.innerHTML = '<span class="spinner"></span>';
                        try {
                            const data = await API.post('/payments/create', { tariff_id: tariffId });
                            Toast.success('Платёж создан');
                            Modal.close();
                            window.open(data.payment_url, '_blank');
                        } catch (err) {
                            Toast.error(err.message);
                        } finally {
                            payBtn.disabled = false;
                            payBtn.textContent = 'Перейти к оплате';
                        }
                    });
                });
            });

        } catch (err) {
            container.innerHTML = `<div class="empty-state"><h3>Ошибка загрузки</h3><p>${_esc(err.message)}</p><button class="btn btn-secondary mt-16" onclick="Router.render('tariffs')">Повторить</button></div>`;
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
                    <button class="btn btn-secondary mt-16" onclick="Router.navigate('#/tariffs')">Выбрать тариф</button>
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
                html += `<div class="card"><div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse">
                    <thead><tr style="border-bottom:2px solid var(--border)">
                        <th style="padding:10px;text-align:left">Дата</th>
                        <th style="padding:10px;text-align:left">Сумма</th>
                        <th style="padding:10px;text-align:left">Тип</th>
                        <th style="padding:10px;text-align:left">Статус</th>
                        <th style="padding:10px;text-align:left"></th>
                    </tr></thead><tbody>`;
                payments.forEach(p => {
                    const date = new Date(p.created_at).toLocaleDateString('ru-RU');
                    const opLabel = (p.payment_type || '').startsWith('web_renew') ? 'Продление' : 'Новый ключ';
                    const stClass = statusClasses[p.status] || '';
                    const stLabel = statusLabels[p.status] || p.status;
                    html += `<tr style="border-bottom:1px solid var(--border)">
                        <td style="padding:10px">${date}</td>
                        <td style="padding:10px"><strong>${p.amount} ₽</strong></td>
                        <td style="padding:10px">${opLabel}</td>
                        <td style="padding:10px"><span class="badge ${stClass}">${stLabel}</span></td>
                        <td style="padding:10px">
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
                            const { Router } = await import('./router.js');
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
                let html = `<div class="card"><div class="table-wrapper"><table class="table">
                    <thead><tr><th>Client ID</th><th>TG ID</th><th>Тариф</th><th>Истекает</th><th>Действия</th></tr></thead>
                    <tbody>`;
                keys.forEach(k => {
                    const exp = k.expiry_time ? new Date(k.expiry_time * 1000).toLocaleDateString('ru-RU') : '—';
                    const isExpired = k.expiry_time && k.expiry_time < now;
                    html += `<tr>
                        <td style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${_esc(k.client_id)}</td>
                        <td>${k.tg_id || '—'}</td>
                        <td>${_esc(k.name_tariff || '—')}</td>
                        <td>${exp} ${isExpired ? '<span class="key-badge expired" style="margin-left:4px">Истёк</span>' : ''}</td>
                        <td>
                            <button class="btn btn-sm btn-danger" onclick="window.Admin.deleteKey('${_esc(k.client_id)}')">Удалить</button>
                        </td>
                    </tr>`;
                });
                html += '</tbody></table></div></div>';
                content.innerHTML = html;
            }
        } catch (err) {
            content.innerHTML = `<div class="card"><p style="color:var(--error)">Ошибка: ${_esc(err.message)}</p></div>`;
        }
    },
};

// ============================================================================
// Лендинг «Только для своих» — Telegram без блокировок
// ============================================================================
// Логика:
//   - При загрузке: fetch('/api/v1/landing/state') → определяем экран
//   - При клике «Получить ключ»: fetch('/api/v1/landing/quick-key') → сохраняем куку → active
//   - Обратный отсчёт в реальном времени на экране active
//   - Каждые 5 минут — перезапрос state (на случай, если юзер дошёл до бота)
// ============================================================================

const API_BASE = '/api/v1/landing';
const POLL_INTERVAL_MS = 5 * 60 * 1000;  // 5 минут
const EXPIRING_THRESHOLD_HOURS = 6;

// ----- Утилиты -----

function showScreen(name) {
    document.querySelectorAll('.screen').forEach(el => el.hidden = true);
    const target = document.getElementById(`screen-${name}`);
    if (target) {
        target.hidden = false;
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
        console.warn('screen not found:', name);
        document.getElementById('screen-new').hidden = false;
    }
}

function showToast(message, type = 'info') {
    const el = document.getElementById('toast');
    el.textContent = message;
    el.className = `toast toast-${type}`;
    el.hidden = false;
    setTimeout(() => { el.hidden = true; }, 3000);
}

function formatCountdown(ms) {
    if (ms <= 0) return '00:00:00';
    const h = String(Math.floor(ms / 3600000)).padStart(2, '0');
    const m = String(Math.floor((ms % 3600000) / 60000)).padStart(2, '0');
    const s = String(Math.floor((ms % 60000) / 1000)).padStart(2, '0');
    return `${h}:${m}:${s}`;
}

// ----- State loading -----

async function loadState() {
    try {
        const res = await fetch(`${API_BASE}/state`, {
            method: 'GET',
            credentials: 'include',
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const state = await res.json();
        renderState(state);
    } catch (err) {
        console.error('loadState failed', err);
        showToast('Не удалось загрузить состояние. Попробуйте позже.', 'error');
        showScreen('new');
    }
}

function renderState(state) {
    switch (state.state) {
        case 'new':
            showScreen('new');
            break;

        case 'active':
        case 'expiring':
            showScreen('active');
            document.getElementById('key-text').textContent = state.key_value || '';
            document.getElementById('open-happ').href = state.deep_link_happ || '#';

            const openBot = document.getElementById('open-bot');
            const banner = document.getElementById('already-registered-banner');
            alreadyRegistered = state.already_registered === true;
            if (alreadyRegistered) {
                banner.hidden = false;
                openBot.textContent = '💬 Открыть бота';
                openBot.href = state.bot_url || '#';
            } else {
                banner.hidden = true;
                openBot.innerHTML = '<span>⏳</span> Продлить на неделю бесплатно';
                openBot.href = state.deep_link_bot || '#';
            }

            startCountdown(state.expires_at_ms);
            break;

        case 'expired':
            showScreen('expired');
            break;

        case 'converted':
            showScreen('converted');
            break;

        default:
            console.warn('unknown state:', state.state);
            showScreen('new');
    }
}

// ----- Countdown -----

let countdownTimer = null;
let alreadyRegistered = false;  // управляет скрытием expiring-cta для уже-зарегистрированных

function startCountdown(expiresAtMs) {
    if (countdownTimer) clearInterval(countdownTimer);

    const el = document.getElementById('countdown');
    const expiringCta = document.getElementById('expiring-cta');

    const tick = () => {
        const remaining = Math.max(0, expiresAtMs - Date.now());
        el.textContent = formatCountdown(remaining);

        const isExpiring = remaining > 0 && remaining < EXPIRING_THRESHOLD_HOURS * 3600 * 1000;
        // Уже-зарегистрированным не показываем CTA «продлите бесплатно»
        expiringCta.hidden = alreadyRegistered ? true : !isExpiring;

        if (remaining <= 0) {
            clearInterval(countdownTimer);
            countdownTimer = null;
            // Ключ истёк — перезагрузим state, чтобы перейти на expired-экран
            setTimeout(() => loadState(), 1000);
        }
    };

    tick();
    countdownTimer = setInterval(tick, 1000);
}

// ----- Actions -----

async function generateKey() {
    const btn = document.getElementById('generate');
    const regenerateBtn = document.getElementById('regenerate');
    const target = btn || regenerateBtn;
    if (target) {
        target.disabled = true;
        target.textContent = '⏳ Генерируем...';
    }

    try {
        const res = await fetch(`${API_BASE}/quick-key`, {
            method: 'POST',
            credentials: 'include',
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();
        // Сразу отрисуем active-экран (не ждём state)
        renderState({
            state: 'active',
            key_value: data.key_value,
            expires_at_ms: data.expires_at_ms,
            deep_link_happ: data.deep_link_happ,
            deep_link_bot: data.deep_link_bot,
        });
        showToast('Ключ создан! Импортируйте в Happ 📱', 'success');
    } catch (err) {
        console.error('generateKey failed', err);
        showToast(`Ошибка: ${err.message}`, 'error');
        if (target) {
            target.disabled = false;
            target.textContent = target === btn ? '📲 Получить ключ' : '🔄 Получить ещё один пробный ключ';
        }
    }
}

async function copyKey() {
    const text = document.getElementById('key-text').textContent;
    if (!text || text === 'vless://...') {
        showToast('Сначала получите ключ', 'error');
        return;
    }
    try {
        await navigator.clipboard.writeText(text);
        showToast('Ключ скопирован в буфер обмена ✅', 'success');
    } catch (err) {
        // Fallback для старых браузеров
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showToast('Ключ скопирован ✅', 'success');
        } catch (e) {
            showToast('Не удалось скопировать. Скопируйте вручную.', 'error');
        }
        document.body.removeChild(textarea);
    }
}

// ----- Init -----

document.addEventListener('DOMContentLoaded', () => {
    const gen = document.getElementById('generate');
    const regen = document.getElementById('regenerate');
    const copy = document.getElementById('copy-key');

    if (gen) gen.addEventListener('click', generateKey);
    if (regen) regen.addEventListener('click', generateKey);
    if (copy) copy.addEventListener('click', copyKey);

    // Загружаем состояние сразу
    loadState();

    // И периодически — на случай, если юзер дошёл до бота
    setInterval(loadState, POLL_INTERVAL_MS);
});

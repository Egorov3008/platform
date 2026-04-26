-- Миграция 006: Добавляем таблицу servers и привязываем пользователей к серверам
BEGIN;

-- Таблица серверов 3x-UI
CREATE TABLE IF NOT EXISTS servers (
    id SERIAL PRIMARY KEY,
    cluster_name TEXT NOT NULL,
    server_name TEXT NOT NULL,
    api_url TEXT NOT NULL,
    subscription_url TEXT NOT NULL,
    login TEXT NOT NULL,
    password TEXT NOT NULL,
    UNIQUE (cluster_name, server_name)
);

COMMENT ON TABLE servers IS 'Серверы 3x-UI панелей';
COMMENT ON COLUMN servers.api_url IS 'URL API сервера 3x-UI';
COMMENT ON COLUMN servers.subscription_url IS 'URL для подписки на этом сервере';
COMMENT ON COLUMN servers.login IS 'Логин для панели 3x-UI';
COMMENT ON COLUMN servers.password IS 'Пароль для панели 3x-UI';

-- Таблица для хранения VPN-ключей пользователей
CREATE TABLE IF NOT EXISTS keys (
    id SERIAL PRIMARY KEY,
    tg_id BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    client_id TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    expiry_time BIGINT NOT NULL,
    key TEXT NOT NULL,
    inbound_id INTEGER NOT NULL,
    tariff_id INTEGER,
    total_gb FLOAT DEFAULT 0.0,
    reset_date BIGINT DEFAULT 0,
    notified_10h BOOLEAN DEFAULT FALSE,
    notified_24h BOOLEAN DEFAULT FALSE,
    created_at BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_keys_tg_id ON keys(tg_id);
CREATE INDEX IF NOT EXISTS idx_keys_client_id ON keys(client_id);
CREATE INDEX IF NOT EXISTS idx_keys_email ON keys(email);
CREATE INDEX IF NOT EXISTS idx_keys_expiry ON keys(expiry_time);

-- Добавляем server_id к таблице users если его нет
ALTER TABLE users
ADD COLUMN IF NOT EXISTS server_id INTEGER REFERENCES servers(id) ON DELETE SET NULL;

COMMIT;

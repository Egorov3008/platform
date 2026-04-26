CREATE TABLE IF NOT EXISTS registrate_msg_user (
    tg_id int8 NOT NULL,
    is_msg int8 DEFAULT 0 NULL
);

CREATE TABLE IF NOT EXISTS cache (
    key TEXT NOT NULL PRIMARY KEY,
    value JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS mass_mailing (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    emoji TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
	tg_id int8 NOT NULL,
	username text NULL,
	first_name text NULL,
	last_name text NULL,
	language_code text NULL,
	balance REAL   NOT NULL DEFAULT 0.0,
	is_bot bool DEFAULT false NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
	is_admin bool DEFAULT false NULL,
	trial int4 DEFAULT 0 NOT NULL,
	server_id int4 NULL,
	check_referral bool DEFAULT false NULL,
	is_blocked bool DEFAULT false NULL,
	CONSTRAINT users_pkey PRIMARY KEY (tg_id),
	CONSTRAINT fk_user_server FOREIGN KEY (server_id) REFERENCES public.servers(id) ON DELETE SET NULL
);


CREATE TABLE IF NOT EXISTS payments
(
    id             SERIAL PRIMARY KEY,                                  -- Уникальный идентификатор платежа
    payment_id     TEXT UNIQUE,
    tg_id          BIGINT NOT NULL,                                     -- Уникальный идентификатор пользователя в Telegram
    amount         REAL   NOT NULL DEFAULT 0.0,                         -- Сумма платежа
    status         TEXT                     DEFAULT 'pending',          -- Статус платежа (pending, succeeded, canceled)
    created_at     TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,  -- Дата и время создания платежа
    payment_type   TEXT NOT NULL,
    number_of_months INTEGER NOT NULL DEFAULT 1,
    discount_percent INTEGER NOT NULL DEFAULT 0,                          -- Процент скидки за объём (0 если без скидки)
    FOREIGN KEY (tg_id) REFERENCES users (tg_id)                        -- Внешний ключ, ссылающийся на таблицу users
);

CREATE TABLE IF NOT EXISTS servers
(
    id               SERIAL PRIMARY KEY,                      -- Уникальный идентификатор сервера
    cluster_name     TEXT NOT NULL,                           -- Имя кластера, к которому принадлежит сервер
    server_name      TEXT NOT NULL,                           -- Имя сервера
    api_url          TEXT NOT NULL,                           -- URL API сервера
    subscription_url TEXT NOT NULL,                           -- URL подписки для сервера
    login            TEXT NOT NULL,                           -- login к панели
    password         TEXT NOT NULL,                           -- password панели
    UNIQUE (cluster_name, server_name)                        -- Уникальное сочетание имени кластера и имени сервера
);

CREATE TABLE IF NOT EXISTS inbound (
    server_id INTEGER NOT NULL,  -- Ссылка на сервер
    inbound_id INTEGER NOT NULL, -- Номер подключения НА КОНКРЕТНОМ СЕРВЕРЕ
    name_inbound TEXT,

    -- Уникальность: inbound_id должен быть уникальным в рамках одного сервера
    UNIQUE (server_id, inbound_id),

    -- Жёсткая связь с сервером
    CONSTRAINT fk_inbound_server
        FOREIGN KEY (server_id)
        REFERENCES servers(id)
        ON DELETE RESTRICT  -- Запрещаем удаление сервера с активными подключениями
);

CREATE TABLE IF NOT EXISTS tariff
(
    id SERIAL           PRIMARY KEY,                                           -- Уникальный идентификатор
    name_tariff         TEXT NOT NULL,                                         -- Название тарифа
    amount              REAL   NOT NULL DEFAULT 0.0,                           -- Сумма, которую предоставляет купон
    description         TEXT,                                                  -- Описание тарифа
    limit_ip            INTEGER NOT NULL DEFAULT 0,                            -- Лимит ip по тарифу
    period              INTEGER NOT NULL DEFAULT 30,                           -- Период по тарифу
    traffic_limit       REAL   NOT NULL DEFAULT 0.0                            -- Лимит трафика по тарифу
);

-- Создаем таблицу ключей (keys) с внешним ключом на inbound
CREATE TABLE IF NOT EXISTS keys (
    tg_id BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    client_id TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at BIGINT NOT NULL,
    expiry_time BIGINT NOT NULL,
    key TEXT NOT NULL,
    total_gb REAL NOT NULL DEFAULT 0.0,
    reset_date BIGINT NOT NULL DEFAULT 0,
    inbound_id INTEGER NOT NULL REFERENCES inbound(inbound_id) ON DELETE CASCADE,
    notified_10h BOOLEAN NOT NULL DEFAULT FALSE,
    notified_24h BOOLEAN NOT NULL DEFAULT FALSE,
    tariff_id INTEGER REFERENCES tariff(id) ON DELETE SET NULL,
    tariff_description TEXT,
    name_tariff TEXT,
    amount REAL,
    limit_ip INTEGER,
    period INTEGER,
    used_traffic REAL NOT NULL DEFAULT 0.0,
    server_info JSONB,
    UNIQUE (tg_id, client_id)
);

CREATE TABLE IF NOT EXISTS referrals (
    referral_id SERIAL PRIMARY KEY,
    referrer_id BIGINT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    discount_percent REAL NOT NULL DEFAULT 15.0,
    max_usages INTEGER,
    current_usages INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS referral_links (
    id              SERIAL PRIMARY KEY,
    referrer_tg_id  BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    token           TEXT NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS referral_redemptions (
    id                SERIAL PRIMARY KEY,
    referral_link_id  INTEGER NOT NULL REFERENCES referral_links(id) ON DELETE CASCADE,
    referred_tg_id    BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    redeemed_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS referral_rewards (
    id              SERIAL PRIMARY KEY,
    referrer_tg_id  BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    reward_type     TEXT NOT NULL,
    reward_value    TEXT NOT NULL,
    awarded_at      TIMESTAMPTZ DEFAULT NOW(),
    is_claimed      BOOLEAN DEFAULT FALSE
);


CREATE TABLE IF NOT EXISTS notifications
(
    tg_id                  BIGINT    NOT NULL,                              -- Уникальный идентификатор пользователя в Telegram
    notification_type      TEXT      NOT NULL,                              -- Тип уведомления
    last_notification_time TIMESTAMP NOT NULL DEFAULT NOW(),                -- Время последнего уведомления для пользователя
    PRIMARY KEY (tg_id, notification_type)                                  -- Составной первичный ключ
);



CREATE TABLE IF NOT EXISTS gifts
(
    id              SERIAL PRIMARY KEY NOT NULL,                       -- Уникальный идентификатор подарка
    sender_tg_id    INTEGER NOT NULL,                                   -- Уникальный идентификатор отправителя подарка
    tariff_id       INTEGER NOT NULL,                                   -- Количество месяцев, выбранных для подарка
    token           TEXT NOT NULL,                                      -- Токен подарка
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- Дата и время создания подарка
    recipient_tg_id BIGINT,                                             -- Уникальный идентификатор получателя подарка
    email           TEXT,                                               -- Email для активации подарка
    used_at         TIMESTAMP WITH TIME ZONE,                           -- Дата и время активации подарка
    CONSTRAINT fk_sender FOREIGN KEY (sender_tg_id) REFERENCES users (tg_id),  -- Внешний ключ, ссылающийся на таблицу users
    CONSTRAINT fk_recipient FOREIGN KEY (recipient_tg_id) REFERENCES users (tg_id) -- Внешний ключ, ссылающийся на таблицу users
);


CREATE TABLE IF NOT EXISTS stocks
(
    id                INTEGER PRIMARY KEY NOT NULL,
    discount_type     TEXT      NOT NULL,
    discount_percent  REAL NOT NULL DEFAULT 0.0,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expiry_time        TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active         BOOLEAN NOT NULL DEFAULT FALSE,
    limit_users       INTEGER NOT DEFAULT 0,
    count_users       INTEGER NOT DEFAULT 0
);


CREATE INDEX IF NOT EXISTS idx_referrals_token ON referrals(token);
CREATE INDEX IF NOT EXISTS idx_referrals_active ON referrals(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_referral_links_token ON referral_links(token);
CREATE INDEX IF NOT EXISTS idx_referral_links_referrer ON referral_links(referrer_tg_id);
CREATE INDEX IF NOT EXISTS idx_referral_redemptions_link ON referral_redemptions(referral_link_id);
CREATE INDEX IF NOT EXISTS idx_referral_rewards_referrer ON referral_rewards(referrer_tg_id);

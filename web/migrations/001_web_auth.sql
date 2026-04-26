-- Веб-пользователи: email + пароль, необязательная привязка к tg_id
CREATE TABLE IF NOT EXISTS web_users (
    id          SERIAL PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    tg_id       BIGINT UNIQUE REFERENCES users(tg_id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Одноразовые токены для входа через Telegram
CREATE TABLE IF NOT EXISTS magic_tokens (
    token       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tg_id       BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    expires_at  TIMESTAMPTZ NOT NULL,
    used        BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_magic_tokens_tg_id ON magic_tokens(tg_id);
CREATE INDEX IF NOT EXISTS idx_magic_tokens_expires ON magic_tokens(expires_at);

-- migrations/002_login_codes.sql

CREATE TABLE login_codes (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(8)   UNIQUE NOT NULL,
    tg_id       BIGINT       NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    expires_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW() + INTERVAL '24 hours',
    used        BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_login_codes_tg_id   ON login_codes(tg_id);
CREATE INDEX idx_login_codes_expires ON login_codes(expires_at);

DROP TABLE IF EXISTS magic_tokens;

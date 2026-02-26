-- ============================
-- Telegram Dialog Quality Bot
-- Database initialization
-- ============================

CREATE TABLE IF NOT EXISTS chats (
    chat_id BIGINT PRIMARY KEY,
    chat_title TEXT
);

CREATE TABLE IF NOT EXISTS user_role (
    role_id SERIAL PRIMARY KEY,
    role_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    role_id INTEGER REFERENCES user_role(role_id)
);

CREATE TABLE IF NOT EXISTS messages (
    message_id BIGINT PRIMARY KEY,
    chat_id BIGINT REFERENCES chats(chat_id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    message_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analysis_results (
    analysis_id SERIAL PRIMARY KEY,
    message_id BIGINT UNIQUE REFERENCES messages(message_id) ON DELETE CASCADE,
    sentiment TEXT NOT NULL,
    detected_problem TEXT NOT NULL,
    analysis_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================
-- Optional: default roles
-- ============================

INSERT INTO user_role (role_name)
VALUES ('admin'), ('user')
ON CONFLICT (role_name) DO NOTHING;
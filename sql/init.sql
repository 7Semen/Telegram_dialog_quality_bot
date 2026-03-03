-- ==========================
-- Telegram Dialog Quality Bot
-- Database initialization
-- ==========================

CREATE TABLE IF NOT EXISTS public.chats (
  chat_id   BIGINT PRIMARY KEY,
  chat_name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.user_role (
  role_id   BIGSERIAL PRIMARY KEY,
  role_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS public.users (
  user_id    BIGSERIAL PRIMARY KEY,
  tg_user_id BIGINT NOT NULL UNIQUE,
  username   TEXT NOT NULL,
  role_id    BIGINT NOT NULL REFERENCES public.user_role(role_id)
    ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS public.messages (
  message_id    BIGSERIAL PRIMARY KEY,
  chat_id       BIGINT NOT NULL REFERENCES public.chats(chat_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  user_id       BIGINT NOT NULL REFERENCES public.users(user_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  tg_message_id BIGINT NOT NULL,
  message_text  TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_messages_chat_tgmsg UNIQUE (chat_id, tg_message_id)
);

CREATE TABLE IF NOT EXISTS public.analysis_results (
  analysis_id      BIGSERIAL PRIMARY KEY,
  message_id       BIGINT NOT NULL UNIQUE REFERENCES public.messages(message_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  sentiment        TEXT NOT NULL,
  detected_problem TEXT NOT NULL,
  analysis_date    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Индексы под отчёты/выборки
CREATE INDEX IF NOT EXISTS idx_messages_chat_created
  ON public.messages(chat_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_user_created
  ON public.messages(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analysis_date
  ON public.analysis_results(analysis_date DESC);

CREATE INDEX IF NOT EXISTS idx_analysis_message
  ON public.analysis_results(message_id);

-- Дефолтные роли
INSERT INTO public.user_role(role_name) VALUES ('admin')
ON CONFLICT (role_name) DO NOTHING;

INSERT INTO public.user_role(role_name) VALUES ('viewer')
ON CONFLICT (role_name) DO NOTHING;

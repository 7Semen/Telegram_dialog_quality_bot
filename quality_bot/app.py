import asyncio
import logging

from aiogram import Router
from aiogram.types import ErrorEvent
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ChatType
from dotenv import load_dotenv

from .config import load_config
from .db import create_pool
from .repo import Repo
from .commands import router as commands_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

async def main():
    cfg = load_config()
    pool = await create_pool(cfg.database_url)
    repo = Repo(pool)

    bot = Bot(cfg.bot_token)
    dp = Dispatcher()

    dp["repo"] = repo
    dp["admin_ids"] = cfg.admin_ids

    dp.include_router(commands_router)

    @dp.message(F.text & ~F.text.startswith("/"))
    async def collect_messages(message: Message):
        try:
            # фильтры
            if not message.text:
                return
            if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
                return
            if not message.from_user:
                return

            chat_name = message.chat.title or "Group"
            await repo.ensure_chat(message.chat.id, chat_name)

            username = (
                message.from_user.username
                or message.from_user.full_name
                or f"user_{message.from_user.id}"
            )

            user_id = await repo.ensure_user(
                tg_user_id=message.from_user.id,
                username=username,
                role_name="viewer",
            )

            await repo.add_message(
                chat_id=message.chat.id,
                user_id=user_id,
                text=message.text,
                tg_message_id=message.message_id,
                created_at=message.date,
            )

        except Exception:
            logger.exception("collect_messages failed")
            return

    logging.info("Bot started.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

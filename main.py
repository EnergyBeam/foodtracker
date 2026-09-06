import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from pantry_bot.ai import AIService
from pantry_bot.config import Settings
from pantry_bot.database import Database
from pantry_bot.handlers import build_router
from pantry_bot.repository import PantryRepository


async def main() -> None:
    settings = Settings()
    database = Database(settings.database_url)
    await database.create_schema()

    repository = PantryRepository(database.sessions)
    api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
    ai = AIService(api_key=api_key, model=settings.openai_model)

    bot = Bot(
        token=settings.telegram_bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(repository, ai))

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await database.close()


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())


if __name__ == "__main__":
    run()

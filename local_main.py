import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from pantry_bot.database import Database
from pantry_bot.handlers import build_router
from pantry_bot.ollama_ai import OllamaAIService
from pantry_bot.repository import PantryRepository


async def main() -> None:
    load_dotenv()
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не найден в .env")

    database = Database(os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./pantry.db"))
    await database.create_schema()
    repository = PantryRepository(database.sessions)
    ai = OllamaAIService(
        base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_MODEL", "gemma3:4b"),
    )

    bot = Bot(
        token=telegram_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(repository, ai))  # type: ignore[arg-type]

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await ai.close()
        await database.close()


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())


if __name__ == "__main__":
    run()

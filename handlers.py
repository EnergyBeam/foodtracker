from __future__ import annotations

import html
import logging
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from pantry_bot.ai import AIService, AIUnavailableError
from pantry_bot.keyboards import import_confirmation
from pantry_bot.parsing import parse_consumption, parse_items
from pantry_bot.repository import PantryRepository
from pantry_bot.schemas import ExtractedItem

HELP_TEXT = """<b>Домашние запасы</b>

/add молоко 2 л; яйца 10 шт — добавить продукты
/inventory — показать запасы
/consume яйца 2 — списать продукт
/recipes — предложить блюда

Также можно отправить фотографию чека или продуктов. Перед добавлением бот обязательно покажет распознанные позиции для подтверждения."""


def format_quantity(value: float) -> str:
    return f"{value:g}"


def format_candidates(items: list[ExtractedItem]) -> str:
    lines = []
    for item in items:
        warning = " ⚠️" if item.confidence < 0.65 else ""
        lines.append(
            f"• {html.escape(item.name)} — {format_quantity(item.quantity)} "
            f"{html.escape(item.unit)}{warning}"
        )
    return "\n".join(lines)


def build_router(repository: PantryRepository, ai: AIService) -> Router:
    router = Router()

    @router.message(Command("start", "help"))
    async def start(message: Message) -> None:
        if message.from_user:
            await repository.ensure_user(message.from_user.id)
        await message.answer(HELP_TEXT)

    @router.message(Command("add"))
    async def add(message: Message, command: CommandObject) -> None:
        if message.from_user is None:
            return
        items = parse_items(command.args or "")
        if not items:
            await message.answer("Пример: <code>/add молоко 2 л; яйца 10 шт</code>")
            return
        await repository.add_items(message.from_user.id, items)
        await message.answer(f"Добавлено:\n{format_candidates(items)}")

    @router.message(Command("inventory"))
    async def inventory(message: Message) -> None:
        if message.from_user is None:
            return
        items = await repository.list_items(message.from_user.id)
        if not items:
            await message.answer("Запасы пока пусты. Добавьте их командой /add или фотографией.")
            return
        lines = [
            f"• {html.escape(item.name)} — {format_quantity(item.quantity)} "
            f"{html.escape(item.unit)}"
            for item in items
        ]
        await message.answer("<b>Сейчас в наличии:</b>\n" + "\n".join(lines))

    @router.message(Command("consume"))
    async def consume(message: Message, command: CommandObject) -> None:
        if message.from_user is None:
            return
        parsed = parse_consumption(command.args or "")
        if parsed is None:
            await message.answer("Пример: <code>/consume яйца 2</code>")
            return
        name, quantity = parsed
        remaining = await repository.consume(message.from_user.id, name, quantity)
        if remaining is None:
            await message.answer("Такого продукта нет в запасах.")
        elif remaining == 0:
            await message.answer(f"{html.escape(name.capitalize())} закончились.")
        else:
            await message.answer(f"Осталось: {format_quantity(remaining)}")

    @router.message(Command("recipes"))
    async def recipes(message: Message) -> None:
        if message.from_user is None:
            return
        items = await repository.list_items(message.from_user.id)
        if not items:
            await message.answer("Сначала добавьте продукты.")
            return
        status = await message.answer("Подбираю блюда…")
        try:
            answer = await ai.suggest_recipes(items)
        except AIUnavailableError as error:
            await status.edit_text(f"AI-функции недоступны: {html.escape(str(error))}.")
        except Exception:
            logging.exception("Recipe generation failed")
            await status.edit_text("Не удалось подобрать рецепты. Попробуйте ещё раз позднее.")
        else:
            await status.edit_text(html.escape(answer))

    @router.message(F.photo)
    async def photo(message: Message, bot: Bot) -> None:
        if message.from_user is None or not message.photo:
            return
        status = await message.answer("Распознаю продукты…")
        try:
            telegram_file = await bot.get_file(message.photo[-1].file_id)
            if telegram_file.file_path is None:
                raise ValueError("Telegram did not return a file path")
            buffer = BytesIO()
            await bot.download_file(telegram_file.file_path, destination=buffer)
            analysis = await ai.analyze_photo(buffer.getvalue())
            if not analysis.items:
                await status.edit_text("На фотографии не удалось уверенно найти продукты.")
                return
            pending_id = await repository.create_pending(message.from_user.id, analysis.items)
            kind = "чек" if analysis.kind == "receipt" else "фотографию продуктов"
            await status.edit_text(
                f"Я распознал {kind}:\n{format_candidates(analysis.items)}\n\n"
                "⚠️ Проверьте список перед добавлением.",
                reply_markup=import_confirmation(pending_id),
            )
        except AIUnavailableError as error:
            await status.edit_text(f"AI-функции недоступны: {html.escape(str(error))}.")
        except Exception:
            logging.exception("Photo analysis failed")
            await status.edit_text(
                "Не удалось обработать фотографию. Попробуйте более чёткий снимок."
            )

    @router.callback_query(F.data.startswith("import:"))
    async def pending_import(callback: CallbackQuery) -> None:
        if callback.data is None or callback.message is None:
            return
        _, action, pending_id = callback.data.split(":", maxsplit=2)
        if action == "confirm":
            items = await repository.confirm_pending(callback.from_user.id, pending_id)
            if items is None:
                await callback.answer("Этот список уже обработан", show_alert=True)
                return
            await callback.message.edit_text(f"Добавлено:\n{format_candidates(items)}")
            await callback.answer("Продукты добавлены")
        else:
            cancelled = await repository.cancel_pending(callback.from_user.id, pending_id)
            if not cancelled:
                await callback.answer("Этот список уже обработан", show_alert=True)
                return
            await callback.message.edit_text("Добавление отменено.")
            await callback.answer()

    return router

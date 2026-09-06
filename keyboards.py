from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def import_confirmation(pending_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Добавить", callback_data=f"import:confirm:{pending_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отменить", callback_data=f"import:cancel:{pending_id}"
                ),
            ]
        ]
    )

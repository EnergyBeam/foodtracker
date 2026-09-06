from __future__ import annotations

import base64
import json
import re

from openai import AsyncOpenAI

from pantry_bot.models import PantryItem
from pantry_bot.schemas import PhotoAnalysis

JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class AIUnavailableError(RuntimeError):
    pass


class AIService:
    def __init__(self, api_key: str | None, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.model = model

    def _require_client(self) -> AsyncOpenAI:
        if self.client is None:
            raise AIUnavailableError("OPENAI_API_KEY не настроен")
        return self.client

    async def analyze_photo(self, image: bytes, mime_type: str = "image/jpeg") -> PhotoAnalysis:
        client = self._require_client()
        encoded = base64.b64encode(image).decode("ascii")
        response = await client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Определи, является ли изображение кассовым чеком или "
                                "фотографией продуктов. Извлеки только явно видимые продукты. "
                                "Для сокращений в чеке восстанови обычное русское название. "
                                "Не выдумывай скрытые позиции и не определяй срок годности, если "
                                "он не виден. Верни только JSON вида: "
                                '{"kind":"receipt|products|unknown","items":['
                                '{"name":"молоко","quantity":2,"unit":"шт",'
                                '"confidence":0.9}]}.'
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:{mime_type};base64,{encoded}",
                            "detail": "high",
                        },
                    ],
                }
            ],
        )
        raw = JSON_FENCE_RE.sub("", response.output_text.strip())
        return PhotoAnalysis.model_validate(json.loads(raw))

    async def suggest_recipes(self, items: list[PantryItem]) -> str:
        client = self._require_client()
        inventory = "\n".join(f"- {item.name}: {item.quantity:g} {item.unit}" for item in items)
        response = await client.responses.create(
            model=self.model,
            input=(
                "Ты помощник по домашней кухне. Предложи три простых блюда на русском "
                "из перечисленных запасов. Не считай специи, масло и воду обязательными. "
                "Для каждого блюда укажи время, используемые количества и отдельно недостающие "
                "ингредиенты. Не утверждай, что продукт есть, если его нет в списке. "
                "Ответ должен быть короче 3500 символов и подходить для Telegram.\n\n"
                f"Запасы:\n{inventory}"
            ),
        )
        return response.output_text.strip()

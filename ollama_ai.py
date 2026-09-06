from __future__ import annotations

import base64
import json

import httpx

from pantry_bot.ai import AIUnavailableError
from pantry_bot.models import PantryItem
from pantry_bot.schemas import PhotoAnalysis

PHOTO_PROMPT = """Определи, является ли изображение кассовым чеком или фотографией
продуктов. Извлеки только явно видимые продукты. Для сокращений в чеке восстанови
обычное русское название. Не выдумывай скрытые позиции и не определяй срок годности,
если он не виден. Количество всегда должно быть положительным числом. Используй
обычные единицы: шт, г, кг, мл или л. Верни результат по переданной JSON-схеме."""


class OllamaAIService:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "gemma3:4b",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(180, connect=5),
        )

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def _chat(
        self,
        messages: list[dict[str, object]],
        *,
        response_format: dict[str, object] | None = None,
        temperature: float = 0,
    ) -> str:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if response_format is not None:
            payload["format"] = response_format

        try:
            response = await self.client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
        except httpx.ConnectError as error:
            raise AIUnavailableError(
                "Ollama недоступен. Запустите Ollama и повторите запрос"
            ) from error
        except httpx.TimeoutException as error:
            raise AIUnavailableError(
                "Ollama не успел ответить за 3 минуты. Попробуйте ещё раз"
            ) from error
        except httpx.HTTPStatusError as error:
            detail = self._error_detail(error.response)
            if error.response.status_code == 404:
                detail = f"Модель {self.model} не установлена. Выполните: ollama pull {self.model}"
            raise AIUnavailableError(f"Ошибка Ollama: {detail}") from error

        try:
            return str(response.json()["message"]["content"])
        except (KeyError, TypeError, ValueError) as error:
            raise AIUnavailableError("Ollama вернул ответ неизвестного формата") from error

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            return str(response.json().get("error", response.text))
        except ValueError:
            return response.text or f"HTTP {response.status_code}"

    async def analyze_photo(self, image: bytes, mime_type: str = "image/jpeg") -> PhotoAnalysis:
        del mime_type  # Ollama receives raw base64 and detects the image format itself.
        encoded = base64.b64encode(image).decode("ascii")
        schema = PhotoAnalysis.model_json_schema()
        prompt = PHOTO_PROMPT + "\n\nJSON-схема:\n" + json.dumps(schema, ensure_ascii=False)
        content = await self._chat(
            [{"role": "user", "content": prompt, "images": [encoded]}],
            response_format=schema,
        )
        return PhotoAnalysis.model_validate_json(content)

    async def suggest_recipes(self, items: list[PantryItem]) -> str:
        inventory = "\n".join(f"- {item.name}: {item.quantity:g} {item.unit}" for item in items)
        prompt = (
            "Ты помощник по домашней кухне. Предложи три простых блюда на русском "
            "из перечисленных запасов. Не считай специи, масло и воду обязательными. "
            "Для каждого блюда укажи время, используемые количества и отдельно недостающие "
            "ингредиенты. Не утверждай, что продукт есть, если его нет в списке. "
            "Ответ должен быть короче 3500 символов и подходить для Telegram.\n\n"
            f"Запасы:\n{inventory}"
        )
        return await self._chat(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
        )

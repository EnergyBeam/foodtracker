from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ExtractedItem(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: float = Field(default=1, gt=0)
    unit: str = Field(default="шт", min_length=1, max_length=30)
    confidence: float = Field(default=0.5, ge=0, le=1)

    @field_validator("name", "unit")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return " ".join(value.strip().lower().split())


class PhotoAnalysis(BaseModel):
    kind: Literal["receipt", "products", "unknown"]
    items: list[ExtractedItem]

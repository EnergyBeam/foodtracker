import re

from pantry_bot.schemas import ExtractedItem

NUMBER_RE = re.compile(r"^(\d+(?:[.,]\d+)?)$")


def parse_items(text: str) -> list[ExtractedItem]:
    """Parse `молоко 2 л; яйца 10 шт`; quantity and unit are optional."""
    items: list[ExtractedItem] = []
    for raw_part in text.split(";"):
        tokens = raw_part.strip().split()
        if not tokens:
            continue

        quantity = 1.0
        unit = "шт"
        name_tokens = tokens

        if len(tokens) >= 3 and NUMBER_RE.match(tokens[-2]):
            quantity = float(tokens[-2].replace(",", "."))
            unit = tokens[-1].lower()
            name_tokens = tokens[:-2]
        elif len(tokens) >= 2 and NUMBER_RE.match(tokens[-1]):
            quantity = float(tokens[-1].replace(",", "."))
            name_tokens = tokens[:-1]

        name = " ".join(name_tokens).strip()
        if name and quantity > 0:
            items.append(ExtractedItem(name=name, quantity=quantity, unit=unit, confidence=1))
    return items


def parse_consumption(text: str) -> tuple[str, float] | None:
    tokens = text.strip().split()
    if len(tokens) < 2 or not NUMBER_RE.match(tokens[-1]):
        return None
    name = " ".join(tokens[:-1])
    quantity = float(tokens[-1].replace(",", "."))
    if not name or quantity <= 0:
        return None
    return name, quantity

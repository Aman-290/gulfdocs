import re
import unicodedata
from decimal import Decimal, InvalidOperation

_WHITESPACE = re.compile(r"[\t\r\f\v ]+")
_MULTIPLE_NEWLINES = re.compile(r"\n{3,}")


def normalize_page_text(value: str) -> str:
    """Normalize layout whitespace without transliterating or reshaping Arabic text."""
    value = unicodedata.normalize("NFKC", value)
    lines = [_WHITESPACE.sub(" ", line).strip() for line in value.split("\n")]
    return _MULTIPLE_NEWLINES.sub("\n\n", "\n".join(lines)).strip()


def normalize_currency(value: str) -> str | None:
    collapsed = re.sub(r"[^A-Za-z\u062f\u0625\u0647\u0631\u0645]", "", value).upper()
    aliases = {
        "AED": "AED",
        "DH": "AED",
        "DHS": "AED",
        "دإ": "AED",
        "درهم": "AED",
        "USD": "USD",
        "EUR": "EUR",
    }
    return aliases.get(collapsed)


def parse_decimal(value: str) -> Decimal | None:
    cleaned = value.strip().replace(",", "").replace("٬", "").replace("٫", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if match is None:
        return None
    try:
        return Decimal(match.group(0))
    except (InvalidOperation, ValueError):
        return None

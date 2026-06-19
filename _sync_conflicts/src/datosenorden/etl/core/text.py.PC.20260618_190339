import re
import unicodedata


def clean_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return re.sub(r"\s+", " ", text)


def normalized_key(value: object | None) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")

from html import unescape


def normalize_input_url(url: str) -> str:
    return unescape((url or "").strip())

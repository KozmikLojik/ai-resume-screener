import re


def clean_text(text: str) -> str:
    """Normalize text without removing character sequences inside words."""
    text = (text or "").lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\b(?:rt|cc)\b", " ", text)
    text = re.sub(r"#\S+|@\S+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

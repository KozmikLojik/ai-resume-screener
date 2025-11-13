import re

def clean_text(text: str) -> str:
    """Clean resume/job description text"""
    text = text.lower()
    text = re.sub(r'http\S+\s', ' ', text)  # URLs
    text = re.sub(r'rt|cc', ' ', text)      # RT, CC
    text = re.sub(r'#\S+', ' ', text)       # Hashtags
    text = re.sub(r'@\S+', ' ', text)       # Mentions
    text = re.sub(r'[^\w\s]', ' ', text)    # Punctuation
    text = re.sub(r'\s+', ' ', text)        # Extra spaces
    return text.strip()
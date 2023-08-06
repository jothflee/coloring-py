import re


def make_url_safe(text):
    # Replace all non-alphanumeric characters with a hyphen
    text = re.sub(r'[^a-zA-Z0-9]+', '-', text)
    # Remove any leading or trailing hyphens
    text = text.strip('-')
    # Convert to lowercase
    text = text.lower()
    return text


def make_title_clean(text) -> str:
    # Remove any leading or trailing whitespace
    text = text.strip()
    # Remove any leading or trailing hyphens
    text = text.strip('-')
    text = text.strip('"')
    return text

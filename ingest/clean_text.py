from __future__ import annotations

import re


def basic_clean(text: str) -> str:
    # Remove repeated blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove common header/footer noise patterns
    text = re.sub(r"Page \d+ of \d+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\f", "\n", text)
    # Trim whitespace
    return text.strip()


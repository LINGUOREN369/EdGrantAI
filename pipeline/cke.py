"""
Controlled Keyphrase Extractor (CKE).

Extracts verbatim keyphrases from input text using a stored prompt and an
OpenAI chat model, returning a JSON array of strings.

Usage examples:
  - from pipeline.cke import run_cke
    phrases = run_cke("Grant text here.")

Inputs/Outputs:
  - Prompt: prompts/cke_prompt_nsf_v1.txt (NSF default)
  - Returns: list[str] of extracted phrases

Environment:
  Requires OPENAI_API_KEY (e.g., in a local .env file).
"""

import json
import re
from openai import OpenAI
from pathlib import Path
from .config import settings

# Eagerly initialize the client so missing keys fail at import time
client = OpenAI()

# Path to the stored CKE prompt (from centralized config)
CKE_PROMPT_PATH = settings.CKE_PROMPT_PATH


def load_cke_prompt() -> str:
    """
    Load the Controlled Keyphrase Extractor prompt from disk.
    """
    if not CKE_PROMPT_PATH.exists():
        raise FileNotFoundError(f"CKE prompt not found at {CKE_PROMPT_PATH}")

    with open(CKE_PROMPT_PATH, "r") as f:
        return f.read()


def run_cke(text: str) -> list:
    """
    Execute the Controlled Keyphrase Extractor.

    Steps:
    1. Load prompt from prompts/cke_prompt_nsf_v1.txt
    2. Append grant text to the prompt
    3. Call LLM to extract verbatim phrases
    4. Parse and return extracted JSON array
    """
    base_prompt = load_cke_prompt()
    final_prompt = base_prompt + "\n\nTEXT:\n" + text

    response = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=[{"role": "user", "content": final_prompt}]
    )

    # openai>=1.0 returns typed objects; use attribute access
    raw_output = response.choices[0].message.content

    try:
        text = (raw_output or "").strip()
        # Some models may wrap JSON in triple backticks; strip if present
        if text.startswith("```"):
            # Extract content between first '[' and last ']'
            start = text.find('[')
            end = text.rfind(']')
            if start != -1 and end != -1:
                text = text[start:end+1]

        extracted_phrases = json.loads(text)
        if not isinstance(extracted_phrases, list):
            raise ValueError("CKE output must be a JSON array of strings.")
        return extracted_phrases
    except Exception as e:
        raise ValueError(f"Failed to parse CKE output: {raw_output}\nError: {e}")

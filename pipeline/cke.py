import json
from openai import OpenAI

client = OpenAI()

def run_cke(text: str):
    # Load the CKE prompt from your prompts folder
    with open("prompts/cke_prompt_v1.txt", "r") as f:
        base_prompt = f.read()

    # Combine prompt + text
    final_prompt = base_prompt + "\n\nTEXT:\n" + text

    # Send to LLM
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": final_prompt}
        ]
    )

    raw_output = response.choices[0].message["content"]

    # Parse JSON returned by the LLM
    return json.loads(raw_output)
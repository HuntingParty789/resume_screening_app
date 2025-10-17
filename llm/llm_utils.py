import os
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def call_llm(prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "openai/gpt-oss-120b",  # Example model
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512
    }
    response = requests.post(GROQ_API_URL, json=data, headers=headers)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

def get_llm_client():
    api_key = os.environ.get("AIPIPE_API_KEY")
    base_url = os.environ.get("AIPIPE_BASE_URL", "https://aipipe.org/openrouter/v1") 
    
    if not api_key:
        logger.warning("AIPIPE_API_KEY not set. LLM calls will fail.")
    
    return OpenAI(api_key=api_key, base_url=base_url)

def chat_with_llm(prompt: str, model: str = "gpt-4o-mini", image_url: str = None):
    client = get_llm_client()
    
    messages = [{"role": "user", "content": prompt}]
    
    if image_url:
        # If image support is needed (e.g. for charts)
        messages = [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        return None

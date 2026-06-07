import logging
import requests
from src.config import settings

logger = logging.getLogger(__name__)

class MistralError(Exception):
    pass

class MistralService:
    def __init__(self):
        self.api_key = settings.MISTRAL_API_KEY
        self.api_url = "https://api.mistral.ai/v1/chat/completions"
        self.model = "open-mistral-7b"
        self.timeout = 30.0

    def enhance_transcript(self, transcript: str, instruction: str) -> str:
        """
        Sends the transcript and enhancement instruction to Mistral AI.
        """
        if not self.api_key:
            raise MistralError("Mistral API key (Mistrel_API) is not configured.")

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a professional writing and language assistant. "
                            "You will enhance, format, translate, summarize, or rewrite the provided audio transcription "
                            "based on the user's instructions. Keep your output concise, clean, and focus purely "
                            "on returning the modified transcript or the direct answer to the instruction."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Transcription to enhance:\n\"\"\"\n{transcript}\n\"\"\"\n\nUser's enhancement instruction:\n{instruction}"
                    }
                ],
                "temperature": 0.3
            }

            logger.info("Sending request to Mistral API...")
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=self.timeout)

            if response.status_code != 200:
                logger.error(f"Mistral API error response: {response.status_code} - {response.text}")

            response.raise_for_status()
            result = response.json()
            
            choices = result.get("choices", [])
            if not choices:
                raise MistralError("Mistral returned an empty response.")
            
            enhanced_text = choices[0].get("message", {}).get("content", "")
            return enhanced_text.strip()
            
        except Exception as e:
            logger.error(f"Error during Mistral transcription enhancement: {e}")
            raise MistralError(f"Mistral enhancement failed: {str(e)}")

mistral_service = MistralService()

import logging
import requests
from src.config import settings

logger = logging.getLogger(__name__)

class TranscriptionError(Exception):
    pass

class HuggingFaceTranscriptionService:
    def __init__(self):
        self.api_token = settings.HUGGINGFACE_API_TOKEN
        # Using the new Hugging Face API router
        self.api_url = "https://router.huggingface.co/hf-inference/models/openai/whisper-large-v3"
        self.timeout = 45.0

    def transcribe_audio(self, local_file_path: str) -> str:
        """
        Transcribes the local audio file using Hugging Face Serverless Inference API via requests.
        """
        if not self.api_token:
            raise TranscriptionError("Hugging Face API token is not configured. Voice transcription is disabled.")

        try:
            logger.info(f"Reading file {local_file_path} for transcription...")
            with open(local_file_path, "rb") as f:
                audio_data = f.read()

            headers = {"Authorization": f"Bearer {self.api_token}"}
            
            logger.info("Sending request to Hugging Face Whisper API...")
            response = requests.post(self.api_url, headers=headers, data=audio_data, timeout=self.timeout)
            
            # Check for model loading state (Hugging Face sometimes returns 503 while loading models)
            if response.status_code == 503:
                logger.info("Model is loading, retrying in 5 seconds...")
                import time
                time.sleep(5)
                response = requests.post(self.api_url, headers=headers, data=audio_data, timeout=self.timeout)

            response.raise_for_status()
            result = response.json()
            
            transcript = result.get("text", "")
            if not transcript:
                raise TranscriptionError("Hugging Face returned an empty transcription.")
            
            return transcript.strip()
        except Exception as e:
            logger.error(f"Error during Hugging Face audio transcription: {e}")
            raise TranscriptionError(f"Transcription failed: {str(e)}")

transcription_service = HuggingFaceTranscriptionService()

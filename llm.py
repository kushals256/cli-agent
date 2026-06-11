import os
from openai import OpenAI, APIStatusError
from dotenv import load_dotenv

load_dotenv()

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "meta/llama-3.1-8b-instruct"
PLACEHOLDER_KEY = "your_nvidia_api_key_here"


def validate_api_key():
    """Return an error message if the NVIDIA API key is missing or invalid."""
    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not api_key:
        return (
            "NVIDIA_API_KEY is not set.\n"
            "  1. Copy .env.example to .env\n"
            "  2. Get a free key at https://build.nvidia.com/settings/api-keys\n"
            "  3. Paste the full key (starts with nvapi-) into .env"
        )
    if api_key == PLACEHOLDER_KEY:
        return (
            "NVIDIA_API_KEY is still the placeholder value.\n"
            "  Edit .env and replace 'your_nvidia_api_key_here' with your real key from:\n"
            "  https://build.nvidia.com/settings/api-keys"
        )
    if not api_key.startswith("nvapi-"):
        return (
            "NVIDIA_API_KEY looks invalid (should start with 'nvapi-').\n"
            "  Regenerate your key at https://build.nvidia.com/settings/api-keys"
        )
    return None


class LLM:
    def __init__(self, model=DEFAULT_MODEL):
        self.api_key = os.getenv("NVIDIA_API_KEY", "").strip()
        self.model = model
        self.client = OpenAI(
            base_url=NVIDIA_BASE_URL,
            api_key=self.api_key,
        )

    def chat(self, messages, stream=False):
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                top_p=0.7,
                max_tokens=16384,
                stream=stream,
            )
        except APIStatusError as e:
            if e.status_code == 401:
                raise RuntimeError(
                    "NVIDIA API returned 401 Unauthorized. Your API key is invalid or expired.\n"
                    "  Regenerate it at https://build.nvidia.com/settings/api-keys"
                ) from e
            if e.status_code == 403:
                raise RuntimeError(
                    "NVIDIA API returned 403 Forbidden. Your account may need 'Public API Endpoints' enabled.\n"
                    "  See https://forums.developer.nvidia.com/ or try regenerating your key."
                ) from e
            raise RuntimeError(f"NVIDIA API error ({e.status_code}): {e.message}") from e

        if stream:
            return self._handle_stream(completion)
        return completion

    def _handle_stream(self, stream):
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

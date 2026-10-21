"""OpenAI API client and utilities - Fixed version with comprehensive debugging."""

import logging
from typing import Any, Optional

from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI, PermissionDeniedError

from pain_narratives.core.database import get_database_manager
from pain_narratives.core.provider_errors import ProviderAuthError, ProviderRequestError, ProviderTransientError

from ..config.settings import get_settings

# Set up logger
logger = logging.getLogger(__name__)


class OpenAIClient:
    """OpenAI API client with database integration."""

    def __init__(self, api_key: Optional[str] = None, org_id: Optional[str] = None) -> None:
        """Initialize the OpenAI client."""
        self.settings = get_settings()

        # Use provided credentials or fall back to centralized configuration
        if api_key:
            self._api_key = api_key
            self._org_id = org_id
        else:
            self._api_key = self.settings.openai_api_key
            self._org_id = self.settings.openai_org_id

            if not self._api_key:
                raise ValueError("OpenAI API key not found in configuration")

        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        """Get or create OpenAI client."""
        if self._client is None:
            self._client = OpenAI(api_key=self._api_key, organization=self._org_id, timeout=60, max_retries=2)
        return self._client

    def create_completion(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        logprobs: bool = True,
        top_logprobs: int = 5,
        response_format: Optional[str] = None,  # Accept 'json_object' or None
    ) -> dict[str, Any]:
        """Create a chat completion."""
        model = model or self.settings.model_config.default_model
        temperature = temperature if temperature is not None else self.settings.model_config.default_temperature
        top_p = top_p if top_p is not None else self.settings.model_config.default_top_p
        max_tokens = max_tokens or self.settings.model_config.default_max_tokens
        request_params: dict[str, Any] = {"model": model, "messages": messages}
        if model.startswith("gpt-5"):
            request_params["max_completion_tokens"] = max(max_tokens, 8000)
            if temperature != 0.0:
                request_params["temperature"] = temperature
            if top_p != 1.0:
                request_params["top_p"] = top_p
        else:
            request_params.update(max_tokens=max_tokens, temperature=temperature, top_p=top_p)
        if response_format == "json_object":
            request_params["response_format"] = {"type": "json_object"}
        logger.info("OpenAI request: model=%s messages=%d", model, len(messages))
        try:
            response = self.client.chat.completions.create(**request_params)
        except (AuthenticationError, PermissionDeniedError) as exc:
            raise ProviderAuthError("Provider credentials or permissions require attention") from exc
        except APIConnectionError as exc:
            raise ProviderTransientError("Provider connection failed") from exc
        except APIStatusError as exc:
            if exc.status_code == 429 or exc.status_code >= 500:
                raise ProviderTransientError("Provider temporarily unavailable") from exc
            raise ProviderRequestError("Provider rejected the request") from exc
        result: dict[str, Any] = dict(response.model_dump())
        result["_request"] = request_params
        logger.info("OpenAI response received: model=%s", result.get("model", model))
        return result

    def evaluate_narrative(
        self,
        narrative: str,
        system_prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        use_json_format: bool = False,
    ) -> dict[str, Any]:
        """Evaluate a pain narrative using the specified prompt."""
        logger.info("=== Starting narrative evaluation ===")
        logger.info("Narrative length: %d", len(narrative))
        logger.info("System prompt length: %d", len(system_prompt))
        logger.info("Use JSON format: %s", use_json_format)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"///{narrative}///"},
        ]

        response_format = "json_object" if use_json_format else None

        return self.create_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            response_format=response_format,
        )


def send_to_db_request_response(
    db_conn: Any,
    response: dict[str, Any],
    experiment_id: int,
    model: str,
    prompt_messages: list[dict[str, str]],
    temperature: float,
    top_p: float,
    logprobs: bool = True,
    max_tokens: Optional[int] = None,
    top_logprobs: int = 5,
    schema: str = "pain_narratives",
) -> None:
    """Persist request/response back to RequestResponse table using ORM to get default timestamp."""
    logger.info("Sending to DB via ORM, experiment_id: %d", experiment_id)
    # Construct minimal JSON objects
    request_json = {
        "model": model,
        "messages": prompt_messages,
        "temperature": temperature,
        "top_p": top_p,
    }
    response_json = dict(response)
    # Persist via DatabaseManager
    db_manager = get_database_manager()
    db_manager.save_request_response(experiment_id, request_json, response_json)
    logger.info("Successfully saved RequestResponse record.")


def remove_unicode_chars(data: dict[str, Any]) -> dict[str, Any]:
    """Remove unicode characters from dictionary for ASCII compatibility."""
    new_dict: dict[str, Any] = {}
    for key, value in data.items():
        # Ensure the key is a string, then encode to ASCII ignoring errors
        ascii_key: str = str(key).encode("ascii", "ignore").decode("ascii")

        ascii_value: Any
        if isinstance(value, str):
            # For string values, remove non-ASCII characters
            ascii_value = value.encode("ascii", "ignore").decode("ascii")
        elif isinstance(value, dict):
            # If the value is a dictionary, recursively clean it
            ascii_value = remove_unicode_chars(value)
        elif isinstance(value, list):
            # Handle lists by processing each item
            ascii_value = [
                (
                    remove_unicode_chars(item)
                    if isinstance(item, dict)
                    else str(item).encode("ascii", "ignore").decode("ascii") if isinstance(item, str) else item
                )
                for item in value
            ]
        else:
            # For other types, keep the value as is
            ascii_value = value

        new_dict[ascii_key] = ascii_value

    return new_dict


# Global OpenAI client instance
_openai_client: Optional[OpenAIClient] = None


def get_openai_client() -> OpenAIClient:
    """Get the global OpenAI client instance."""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAIClient()
    return _openai_client

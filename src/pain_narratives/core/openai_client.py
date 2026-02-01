"""OpenAI API client and utilities - Fixed version with comprehensive debugging."""

import logging
from typing import Any, Optional

from openai import OpenAI

from pain_narratives.core.database import get_database_manager

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

        logger.info(
            "OpenAI Client initialized with API key: %s",
            "***" + self._api_key[-4:] if self._api_key and len(self._api_key) > 4 else "NOT SET",
        )
        logger.info("Organization ID: %s", self._org_id or "NOT SET")

        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        """Get or create OpenAI client."""
        if self._client is None:
            logger.info("Creating new OpenAI client instance...")
            try:
                self._client = OpenAI(api_key=self._api_key, organization=self._org_id, timeout=60)
                logger.info("OpenAI client created successfully")
            except Exception as e:
                logger.error("Failed to create OpenAI client: %s", str(e), exc_info=True)
                raise
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
        logger.info("=== OpenAI API Request Starting ===")

        # Resolve parameters
        model = model or self.settings.model_config.default_model
        temperature = temperature if temperature is not None else self.settings.model_config.default_temperature
        top_p = top_p if top_p is not None else self.settings.model_config.default_top_p
        max_tokens = max_tokens or self.settings.model_config.default_max_tokens

        logger.info("Request parameters:")
        logger.info("  Model: %s", model)
        logger.info("  Temperature: %s", temperature)
        logger.info("  Top P: %s", top_p)
        logger.info("  Max tokens: %s", max_tokens)
        logger.info("  Response format: %s", response_format)
        logger.info("  Messages count: %s", len(messages))

        # Log message details (truncated for security)
        for i, msg in enumerate(messages):
            logger.info(
                "  Message %d - Role: %s, Content length: %d",
                i,
                msg.get("role", "unknown"),
                len(msg.get("content", "")),
            )
            # Log first 200 chars of each message for debugging
            content_preview = msg.get("content", "")[:200]
            logger.info(
                "  Message %d preview: %s%s",
                i,
                content_preview,
                "..." if len(msg.get("content", "")) > 200 else "",
            )

        try:
            logger.info("Making OpenAI API call...")

            # Prepare request parameters
            request_params = {
                "model": model,
                "messages": messages,
            }
            
            # Handle GPT-5 model specific parameters
            if model.startswith("gpt-5"):
                # GPT-5 models use max_completion_tokens and need higher token limits
                # Ensure minimum token limit for GPT-5 models (reasoning tokens + output)
                gpt5_max_tokens = max(max_tokens, 8000)  # GPT-5 needs high limits for reasoning + output
                request_params["max_completion_tokens"] = gpt5_max_tokens
                
                # GPT-5 models have limited parameter support
                # Only set temperature if it's not 0.0 (GPT-5 models work best with default temperature)
                if temperature != 0.0:
                    request_params["temperature"] = temperature
                # Only set top_p if it's not the default
                if top_p != 1.0:
                    request_params["top_p"] = top_p
                    
                logger.info("  GPT-5 adjusted max_completion_tokens: %s", gpt5_max_tokens)
            else:
                # Older models use max_tokens and support all parameters
                request_params["max_tokens"] = max_tokens
                request_params["temperature"] = temperature
                request_params["top_p"] = top_p

            # Add response_format only if specified and not None
            if response_format == "json_object":
                request_params["response_format"] = {"type": "json_object"}
                logger.info("  Added JSON response format")

            logger.info("Final request parameters: %s", list(request_params.keys()))

            response = self.client.chat.completions.create(**request_params)

            logger.info("OpenAI API call successful!")
            logger.info("Response type: %s", type(response))

            if hasattr(response, "model_dump"):
                result = response.model_dump()
                logger.info("Response model_dump successful, type: %s", type(result))
                if isinstance(result, dict):
                    logger.info("Response keys: %s", list(result.keys()))
                    if "choices" in result and result["choices"]:
                        choice = result["choices"][0]
                        logger.info("Choice keys: %s", list(choice.keys()))
                        logger.info("Finish reason: %s", choice.get("finish_reason"))
                        if "message" in choice:
                            message = choice["message"]
                            logger.info("Message keys: %s", list(message.keys()))
                            
                            # GPT-5 models may return content in different fields
                            content = None
                            if "content" in message and message["content"]:
                                content = message["content"]
                            elif "refusal" in message and message["refusal"]:
                                logger.warning("Model returned refusal: %s", message["refusal"])
                                content = message["refusal"]
                            
                            # For debugging: log all message fields
                            for key, value in message.items():
                                if value:
                                    logger.info("Message field '%s' has value (length: %d)", key, len(str(value)))
                                else:
                                    logger.info("Message field '%s' is empty or None", key)
                            
                            if content:
                                content_length = len(content)
                                logger.info("Response content length: %d", content_length)
                                content_preview = content[:200]
                                logger.info(
                                    "Response content preview: %s%s",
                                    content_preview,
                                    "..." if content_length > 200 else "",
                                )
                            else:
                                logger.warning("No content found in message! Full message: %s", message)
                    return result
                else:
                    logger.warning("Response model_dump returned non-dict: %s", type(result))
                    return {"response": result}
            else:
                logger.warning("Response has no model_dump method")
                return {"response": response}

        except Exception as e:
            logger.error("OpenAI API call failed: %s", str(e), exc_info=True)
            logger.error("Exception type: %s", type(e).__name__)

            # Log additional details for common errors
            if hasattr(e, "response"):
                logger.error("API Error response: %s", getattr(e, "response", None))
            if hasattr(e, "status_code"):
                logger.error("API Error status code: %s", getattr(e, "status_code", None))
            if hasattr(e, "body"):
                logger.error("API Error body: %s", getattr(e, "body", None))

            raise

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
    response_json = remove_unicode_chars(response)
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

"""
Translation service for multilingual e        # Collect content that needs translation
        content_to_translate = {}

        # Always include reasoning if present
        if "reasoning" in evaluation_result:
            content_to_translate["reasoning"] = evaluation_result["reasoning"]

        # Handle general explanation field
        if "explanation" in evaluation_result:
            content_to_translate["explanation"] = evaluation_result["explanation"]

        # Handle different possible explanation structures
        if "explanations" in evaluation_result:
            content_to_translate["explanations"] = evaluation_result["explanations"]
        elif "dimension_explanations" in evaluation_result:
            content_to_translate["dimension_explanations"] = evaluation_result["dimension_explanations"]

        # Handle fields ending with _explanation (like severity_explanation, disability_explanation)
        for key, value in evaluation_result.items():
            if key.endswith("_explanation") and isinstance(value, str):
                content_to_translate[key] = valuesults.
"""

import json
import logging
from typing import Any, Dict, Optional

from pain_narratives.core.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class TranslationService:
    """Service for translating evaluation results to different languages."""

    def __init__(self, openai_client: Optional[OpenAIClient] = None):
        """Initialize translation service with OpenAI client."""
        self.openai_client = openai_client or OpenAIClient()

        # Load translation-specific configuration
        from pain_narratives.config.settings import get_settings

        settings = get_settings()
        self.model_config = settings.model_config

    def translate_evaluation_result(
        self, evaluation_result: Dict[str, Any], target_language: str = "es"
    ) -> Dict[str, Any]:
        """
        Translate evaluation result explanations to target language.

        Args:
            evaluation_result: The evaluation result dictionary from the "en" key
            target_language: Target language code (e.g., "es" for Spanish)

        Returns:
            Translated evaluation result dictionary
        """
        if not evaluation_result:
            return evaluation_result

        # Extract content that needs translation
        content_to_translate = {}

        # Handle reasoning fields (both formats)
        if "reasoning" in evaluation_result:
            content_to_translate["reasoning"] = evaluation_result["reasoning"]
        if "model_reasoning" in evaluation_result:
            content_to_translate["model_reasoning"] = evaluation_result["model_reasoning"]

        # Handle general explanation field
        if "explanation" in evaluation_result:
            content_to_translate["explanation"] = evaluation_result["explanation"]

        # Handle different possible explanation structures
        if "explanations" in evaluation_result:
            content_to_translate["explanations"] = evaluation_result["explanations"]
        elif "dimension_explanations" in evaluation_result:
            content_to_translate["dimension_explanations"] = evaluation_result["dimension_explanations"]

        # Handle all fields ending with _explanation (assessment result fields)
        for key, value in evaluation_result.items():
            if key.endswith("_explanation") and isinstance(value, str):
                content_to_translate[key] = value

        if not content_to_translate:
            logger.warning("No translatable content found in evaluation result")
            return evaluation_result

        # Create translation prompt
        language_names = {"es": "Spanish", "en": "English", "fr": "French", "de": "German", "it": "Italian"}

        target_language_name = language_names.get(target_language, target_language)

        translation_prompt = self._create_translation_prompt(content_to_translate, target_language_name)

        try:
            # Call OpenAI for translation using configured translation model
            response = self.openai_client.create_completion(
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a professional medical translator. Translate the provided text accurately to {target_language_name}, maintaining medical terminology precision and context. Respond in the same structured JSON format.",
                    },
                    {"role": "user", "content": translation_prompt},
                ],
                model=self.model_config.translation_model,
                temperature=self.model_config.translation_temperature,
                max_tokens=self.model_config.translation_max_tokens,
                response_format="json_object",
            )

            translated_content = response["choices"][0]["message"]["content"]
            translated_data = json.loads(translated_content)

            # Debug: Log what was actually returned by the translation model
            logger.info(f"Translation model returned keys: {list(translated_data.keys())}")
            logger.info(f"Expected keys: {list(content_to_translate.keys())}")
            
            # Create translated result by copying original and updating translated fields
            translated_result = evaluation_result.copy()

            # Update all translated fields
            for key, value in translated_data.items():
                if key in content_to_translate:
                    translated_result[key] = value
                    logger.info(f"Updated field '{key}' with translation")
                    
            # Check for missing translations and warn
            missing_keys = set(content_to_translate.keys()) - set(translated_data.keys())
            if missing_keys:
                logger.warning(f"Translation model did not return translations for: {missing_keys}")

            logger.info(f"Successfully translated evaluation result to {target_language}")
            return translated_result

        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            # Return original result if translation fails
            return evaluation_result

    def _create_translation_prompt(self, content: Dict[str, Any], target_language: str) -> str:
        """Create a structured prompt for translating evaluation content."""
        prompt = f"""
Please translate the following medical evaluation content from English to {target_language}.
Maintain the same JSON structure and keys. Only translate the text values, not the keys.
Preserve medical terminology accuracy and context.

Content to translate:
{json.dumps(content, indent=2)}

Return the translated explanations in the same JSON format, with the same keys but translated values.
"""
        return prompt

    def get_available_translation(self, result_json: Dict[str, Any], preferred_language: str = "en") -> Dict[str, Any]:
        """
        Get evaluation result in preferred language, falling back to English.

        Args:
            result_json: Complete multilingual result JSON from database
            preferred_language: Preferred language code

        Returns:
            Evaluation result in requested language or English fallback
        """
        if not result_json or not isinstance(result_json, dict):
            return {}

        # Try preferred language first
        if preferred_language in result_json:
            return result_json[preferred_language]

        # Fallback to English
        if "en" in result_json:
            return result_json["en"]

        # If neither exists, return empty dict
        logger.warning(f"No translation found for language {preferred_language} or English fallback")
        return {}

    def add_translation_to_result(self, result_json: Dict[str, Any], target_language: str) -> Dict[str, Any]:
        """
        Add a new translation to existing multilingual result JSON.

        Args:
            result_json: Existing multilingual result JSON
            target_language: Target language to add

        Returns:
            Updated result JSON with new translation
        """
        if not result_json or target_language in result_json:
            return result_json

        # Get English version for translation
        english_result = result_json.get("en", {})
        if not english_result:
            logger.warning("No English version found for translation")
            return result_json

        # Translate and add to result
        translated_result = self.translate_evaluation_result(english_result, target_language)
        result_json[target_language] = translated_result

        logger.info(f"Added {target_language} translation to result")
        return result_json

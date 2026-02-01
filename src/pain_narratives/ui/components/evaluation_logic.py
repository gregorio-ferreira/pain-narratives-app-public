"""Evaluation logic for pain narratives, extracted from the main Streamlit app."""

import json
import logging
import re
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List

import streamlit as st
from pydantic import BaseModel

# Set up logger
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pain_narratives.core.openai_client import OpenAIClient


class EvaluationInput(BaseModel):
    narrative: str
    prompt: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 512
    # Add more fields as needed


class NarrativeEvaluator:
    """Handles narrative evaluation and consistency testing."""

    @staticmethod
    def evaluate_single_narrative(
        narrative_text: str,
        prompt: str,
        openai_client: "OpenAIClient",
        config: Dict[str, Any],
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Evaluate a single narrative using the OpenAI client."""
        logger.info("=== Evaluation Starting ===")
        logger.info("Narrative length: %d", len(narrative_text))
        logger.info("Prompt length: %d", len(prompt))
        logger.info("Config: %s", config)
        logger.info("Max tokens: %d", max_tokens)

        try:
            logger.info("Formatting prompt with narrative...")
            formatted_prompt = prompt.format(narrative=narrative_text)
            logger.info("Formatted prompt length: %d", len(formatted_prompt))
            logger.info("Formatted prompt preview: %s...", formatted_prompt[:200])

            logger.info("Calling OpenAI client create_completion...")
            response = openai_client.create_completion(
                messages=[{"role": "user", "content": formatted_prompt}],
                model=config["model"],
                temperature=config["temperature"],
                max_tokens=max_tokens,
            )
            logger.info("OpenAI client returned response type: %s", type(response))
            logger.info(
                "OpenAI response keys: %s",
                list(response.keys()) if isinstance(response, dict) else "Not a dict",
            )

            # Store raw OpenAI response in session state for DB saving
            logger.debug(f"About to store OpenAI response in session state: {type(response)}")
            st.session_state.last_openai_response = response
            logger.debug(f"OpenAI response stored. Session state keys: {list(st.session_state.keys())}")
            logger.debug(f"last_openai_response in session state: {'last_openai_response' in st.session_state}")

            # Defensive: ensure this is always set, even if rerun or error
            if "last_openai_response" not in st.session_state or st.session_state.last_openai_response is None:
                logger.debug("Re-setting last_openai_response as it was None or missing")
                st.session_state.last_openai_response = response

            logger.info("Extracting content from OpenAI response...")
            content = response["choices"][0]["message"]["content"]
            logger.info("Content extracted, length: %d", len(content))
            logger.info("Content preview: %s...", content[:200])

            # Parse OpenAI response using centralized method
            result = NarrativeEvaluator._parse_openai_response(content)

            final_result = {
                "narrative": narrative_text,
                "result": result,
                "model": config["model"],
                "temperature": config["temperature"],
                "timestamp": datetime.now().isoformat(),
                "prompt_used": formatted_prompt,
            }
            logger.info("Evaluation completed successfully!")
            logger.info("Final result keys: %s", list(final_result.keys()))
            return final_result

        except Exception as e:
            logger.error("Evaluation failed with exception: %s", str(e), exc_info=True)
            logger.error("Exception type: %s", type(e).__name__)

            fallback_result = {
                "narrative": narrative_text,
                "result": {
                    "error": f"Evaluation failed: {str(e)}",
                    "pain_intensity": 0,
                    "functional_impact": 0,
                    "emotional_impact": 0,
                    "descriptive_quality": 0,
                    "reasoning": f"Error during evaluation: {str(e)}",
                },
                "model": config["model"],
                "temperature": config["temperature"],
                "timestamp": datetime.now().isoformat(),
            }
            logger.info("Returning fallback result due to exception")
            return fallback_result

    @staticmethod
    def _parse_openai_response(content: str) -> Dict[str, Any]:
        """Parse and clean OpenAI response content to extract JSON."""
        # Clean the content and try to parse JSON
        content = content.strip()

        # Try to extract JSON if it's wrapped in markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        # Additional cleaning for common JSON formatting issues
        # Remove any leading/trailing whitespace or newlines
        content = content.replace("\n", "").replace("\r", "")

        # Try to find JSON content if it's embedded in text
        if "{" in content and "}" in content:
            start = content.find("{")
            end = content.rfind("}") + 1
            content = content[start:end]

        logger.info("Attempting to parse JSON from cleaned content...")
        logger.info("Cleaned content: %s", content[:500])

        try:
            result = json.loads(content)
            logger.info("JSON parsing successful!")
            logger.info(
                "Parsed result keys: %s",
                list(result.keys()) if isinstance(result, dict) else "Not a dict",
            )
            return result
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing failed: %s", str(e))
            # If JSON parsing fails, try to create a valid structure from the content
            st.warning("JSON parsing failed. Attempting to extract values from raw content.")
            result = NarrativeEvaluator._extract_fallback_values(content)
            result["error"] = f"JSON parsing failed: {str(e)}"
            result["raw_content"] = content[:500]  # Limit raw content length
            return result

    @staticmethod
    def _extract_fallback_values(content: str) -> Dict[str, Any]:
        """Extract values from malformed JSON content as a fallback."""
        result = {
            "pain_intensity": 0,
            "functional_impact": 0,
            "emotional_impact": 0,
            "descriptive_quality": 0,
            "reasoning": "Unable to parse structured response",
        }

        # Try to extract numeric values for known fields
        for field in [
            "pain_intensity",
            "functional_impact",
            "emotional_impact",
            "descriptive_quality",
        ]:
            # Look for patterns like "field_name": 5 or "field_name": "5"
            patterns = [
                rf'"{field}":\s*(\d+)',
                rf'"{field}":\s*"(\d+)"',
                rf"{field}.*?(\d+)",
            ]

            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    try:
                        result[field] = int(match.group(1))
                        break
                    except (ValueError, IndexError):
                        continue

        # Try to extract reasoning
        reasoning_patterns = [
            r'"reasoning":\s*"([^"]+)"',
            r'"reasoning":\s*\'([^\']+)\'',
            r"reasoning[:\s]+([^,}]+)",
        ]

        for pattern in reasoning_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                result["reasoning"] = match.group(1).strip()
                break

        return result

    @staticmethod
    def evaluate_multiple_narratives(
        narrative_text: str,
        prompt: str,
        openai_client: "OpenAIClient",
        config: Dict[str, Any],
        max_tokens: int,
        num_evaluations: int,
    ) -> List[Dict[str, Any]]:
        """Evaluate a narrative multiple times for consistency testing."""
        evaluations: List[Dict[str, Any]] = []

        for i in range(num_evaluations):
            try:
                formatted_prompt = prompt.format(narrative=narrative_text)
                response = openai_client.create_completion(
                    messages=[{"role": "user", "content": formatted_prompt}],
                    model=config["model"],
                    temperature=config["temperature"],
                    max_tokens=max_tokens,
                )
                content = response["choices"][0]["message"]["content"]

                # Parse OpenAI response using centralized method
                result = NarrativeEvaluator._parse_openai_response(content)

                evaluations.append(result)
                time.sleep(0.5)  # To avoid rate limits

            except Exception as e:
                evaluations.append(
                    {
                        "error": f"Evaluation {i + 1} failed: {str(e)}",
                        "pain_intensity": 0,
                        "functional_impact": 0,
                        "emotional_impact": 0,
                        "descriptive_quality": 0,
                        "reasoning": f"Error during evaluation: {str(e)}",
                    }
                )

        return evaluations


def evaluate_narrative(input_data: EvaluationInput, openai_client: "OpenAIClient") -> Dict[str, Any]:
    """
    Evaluate a single narrative using OpenAIClient and return the result as a dict.
    """
    response = openai_client.create_completion(
        messages=[
            {"role": "system", "content": input_data.prompt},
            {"role": "user", "content": input_data.narrative},
        ],
        model=input_data.model,
        temperature=input_data.temperature,
        max_tokens=input_data.max_tokens,
    )
    result: Dict[str, Any] = {
        "reasoning": response["choices"][0]["message"]["content"],
        # Add more fields as needed
    }
    return result


def batch_evaluate_narratives(inputs: List[EvaluationInput], openai_client: "OpenAIClient") -> List[Dict[str, Any]]:
    """
    Evaluate a batch of narratives and return a list of results.
    """
    results: List[Dict[str, Any]] = []
    for input_data in inputs:
        result = evaluate_narrative(input_data, openai_client)
        results.append(result)
    return results

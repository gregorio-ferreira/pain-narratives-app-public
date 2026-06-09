"""
Streamlit-free questionnaire runners for batch processing.

This module provides pure functions for running PCS, BPI-IS, and TSK-11SV
questionnaires without any Streamlit dependencies. It can be used by both
the Streamlit UI (via wrappers) and the batch processing CLI.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple

from pain_narratives.config.prompts import get_questionnaire_prompt
from pain_narratives.core.bedrock_client import BedrockAuthError

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    """Minimal interface satisfied by both `OpenAIClient` and `BedrockOpenAIAdapter`.

    Defined as a Protocol so callers don't pull a concrete dependency on either
    provider's module. Both clients return an OpenAI Chat Completions shaped dict.
    """

    def create_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: Optional[float] = ...,
        max_tokens: int = ...,
        response_format: Optional[str] = ...,
        **kwargs: Any,
    ) -> Dict[str, Any]: ...


@dataclass
class QuestionnaireResult:
    """Container for questionnaire evaluation results."""

    questionnaire_type: str
    success: bool
    data: Dict[str, Any]
    raw_response: Dict[str, Any]
    messages: List[Dict[str, str]]
    error: Optional[str] = None

    @property
    def scores(self) -> Dict[str, Any]:
        """Get scores (PCS format)."""
        return self.data.get("scores", {})

    @property
    def responses(self) -> List[Dict[str, Any]]:
        """Get responses (BPI-IS/TSK format)."""
        return self.data.get("responses", [])

    @property
    def model_reasoning(self) -> str:
        """Get model reasoning."""
        return self.data.get("model_reasoning", "")

    @property
    def persona(self) -> Dict[str, str]:
        """Get persona information."""
        return self.data.get("persona", {})


def extract_json_from_text(text: str) -> str:
    """Extract JSON from text that may contain markdown code blocks."""
    text = text.strip()

    # Remove markdown code blocks
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    # Try to find JSON object boundaries
    start_idx = text.find("{")
    end_idx = text.rfind("}")

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        text = text[start_idx : end_idx + 1]

    return text.strip()


def repair_json_brackets(text: str) -> str:
    """Fix mismatched closing brackets that some LLMs produce.

    Observed failure mode: Claude Sonnet 4.5 with thinking sometimes closes an
    array (``[``) with ``}`` instead of ``]`` (and vice versa). This walks the
    text character by character, tracks the open-bracket stack, and rewrites a
    mismatched close to whatever the stack actually wants. String literals
    (with backslash escapes) are passed through verbatim so we never touch
    brackets inside quoted text.
    """
    out: list[str] = []
    stack: list[str] = []
    i = 0
    in_string = False
    while i < len(text):
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < len(text):
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch in "[{":
            stack.append(ch)
            out.append(ch)
        elif ch in "]}":
            if stack:
                open_ch = stack.pop()
                want = "]" if open_ch == "[" else "}"
                out.append(want)  # rewrite if mismatched, else identity
            else:
                # Closing bracket without a matching open; keep as-is. The
                # subsequent json.loads will fail loudly which is the right
                # behaviour for genuinely broken output.
                out.append(ch)
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def loads_with_repair(text: str) -> Any:
    """Parse JSON, retrying once with bracket repair if the first parse fails."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = repair_json_brackets(text)
        return json.loads(repaired)


def parse_questionnaire_response(content: str, questionnaire_type: str) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """
    Parse questionnaire response JSON.

    Args:
        content: Raw response content from API
        questionnaire_type: One of 'PCS', 'BPI-IS', 'TSK-11SV'

    Returns:
        Tuple of (success, data_dict, error_message)
    """
    if not content:
        return False, {}, "Empty response from API"

    cleaned_content = extract_json_from_text(content)
    logger.debug(f"Cleaned {questionnaire_type} JSON content: {cleaned_content[:200]}...")

    try:
        data = loads_with_repair(cleaned_content)

        if not isinstance(data, dict):
            return False, {}, f"Invalid {questionnaire_type} response: expected JSON object"

        # Validate based on questionnaire type
        if questionnaire_type == "PCS":
            if "scores" not in data:
                return False, {}, f"Invalid {questionnaire_type} response: missing 'scores' field"
            if not isinstance(data["scores"], dict):
                return False, {}, f"Invalid {questionnaire_type} response: 'scores' should be an object"
        else:  # BPI-IS and TSK-11SV use responses array
            if "responses" not in data:
                return False, {}, f"Invalid {questionnaire_type} response: missing 'responses' field"
            if not isinstance(data["responses"], list):
                return False, {}, f"Invalid {questionnaire_type} response: 'responses' should be an array"

        return True, data, None

    except json.JSONDecodeError as e:
        logger.error(f"{questionnaire_type} JSON decode error: {e}")
        return False, {}, f"Could not parse JSON response: {str(e)}"


def run_questionnaire(
    narrative: str,
    questionnaire_type: str,
    llm_client: LLMClient,
    model: str,
    temperature: float,
    system_role: Optional[str] = None,
    instructions: Optional[str] = None,
    max_tokens: int = 8000,
) -> QuestionnaireResult:
    """
    Run a questionnaire evaluation on a narrative.

    `BedrockAuthError` propagates so the caller can halt the batch immediately;
    every other exception is captured in the returned result so a per-narrative
    failure does not abort the run.
    """
    # Get prompts from YAML config if not provided
    if system_role is None or instructions is None:
        yaml_prompts = get_questionnaire_prompt(questionnaire_type)
        if system_role is None:
            system_role = yaml_prompts.get("system_role", "")
        if instructions is None:
            instructions = yaml_prompts.get("instructions", "")

    # Build the prompt
    prompt = instructions.replace("{narrative}", narrative)
    messages = [
        {"role": "system", "content": system_role},
        {"role": "user", "content": prompt},
    ]

    logger.info(f"Running {questionnaire_type} questionnaire evaluation")

    try:
        response = llm_client.create_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format="json_object",
        )

        # Extract content
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

        if not content:
            logger.error(f"Empty content from API for {questionnaire_type}")
            return QuestionnaireResult(
                questionnaire_type=questionnaire_type,
                success=False,
                data={},
                raw_response=response,
                messages=messages,
                error="Model returned empty response",
            )

        # Parse the response
        success, data, error = parse_questionnaire_response(content, questionnaire_type)

        return QuestionnaireResult(
            questionnaire_type=questionnaire_type,
            success=success,
            data=data,
            raw_response=response,
            messages=messages,
            error=error,
        )

    except BedrockAuthError:
        # Halt the batch — refreshing credentials is the only recourse.
        raise
    except Exception as e:
        logger.error(f"{questionnaire_type} questionnaire failed: {str(e)}", exc_info=True)
        return QuestionnaireResult(
            questionnaire_type=questionnaire_type,
            success=False,
            data={},
            raw_response={},
            messages=messages,
            error=str(e),
        )


# Score calculation functions (copied from questionnaire.py for independence)


def calculate_pcs_total_score(result: QuestionnaireResult) -> int:
    """Calculate total score for PCS questionnaire (0-52 range)."""
    scores = result.scores
    return sum(int(score) for score in scores.values())


def calculate_bpi_is_total_score(result: QuestionnaireResult) -> int:
    """Calculate total score for BPI-IS questionnaire."""
    responses = result.responses
    return sum(r.get("value", 0) for r in responses)


def calculate_tsk_11sv_total_score(result: QuestionnaireResult) -> int:
    """Calculate total score for TSK-11SV questionnaire (11-44 range)."""
    responses = result.responses
    return sum(r.get("value", 0) for r in responses)


def calculate_pcs_subscales(result: QuestionnaireResult) -> Dict[str, int]:
    """
    Calculate PCS subscales.

    Returns:
        Dict with 'rumination', 'magnification', 'helplessness' scores
    """
    scores = result.scores

    # PCS subscale mappings (question numbers)
    rumination_items = ["8", "9", "10", "11"]  # Q8-Q11
    magnification_items = ["6", "7", "13"]  # Q6, Q7, Q13
    helplessness_items = ["1", "2", "3", "4", "5", "12"]  # Q1-Q5, Q12

    def sum_items(items: List[str]) -> int:
        return sum(int(scores.get(item, 0)) for item in items)

    return {
        "rumination": sum_items(rumination_items),
        "magnification": sum_items(magnification_items),
        "helplessness": sum_items(helplessness_items),
    }


def calculate_bpi_is_subscales(result: QuestionnaireResult) -> Dict[str, float]:
    """
    Calculate BPI-IS subscales.

    Returns:
        Dict with 'interference' (average) and 'intensity' (average) scores
    """
    responses = result.responses

    # Build lookup by code
    scores_by_code = {r.get("code"): r.get("value", 0) for r in responses}

    # Interference items (Q1 group)
    interference_codes = ["BPI_Q1_1", "BPI_Q1_2", "BPI_Q1_3", "BPI_Q1_5", "BPI_Q1_6", "BPI_Q1_7"]
    interference_values = [scores_by_code.get(code, 0) for code in interference_codes]
    interference_avg = sum(interference_values) / len(interference_values) if interference_values else 0

    # Intensity items (Q2-Q5)
    intensity_codes = ["BPI_Q2_8", "BPI_Q3_9", "BPI_Q4_10", "BPI_Q5_11"]
    intensity_values = [scores_by_code.get(code, 0) for code in intensity_codes]
    intensity_avg = sum(intensity_values) / len(intensity_values) if intensity_values else 0

    return {
        "interference_avg": round(interference_avg, 2),
        "intensity_avg": round(intensity_avg, 2),
        "interference_total": sum(interference_values),
        "intensity_total": sum(intensity_values),
    }

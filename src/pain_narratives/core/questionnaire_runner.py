"""
Streamlit-free questionnaire runners for batch processing.

This module provides pure functions for running PCS, BPI-IS, and TSK-11SV 
questionnaires without any Streamlit dependencies. It can be used by both
the Streamlit UI (via wrappers) and the batch processing CLI.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from pain_narratives.config.prompts import get_questionnaire_prompt
from pain_narratives.core.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


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


def parse_questionnaire_response(
    content: str, 
    questionnaire_type: str
) -> Tuple[bool, Dict[str, Any], Optional[str]]:
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
        data = json.loads(cleaned_content)
        
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
    openai_client: OpenAIClient,
    model: str,
    temperature: float,
    system_role: Optional[str] = None,
    instructions: Optional[str] = None,
    max_tokens: int = 8000,
) -> QuestionnaireResult:
    """
    Run a questionnaire evaluation on a narrative.
    
    Args:
        narrative: The pain narrative text
        questionnaire_type: One of 'PCS', 'BPI-IS', 'TSK-11SV'
        openai_client: OpenAI client instance
        model: Model to use (e.g., 'gpt-5-mini')
        temperature: Temperature for generation
        system_role: Optional custom system role (uses YAML default if None)
        instructions: Optional custom instructions (uses YAML default if None)
        max_tokens: Maximum tokens for response
        
    Returns:
        QuestionnaireResult with success status and data
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
        response = openai_client.create_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format="json_object",
        )
        
        # Extract content
        content = (
            response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        
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


def run_pcs_questionnaire_pure(
    narrative: str,
    openai_client: OpenAIClient,
    model: str,
    temperature: float,
    system_role: Optional[str] = None,
    instructions: Optional[str] = None,
) -> QuestionnaireResult:
    """Run PCS questionnaire (Streamlit-free)."""
    return run_questionnaire(
        narrative=narrative,
        questionnaire_type="PCS",
        openai_client=openai_client,
        model=model,
        temperature=temperature,
        system_role=system_role,
        instructions=instructions,
    )


def run_bpi_is_questionnaire_pure(
    narrative: str,
    openai_client: OpenAIClient,
    model: str,
    temperature: float,
    system_role: Optional[str] = None,
    instructions: Optional[str] = None,
) -> QuestionnaireResult:
    """Run BPI-IS questionnaire (Streamlit-free)."""
    return run_questionnaire(
        narrative=narrative,
        questionnaire_type="BPI-IS",
        openai_client=openai_client,
        model=model,
        temperature=temperature,
        system_role=system_role,
        instructions=instructions,
    )


def run_tsk_11sv_questionnaire_pure(
    narrative: str,
    openai_client: OpenAIClient,
    model: str,
    temperature: float,
    system_role: Optional[str] = None,
    instructions: Optional[str] = None,
) -> QuestionnaireResult:
    """Run TSK-11SV questionnaire (Streamlit-free)."""
    return run_questionnaire(
        narrative=narrative,
        questionnaire_type="TSK-11SV",
        openai_client=openai_client,
        model=model,
        temperature=temperature,
        system_role=system_role,
        instructions=instructions,
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

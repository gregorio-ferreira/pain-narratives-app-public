"""Questionnaire utilities for Streamlit UI."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

import streamlit as st

from pain_narratives.core.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

##########################################################################
# Questionnaire Data Structures and Runners ##############################


##########################################################################
# PCS Questionnaire Data Structures

PCS_SCORE_LABELS = {
    0: "Nada (Not at all)",
    1: "Algo (Somewhat)",
    2: "Bastante (Quite a bit)",
    3: "Mucho (A lot)",
    4: "Muchísimo (Extremely)",
}

PCS_QUESTIONS = {
    1: "Estoy preocupado todo el tiempo pensando si el dolor desaparecerá",
    2: "Siento que ya no puedo más.",
    3: "Es terrible y pienso que esto nunca va a mejorar",
    4: "Esto es horrible y siento que esto es más fuerte que yo",
    5: "Siento que no puedo soportarlo más",
    6: "Temo que el dolor empeore.",
    7: "No dejo de pensar en otras situaciones en las que experimento dolor",
    8: "Deseo desesperadamente que desaparezca el dolor",
    9: "No puedo apartar el dolor de mi mente",
    10: "No dejo de pensar en lo mucho que me duele",
    11: "No dejo de pensar en lo mucho que deseo que desaparezca el dolor",
    12: "No hay nada que pueda hacer para aliviar la intensidad del dolor",
    13: "Me pregunto si me pude pasar algo grave",
}

PCS_SYSTEM_ROLE = (
    "You are an expert in psychological assessment. Your task is to "
    "impersonate the person who wrote the following pain narrative, and answer "
    'the "Pain Catastrophizing Scale" (PCS) questionnaire as if you were that person.'
)

PCS_INSTRUCTIONS = """
**Instructions:**

1. Carefully read the pain narrative below.
2. Imagine you are the person describing these experiences and feelings.
3. For each of the 13 questions in the PCS, select the score that best reflects how this person would likely respond, using the following scale:

   * 0: Nada (Not at all)
   * 1: Algo (Somewhat)
   * 2: Bastante (Quite a bit)
   * 3: Mucho (A lot)
   * 4: Muchísimo (Extremely)
4. Output a JSON object where the key is the question number and the value is the score selected.
5. After the JSON object, provide a brief overall explanation (“model reasoning”) describing **how and why** you answered the questionnaire with those scores, based on the pain narrative.

#### **PCS Questionnaire**
1. Estoy preocupado todo el tiempo pensando si el dolor desaparecerá
2. Siento que ya no puedo más.
3. Es terrible y pienso que esto nunca va a mejorar
4. Esto es horrible y siento que esto es más fuerte que yo
5. Siento que no puedo soportarlo más
6. Temo que el dolor empeore.
7. No dejo de pensar en otras situaciones en las que experimento dolor
8. Deseo desesperadamente que desaparezca el dolor
9. No puedo apartar el dolor de mi mente
10. No dejo de pensar en lo mucho que me duele
11. No dejo de pensar en lo mucho que deseo que desaparezca el dolor
12. No hay nada que pueda hacer para aliviar la intensidad del dolor
13. Me pregunto si me pude pasar algo grave

---
#### **Pain narrative**
{narrative}
---

**Output format:**
```json
{
  "questionnaire_id": "PCS",
  "persona": {
    "name": "PersonaName",
    "traits": "brief description of key personality traits inferred from narrative"
  },
  "scores": {
    "1": score,
    "2": score,
    "3": score,
    "4": score,
    "5": score,
    "6": score,
    "7": score,
    "8": score,
    "9": score,
    "10": score,
    "11": score,
    "12": score,
    "13": score
  },
  "model_reasoning": "Write a brief explanation of how you, as the model, impersonated the person from the narrative to answer the questionnaire. Explain the overall reasoning for the pattern of scores you selected, citing general evidence from the narrative."
}
```
"""

##########################################################################
# BPI-IS Questionnaire Data Structures
BPI_IS_QUESTIONS = {
    "BPI_Q1_1": "Actividad general",
    "BPI_Q1_2": "Estado de ánimo",
    "BPI_Q1_3": "Capacidad de andar",
    "BPI_Q1_5": "Relaciones con otras personas",
    "BPI_Q1_6": "Sueño",
    "BPI_Q1_7": "Disfrute de la vida",
    "BPI_Q2_8": "Peor Dolor",
    "BPI_Q3_9": "Dolor Más Leve",
    "BPI_Q4_10": "Dolor Promedio",
    "BPI_Q5_11": "Dolor Ahora Mismo"
}

# Question groups with their specific instructions from the original questionnaire
BPI_IS_QUESTION_GROUPS = {
    "Q1": {
        "instruction": "Marque el número que mejor describa hasta qué punto el dolor le ha perturbado en los siguientes aspectos de la vida, durante LA ÚLTIMA SEMANA, siendo 0 = \"No le perturba nada\" y 10 = \"Le perturba totalmente\":",
        "items": ["BPI_Q1_1", "BPI_Q1_2", "BPI_Q1_3", "BPI_Q1_5", "BPI_Q1_6", "BPI_Q1_7"],
        "scale_labels": {0: "No le perturba nada", 10: "Le perturba totalmente"}
    },
    "Q2": {
        "instruction": "Puntúe EL PEOR DOLOR QUE HA SENTIDO EN LAS ÚLTIMAS 24 HORAS del 0 al 10, donde 0 representa \"sin dolor\" y 10 representa \"el peor dolor que se pueda imaginar\".",
        "items": ["BPI_Q2_8"],
        "scale_labels": {0: "Sin dolor", 10: "El peor dolor que se pueda imaginar"}
    },
    "Q3": {
        "instruction": "El DOLOR MÁS LEVE QUE HA SENTIDO EN LAS ÚLTIMAS 24 HORAS del 0 al 10, donde 0 representa \"sin dolor\" y 10 representa \"el peor dolor que se pueda imaginar\".",
        "items": ["BPI_Q3_9"],
        "scale_labels": {0: "Sin dolor", 10: "El peor dolor que se pueda imaginar"}
    },
    "Q4": {
        "instruction": "El DOLOR PROMEDIO EN LAS ÚLTIMAS 24 HORAS del 0 al 10, donde 0 representa \"sin dolor\" y 10 representa \"el peor dolor que se pueda imaginar\".",
        "items": ["BPI_Q4_10"],
        "scale_labels": {0: "Sin dolor", 10: "El peor dolor que se pueda imaginar"}
    },
    "Q5": {
        "instruction": "Puntúe EL DOLOR AHORA MISMO del 0 al 10, donde 0 representa \"sin dolor\" y 10 representa \"el peor dolor que se pueda imaginar\".",
        "items": ["BPI_Q5_11"],
        "scale_labels": {0: "Sin dolor", 10: "El peor dolor que se pueda imaginar"}
    }
}

BPI_IS_SCALE_LABELS = {
    # Interference items (BPI_1 to BPI_7)
    "interference": {
        0: "No le perturba nada",
        10: "Le perturba totalmente"
    },
    # Intensity items (BPI_8 to BPI_11)
    "intensity": {
        0: "Sin dolor",
        10: "El peor dolor que se pueda imaginar"
    }
}

BPI_IS_SYSTEM_ROLE = (
    "You are an expert in pain assessment. Your task is to "
    "impersonate the person who wrote the following pain narrative, and answer "
    'the "Brief Pain Inventory - Interference Scale" (BPI-IS) questionnaire as if you were that person. '
    "The BPI-IS evaluates how pain interferes with daily activities (Q1) and measures pain intensity "
    "at different time points (Q2-Q5). Answer each question group following the specific instructions provided."
)

BPI_IS_INSTRUCTIONS = """
**Instructions:**

1. Carefully read the pain narrative below.
2. Imagine you are the person describing these experiences and feelings.
3. Answer each question group (Q1-Q5) following the specific instructions for each.
4. Respond ONLY with a JSON object conforming to the specified schema.

#### **BPI-IS Questionnaire (Brief Pain Inventory - Interference Scale)**

**Q1. Interferencia del dolor (última semana)**
Marque el número que mejor describa hasta qué punto el dolor le ha perturbado en los siguientes aspectos de la vida, durante LA ÚLTIMA SEMANA, siendo 0 = "No le perturba nada" y 10 = "Le perturba totalmente":

- BPI_Q1_1: Actividad general [0..10]
- BPI_Q1_2: Estado de ánimo [0..10]
- BPI_Q1_3: Capacidad de andar [0..10]
- BPI_Q1_5: Relaciones con otras personas [0..10]
- BPI_Q1_6: Sueño [0..10]
- BPI_Q1_7: Disfrute de la vida [0..10]

**Q2. Peor dolor (últimas 24 horas)**
Puntúe EL PEOR DOLOR QUE HA SENTIDO EN LAS ÚLTIMAS 24 HORAS del 0 al 10, donde 0 representa "sin dolor" y 10 representa "el peor dolor que se pueda imaginar":

- BPI_Q2_8: Peor Dolor [0..10]

**Q3. Dolor más leve (últimas 24 horas)**
El DOLOR MÁS LEVE QUE HA SENTIDO EN LAS ÚLTIMAS 24 HORAS del 0 al 10, donde 0 representa "sin dolor" y 10 representa "el peor dolor que se pueda imaginar":

- BPI_Q3_9: Dolor Más Leve [0..10]

**Q4. Dolor promedio (últimas 24 horas)**
El DOLOR PROMEDIO EN LAS ÚLTIMAS 24 HORAS del 0 al 10, donde 0 representa "sin dolor" y 10 representa "el peor dolor que se pueda imaginar":

- BPI_Q4_10: Dolor Promedio [0..10]

**Q5. Dolor ahora mismo**
Puntúe EL DOLOR AHORA MISMO del 0 al 10, donde 0 representa "sin dolor" y 10 representa "el peor dolor que se pueda imaginar":

- BPI_Q5_11: Dolor Ahora Mismo [0..10]

---
#### **Pain narrative**
{narrative}
---

**Output format (JSON only):**
```json
{
  "questionnaire_id": "BPI-IS",
  "persona": {
    "name": "PersonaName",
    "traits": "brief description of key personality traits inferred from narrative"
  },
  "responses": [
    {"code": "BPI_Q1_1", "value": 0},
    {"code": "BPI_Q1_2", "value": 0},
    {"code": "BPI_Q1_3", "value": 0},
    {"code": "BPI_Q1_5", "value": 0},
    {"code": "BPI_Q1_6", "value": 0},
    {"code": "BPI_Q1_7", "value": 0},
    {"code": "BPI_Q2_8", "value": 0},
    {"code": "BPI_Q3_9", "value": 0},
    {"code": "BPI_Q4_10", "value": 0},
    {"code": "BPI_Q5_11", "value": 0}
  ],
  "model_reasoning": "Write a brief explanation of how you, as the model, impersonated the person from the narrative to answer the questionnaire. Explain the overall reasoning for the pattern of scores you selected, citing general evidence from the narrative."
}
```
"""

##########################################################################
# TSK-11SV Questionnaire Data Structures
TSK_11SV_QUESTIONS = {
    "TSK_01": "Tengo miedo de lesionarme si hago ejercicio físico",
    "TSK_02": "Si me dejara vencer por el dolor, el dolor aumentaría",
    "TSK_03": "Mi cuerpo me está diciendo que tengo algo serio",
    "TSK_04": "Tener dolor siempre quiere decir que en el cuerpo hay una lesión",
    "TSK_05": "Tengo miedo a lesionarme sin querer",
    "TSK_06": "Lo más seguro para evitar que aumente el dolor es tener cuidado y no hacer movimientos innecesarios",
    "TSK_07": "No me dolería tanto si no tuviese algo serio en mi cuerpo",
    "TSK_08": "El dolor me dice cuándo debo parar la actividad para no lesionarme",
    "TSK_09": "No es seguro para una persona con mi enfermedad hacer actividades físicas",
    "TSK_10": "No puedo hacer todo lo que la gente normal hace porque me podría lesionar con facilidad",
    "TSK_11": "Nadie debería hacer actividades físicas cuando tiene dolor"
}

TSK_11SV_SCALE_LABELS = {
    1: "Totalmente en desacuerdo",
    2: "En desacuerdo",
    3: "De acuerdo",
    4: "Totalmente de acuerdo"
}

TSK_11SV_SYSTEM_ROLE = (
    "You are an expert in kinesiophobia assessment. Your task is to "
    "impersonate the person who wrote the following pain narrative, and answer "
    'the "Tampa Scale of Kinesiophobia - 11 items Short Version" (TSK-11SV) questionnaire as if you were that person. '
    "The TSK-11SV measures fear of movement and activity avoidance due to pain. "
    "For each statement, indicate the degree of agreement based on the person's pain experience and attitudes toward movement."
)

TSK_11SV_INSTRUCTIONS = """
**Instructions:**

1. Carefully read the pain narrative below.
2. Imagine you are the person describing these experiences and feelings.
3. For each of the 11 statements in the TSK-11SV, select the score (1-4) that best reflects how this person would likely respond.
4. Respond ONLY with a JSON object conforming to the specified schema.

#### **TSK-11SV Questionnaire (Tampa Scale of Kinesiophobia - Short Version)**

**Instrucciones:** Indique en qué medida está de acuerdo con cada afirmación.

**Escala de respuesta:**
- 1 = "Totalmente en desacuerdo"
- 2 = "En desacuerdo"
- 3 = "De acuerdo"
- 4 = "Totalmente de acuerdo"

**Afirmaciones:**
- TSK_01: Tengo miedo de lesionarme si hago ejercicio físico [1..4]
- TSK_02: Si me dejara vencer por el dolor, el dolor aumentaría [1..4]
- TSK_03: Mi cuerpo me está diciendo que tengo algo serio [1..4]
- TSK_04: Tener dolor siempre quiere decir que en el cuerpo hay una lesión [1..4]
- TSK_05: Tengo miedo a lesionarme sin querer [1..4]
- TSK_06: Lo más seguro para evitar que aumente el dolor es tener cuidado y no hacer movimientos innecesarios [1..4]
- TSK_07: No me dolería tanto si no tuviese algo serio en mi cuerpo [1..4]
- TSK_08: El dolor me dice cuándo debo parar la actividad para no lesionarme [1..4]
- TSK_09: No es seguro para una persona con mi enfermedad hacer actividades físicas [1..4]
- TSK_10: No puedo hacer todo lo que la gente normal hace porque me podría lesionar con facilidad [1..4]
- TSK_11: Nadie debería hacer actividades físicas cuando tiene dolor [1..4]

---
#### **Pain narrative**
{narrative}
---

**Output format (JSON only):**
```json
{
  "questionnaire_id": "TSK-11SV",
  "persona": {
    "name": "PersonaName",
    "traits": "brief description of key personality traits inferred from narrative"
  },
  "responses": [
    {"code": "TSK_01", "value": 1},
    {"code": "TSK_02", "value": 1},
    {"code": "TSK_03", "value": 1},
    {"code": "TSK_04", "value": 1},
    {"code": "TSK_05", "value": 1},
    {"code": "TSK_06", "value": 1},
    {"code": "TSK_07", "value": 1},
    {"code": "TSK_08", "value": 1},
    {"code": "TSK_09", "value": 1},
    {"code": "TSK_10", "value": 1},
    {"code": "TSK_11", "value": 1}
  ],
  "model_reasoning": "Write a brief explanation of how you, as the model, impersonated the person from the narrative to answer the questionnaire. Explain the overall reasoning for the pattern of scores you selected, citing general evidence from the narrative."
}
```
"""


def run_pcs_questionnaire(
    narrative: str,
    openai_client: OpenAIClient,
    model: str,
    temperature: float,
    pcs_system_role: str = PCS_SYSTEM_ROLE,
    pcs_instructions: str = PCS_INSTRUCTIONS,
) -> Dict[str, Any]:
    """Run the PCS questionnaire using the given narrative."""
    # Avoid str.format() because PCS_INSTRUCTIONS contains many curly braces for
    # the JSON example. Using .format would attempt to treat those as
    # placeholders and raise ``KeyError``. Instead, simply replace the
    # ``{narrative}`` placeholder manually.
    prompt = pcs_instructions.replace("{narrative}", narrative)
    messages = [
        {"role": "system", "content": pcs_system_role},
        {"role": "user", "content": prompt},
    ]
    logger.info("Sending PCS questionnaire to OpenAI")
    response = openai_client.create_completion(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=8000,  # Increased for GPT-5 reasoning tokens + full JSON output
        response_format="json_object",  # Force JSON output
    )
    logger.info("Received response from OpenAI")
    # Store request/response in session state for later DB persistence
    st.session_state.last_openai_response = response
    st.session_state.last_prompt_messages = messages

    # Extract content with proper error handling for gpt-5 empty responses
    content = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    
    # Check if content is empty (common issue with gpt-5)
    if not content:
        logger.error("Received empty content from OpenAI API")
        logger.error(f"Full response: {response}")
        st.error("❌ The model returned an empty response. This can happen with gpt-5 when the response is truncated.")
        st.info("💡 Try again or switch to gpt-5-mini in the sidebar.")
        return {}
    
    logger.info(f"Raw response content: {content[:200]}...")  # Log first 200 chars for debugging

    # More robust JSON extraction
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

    cleaned_content = extract_json_from_text(content)
    logger.info(f"Cleaned JSON content: {cleaned_content[:200]}...")

    try:
        data = json.loads(cleaned_content)
        logger.info("Successfully parsed JSON response")

        # Validate the response structure
        if not isinstance(data, dict):
            logger.warning("Response is not a dictionary")
            st.warning("Invalid response format: expected JSON object")
            return {}

        if "scores" not in data:
            logger.warning("No 'scores' key found in response")
            st.warning("Invalid response format: missing 'scores' field")
            return {}

        scores = data["scores"]
        if not isinstance(scores, dict):
            logger.warning("'scores' is not a dictionary")
            st.warning("Invalid response format: 'scores' should be an object")
            return {}

        logger.info(f"Found {len(scores)} scores in response")
        return data

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        logger.error(f"Failed to parse content: {cleaned_content}")
        st.warning(f"Could not parse JSON response from model: {str(e)}")
        st.error("Please try again. If the problem persists, the model may not be following the JSON format.")
        return {}


def count_scores(scores: Dict[str, Any]) -> Dict[int, int]:
    """Count how many answers fall into each PCS score (0-4)."""
    counts = {i: 0 for i in range(5)}
    for value in scores.values():
        try:
            score = int(value)
            if 0 <= score <= 4:
                counts[score] += 1
        except (TypeError, ValueError):
            continue
    return counts


def run_bpi_is_questionnaire(
    narrative: str,
    openai_client: OpenAIClient,
    model: str,
    temperature: float,
    bpi_system_role: str = BPI_IS_SYSTEM_ROLE,
    bpi_instructions: str = BPI_IS_INSTRUCTIONS,
) -> Dict[str, Any]:
    """Run the BPI-IS questionnaire using the given narrative."""
    prompt = bpi_instructions.replace("{narrative}", narrative)
    messages = [
        {"role": "system", "content": bpi_system_role},
        {"role": "user", "content": prompt},
    ]
    logger.info("Sending BPI-IS questionnaire to OpenAI")
    response = openai_client.create_completion(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=8000,  # Increased for GPT-5 reasoning tokens + full JSON output
        response_format="json_object",  # Force JSON output
    )
    logger.info("Received BPI-IS response from OpenAI")
    
    # Store request/response in session state for later DB persistence
    st.session_state.last_openai_response = response
    st.session_state.last_prompt_messages = messages

    # Extract content with proper error handling for gpt-5 empty responses
    content = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    
    # Check if content is empty (common issue with gpt-5)
    if not content:
        logger.error("Received empty content from OpenAI API for BPI-IS")
        logger.error(f"Full response: {response}")
        st.error("❌ The model returned an empty response. This can happen with gpt-5 when the response is truncated.")
        st.info("💡 Try again or switch to gpt-5-mini in the sidebar.")
        return {}
    
    logger.info(f"Raw BPI-IS response content: {content[:200]}...")

    # Use the same JSON extraction logic as PCS
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

    cleaned_content = extract_json_from_text(content)
    logger.info(f"Cleaned BPI-IS JSON content: {cleaned_content[:200]}...")

    try:
        data = json.loads(cleaned_content)
        logger.info("Successfully parsed BPI-IS JSON response")

        # Validate the response structure
        if not isinstance(data, dict):
            logger.warning("BPI-IS response is not a dictionary")
            st.warning("Invalid BPI-IS response format: expected JSON object")
            return {}

        if "responses" not in data:
            logger.warning("No 'responses' key found in BPI-IS response")
            st.warning("Invalid BPI-IS response format: missing 'responses' field")
            return {}

        responses = data["responses"]
        if not isinstance(responses, list):
            logger.warning("BPI-IS 'responses' is not a list")
            st.warning("Invalid BPI-IS response format: 'responses' should be an array")
            return {}

        logger.info(f"Found {len(responses)} responses in BPI-IS response")
        return data

    except json.JSONDecodeError as e:
        logger.error(f"BPI-IS JSON decode error: {e}")
        logger.error(f"Failed to parse BPI-IS content: {cleaned_content}")
        st.warning(f"Could not parse BPI-IS JSON response from model: {str(e)}")
        st.error("Please try again. If the problem persists, the model may not be following the JSON format.")
        return {}


def run_tsk_11sv_questionnaire(
    narrative: str,
    openai_client: OpenAIClient,
    model: str,
    temperature: float,
    tsk_system_role: str = TSK_11SV_SYSTEM_ROLE,
    tsk_instructions: str = TSK_11SV_INSTRUCTIONS,
) -> Dict[str, Any]:
    """Run the TSK-11SV questionnaire using the given narrative."""
    prompt = tsk_instructions.replace("{narrative}", narrative)
    messages = [
        {"role": "system", "content": tsk_system_role},
        {"role": "user", "content": prompt},
    ]
    logger.info("Sending TSK-11SV questionnaire to OpenAI")
    response = openai_client.create_completion(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=8000,  # Increased for GPT-5 reasoning tokens + full JSON output
        response_format="json_object",  # Force JSON output
    )
    logger.info("Received TSK-11SV response from OpenAI")
    
    # Store request/response in session state for later DB persistence
    st.session_state.last_openai_response = response
    st.session_state.last_prompt_messages = messages

    # Extract content with proper error handling for gpt-5 empty responses
    content = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    
    # Check if content is empty (common issue with gpt-5)
    if not content:
        logger.error("Received empty content from OpenAI API for TSK-11SV")
        logger.error(f"Full response: {response}")
        st.error("❌ The model returned an empty response. This can happen with gpt-5 when the response is truncated.")
        st.info("💡 Try again or switch to gpt-5-mini in the sidebar.")
        return {}
    
    logger.info(f"Raw TSK-11SV response content: {content[:200]}...")

    # Use the same JSON extraction logic as PCS
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

    cleaned_content = extract_json_from_text(content)
    logger.info(f"Cleaned TSK-11SV JSON content: {cleaned_content[:200]}...")

    try:
        data = json.loads(cleaned_content)
        logger.info("Successfully parsed TSK-11SV JSON response")

        # Validate the response structure
        if not isinstance(data, dict):
            logger.warning("TSK-11SV response is not a dictionary")
            st.warning("Invalid TSK-11SV response format: expected JSON object")
            return {}

        if "responses" not in data:
            logger.warning("No 'responses' key found in TSK-11SV response")
            st.warning("Invalid TSK-11SV response format: missing 'responses' field")
            return {}

        responses = data["responses"]
        if not isinstance(responses, list):
            logger.warning("TSK-11SV 'responses' is not a list")
            st.warning("Invalid TSK-11SV response format: 'responses' should be an array")
            return {}

        logger.info(f"Found {len(responses)} responses in TSK-11SV response")
        return data

    except json.JSONDecodeError as e:
        logger.error(f"TSK-11SV JSON decode error: {e}")
        logger.error(f"Failed to parse TSK-11SV content: {cleaned_content}")
        st.warning(f"Could not parse TSK-11SV JSON response from model: {str(e)}")
        st.error("Please try again. If the problem persists, the model may not be following the JSON format.")
        return {}


def count_bpi_is_scores(responses: List[Dict[str, Any]]) -> Dict[int, int]:
    """Count how many BPI-IS answers fall into each score range (0-10)."""
    counts = {i: 0 for i in range(11)}
    for response in responses:
        try:
            score = int(response["value"])
            if 0 <= score <= 10:
                counts[score] += 1
        except (TypeError, ValueError, KeyError):
            continue
    return counts


def count_tsk_11sv_scores(responses: List[Dict[str, Any]]) -> Dict[int, int]:
    """Count how many TSK-11SV answers fall into each score (1-4)."""
    counts = {i: 0 for i in range(1, 5)}
    for response in responses:
        try:
            score = int(response["value"])
            if 1 <= score <= 4:
                counts[score] += 1
        except (TypeError, ValueError, KeyError):
            continue
    return counts


def calculate_pcs_total_score(result: Dict[str, Any]) -> int:
    """Calculate total score for PCS questionnaire."""
    scores = result.get("scores", {})
    return sum(int(score) for score in scores.values())


def calculate_bpi_is_total_score(result: Dict[str, Any]) -> int:
    """Calculate total score for BPI-IS questionnaire."""
    responses = result.get("responses", [])
    return sum(r["value"] for r in responses)


def calculate_tsk_11sv_total_score(result: Dict[str, Any]) -> int:
    """Calculate total score for TSK-11SV questionnaire."""
    responses = result.get("responses", [])
    return sum(r["value"] for r in responses)


def display_score_distribution_chart(counts: Dict[int, int], questionnaire_type: str, translator):
    """
    Display a standardized score distribution chart for any questionnaire type.
    
    Args:
        counts: Dictionary mapping score values to counts
        questionnaire_type: One of 'PCS', 'BPI-IS', 'TSK-11SV'
        translator: Translation function for localized labels
    """
    import altair as alt
    import pandas as pd
    import streamlit as st
    
    if not counts or all(count == 0 for count in counts.values()):
        st.info(translator("questionnaires.no_scores_warning"))
        return
    
    st.subheader(translator("questionnaires.score_distribution_header"))
    
    chart = None
    if questionnaire_type == "PCS":
        # PCS: Use defined order from PCS_SCORE_LABELS (0→1→2→3→4)
        ordered_scores = sorted(PCS_SCORE_LABELS.keys())
        chart_data = []
        for score in ordered_scores:
            chart_data.append({
                "Score": score,
                "Count": counts.get(score, 0),
                "Scale": PCS_SCORE_LABELS[score]
            })
        df = pd.DataFrame(chart_data)
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X(
                    "Scale:N",
                    axis=alt.Axis(labelAngle=-45, title="Scale"),
                    sort=None,  # Preserve DataFrame order
                ),
                y=alt.Y("Count:Q", axis=alt.Axis(title="Count")),
            )
        )
    elif questionnaire_type == "BPI-IS":
        # BPI-IS: Numeric 0-10 scale, displayed normally (not rotated)
        ordered_scores = list(range(11))  # 0 through 10
        chart_data = []
        for score in ordered_scores:
            chart_data.append({
                "Score": score,
                "Count": counts.get(score, 0)
            })
        df = pd.DataFrame(chart_data)
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X(
                    "Score:O",
                    axis=alt.Axis(title="Score (0-10)", labelAngle=0),  # No rotation
                    sort=None,  # Preserve natural numeric order
                ),
                y=alt.Y("Count:Q", axis=alt.Axis(title="Count")),
            )
        )
    elif questionnaire_type == "TSK-11SV":
        # TSK-11SV: Use defined order from TSK_11SV_SCALE_LABELS (1→2→3→4)
        ordered_scores = sorted(TSK_11SV_SCALE_LABELS.keys())
        chart_data = []
        for score in ordered_scores:
            chart_data.append({
                "Score": score,
                "Count": counts.get(score, 0),
                "Scale": TSK_11SV_SCALE_LABELS[score]
            })
        df = pd.DataFrame(chart_data)
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X(
                    "Scale:N",
                    axis=alt.Axis(labelAngle=-45, title="Scale"),
                    sort=None,  # Preserve DataFrame order
                ),
                y=alt.Y("Count:Q", axis=alt.Axis(title="Count")),
            )
        )
    else:
        st.error(f"Unknown questionnaire type: {questionnaire_type}")
        return

    if chart is not None:
        st.altair_chart(chart, use_container_width=True)





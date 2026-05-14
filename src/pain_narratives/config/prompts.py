"""
Configuration loader for default prompts.

This module provides centralized access to all default prompts used across the application.
Prompts are loaded from default_prompts.yaml for easy maintenance and updates.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# Path to the default prompts YAML file
PROMPTS_CONFIG_FILE = Path(__file__).parent / "default_prompts.yaml"

# Map of prompt-version name -> YAML file. "original" is what was used in the
# published GPT-5 baseline; "simplified_v1" is the revision-experiment variant.
PROMPT_VERSION_FILES: Dict[str, Path] = {
    "original": PROMPTS_CONFIG_FILE,
    "simplified_v1": Path(__file__).parent / "simplified_v1_prompts.yaml",
}


@lru_cache(maxsize=4)
def load_prompts_version(version: str = "original") -> Dict[str, Any]:
    """Load a versioned prompts configuration.

    `version="original"` returns the pre-revision baseline used by the published
    GPT-5 experiments (groups 38, 39, 40); `version="simplified_v1"` returns the
    structured-answer-only variant used by the DeepSeek-R1 / Claude Sonnet 4.5
    revision runs.
    """
    if version not in PROMPT_VERSION_FILES:
        raise ValueError(f"Unknown prompt version {version!r}; known versions: {list(PROMPT_VERSION_FILES)}")
    path = PROMPT_VERSION_FILES[version]
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    logger.info(f"Loaded prompts version {version!r} from {path}")
    return config


@lru_cache(maxsize=1)
def load_prompts_config() -> Dict[str, Any]:
    """Backward-compatible loader: returns the original-version prompts."""
    return load_prompts_version("original")


def get_narrative_evaluation_config(version: str = "original") -> Dict[str, Any]:
    """Return the `narrative_evaluation` block from the requested prompt version."""
    return load_prompts_version(version).get("narrative_evaluation", {})


def get_system_role(version: str = "original") -> str:
    """Return the system role for narrative evaluation in the requested version."""
    return get_narrative_evaluation_config(version).get("system_role", "").strip()


def get_base_prompt(version: str = "original") -> str:
    """Return the base prompt for narrative evaluation in the requested version."""
    return get_narrative_evaluation_config(version).get("base_prompt", "").strip()


def get_default_dimensions(version: str = "original") -> List[Dict[str, Any]]:
    """Return the dimension list for the requested prompt version, in app format
    (string min/max, generated uuid per dimension)."""
    dimensions = get_narrative_evaluation_config(version).get("dimensions", [])

    import uuid
    from datetime import datetime

    timestamp = int(datetime.now().timestamp() * 1000000)
    return [
        {
            "name": dim.get("name", ""),
            "definition": dim.get("definition", ""),
            "min": str(dim.get("min", 0)),
            "max": str(dim.get("max", 10)),
            "uuid": f"{timestamp}_{str(uuid.uuid4())}",
            "active": dim.get("active", True),
        }
        for dim in dimensions
    ]


def get_default_prompt(version: str = "original") -> str:
    """Generate the complete prompt template for the requested version, with a
    `{narrative}` placeholder at the end."""
    system_role = get_system_role(version)
    base_prompt = get_base_prompt(version)
    dimensions = get_default_dimensions(version)

    # Build the dimensions section
    dimension_lines = [
        "Please analyze the following narrative and provide scores for these dimensions as specified:",
        "",
    ]

    for idx, dim in enumerate(dimensions, 1):
        if dim.get("active", True):
            dimension_lines.append(
                f"{idx}. **{dim['name']}**: {dim['definition']} (Score range: {dim['min']}-{dim['max']})"
            )

    # Build JSON structure
    json_structure = ["Please respond in JSON format with the following structure:", "{{"]

    for dim in dimensions:
        if dim.get("active", True):
            field_name = dim["name"].lower().replace(" ", "_").replace("-", "_")
            json_structure.append(f'    "{field_name}": <score>,')
            json_structure.append(
                f'    "{field_name}_explanation": "<explanation in English for the {dim["name"].lower()}">",'
            )

    json_structure.extend(['    "reasoning": "<brief explanation of your overall scoring>"', "}}"])

    # Combine all parts
    parts = []
    if system_role:
        parts.append(system_role)
    parts.append("\n".join(dimension_lines))
    if base_prompt:
        parts.append(base_prompt)
    parts.append("\n".join(json_structure))
    parts.append("Patient narrative:\n{narrative}")

    return "\n\n".join(parts)


def get_questionnaire_prompts(version: str = "original") -> Dict[str, Dict[str, str]]:
    """Return all questionnaire prompts (PCS, BPI-IS, TSK-11SV) for the requested
    prompt version, as a dict mapping type → {system_role, instructions}."""
    questionnaires = load_prompts_version(version).get("questionnaires", {})
    return {
        q_type: {
            "system_role": q_config.get("system_role", "").strip(),
            "instructions": q_config.get("instructions", "").strip(),
        }
        for q_type, q_config in questionnaires.items()
    }


def get_questionnaire_prompt(questionnaire_type: str, version: str = "original") -> Optional[Dict[str, str]]:
    """Get prompts for a specific questionnaire type and prompt version.

    Args:
        questionnaire_type: One of 'PCS', 'BPI-IS', 'TSK-11SV'
        version: prompt version key from PROMPT_VERSION_FILES (default: "original")
    """
    config = load_prompts_version(version)
    q = config.get("questionnaires", {}).get(questionnaire_type)
    if not q:
        return None
    return {
        "system_role": q.get("system_role", "").strip(),
        "instructions": q.get("instructions", "").strip(),
    }


def get_prompt_library() -> Dict[str, Dict[str, Any]]:
    """
    Get all prompt library templates.

    Returns:
        Dict mapping template IDs to their configuration (name, description, category, template)
    """
    config = load_prompts_config()
    library = config.get("prompt_library", {})

    # Add created timestamp for compatibility with existing code
    from datetime import datetime

    result = {}
    for template_id, template_config in library.items():
        result[template_id] = {
            "name": template_config.get("name", ""),
            "description": template_config.get("description", ""),
            "category": template_config.get("category", "custom"),
            "template": template_config.get("template", "").strip(),
            "created": datetime.now().isoformat(),
        }

    return result


def reload_prompts_config() -> None:
    """
    Clear the cache and reload the prompts configuration.

    Use this function when the YAML file has been updated and you need to reload it.
    """
    load_prompts_config.cache_clear()
    logger.info("Prompts configuration cache cleared and reloaded")


# Convenience functions for backward compatibility
def get_default_system_role() -> str:
    """Alias for get_system_role() for backward compatibility."""
    return get_system_role()


def get_default_base_prompt() -> str:
    """Alias for get_base_prompt() for backward compatibility."""
    return get_base_prompt()

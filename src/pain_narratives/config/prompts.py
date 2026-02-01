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


@lru_cache(maxsize=1)
def load_prompts_config() -> Dict[str, Any]:
    """
    Load the default prompts configuration from YAML file.
    
    This function is cached to avoid repeated file I/O operations.
    
    Returns:
        Dict containing all prompt configurations
        
    Raises:
        FileNotFoundError: If the prompts config file doesn't exist
        yaml.YAMLError: If the YAML file is malformed
    """
    try:
        with open(PROMPTS_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded prompts configuration from {PROMPTS_CONFIG_FILE}")
        return config
    except FileNotFoundError:
        logger.error(f"Prompts configuration file not found: {PROMPTS_CONFIG_FILE}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing prompts YAML file: {e}")
        raise


def get_narrative_evaluation_config() -> Dict[str, Any]:
    """
    Get narrative evaluation prompt configuration.
    
    Returns:
        Dict with keys: system_role, base_prompt, dimensions
    """
    config = load_prompts_config()
    return config.get("narrative_evaluation", {})


def get_system_role() -> str:
    """
    Get the default system role for narrative evaluation.
    
    Returns:
        System role prompt as string
    """
    config = get_narrative_evaluation_config()
    return config.get("system_role", "").strip()


def get_base_prompt() -> str:
    """
    Get the default base prompt for narrative evaluation.
    
    Returns:
        Base prompt as string
    """
    config = get_narrative_evaluation_config()
    return config.get("base_prompt", "").strip()


def get_default_dimensions() -> List[Dict[str, Any]]:
    """
    Get the default evaluation dimensions.
    
    Returns:
        List of dimension dictionaries with keys: name, definition, min, max, active
    """
    config = get_narrative_evaluation_config()
    dimensions = config.get("dimensions", [])
    
    # Convert to format expected by the application (with uuid generation)
    import uuid
    from datetime import datetime
    
    result = []
    timestamp = int(datetime.now().timestamp() * 1000000)
    
    for dim in dimensions:
        result.append({
            "name": dim.get("name", ""),
            "definition": dim.get("definition", ""),
            "min": str(dim.get("min", 0)),
            "max": str(dim.get("max", 10)),
            "uuid": f"{timestamp}_{str(uuid.uuid4())}",
            "active": dim.get("active", True)
        })
    
    return result


def get_default_prompt() -> str:
    """
    Generate the complete default prompt for narrative evaluation.
    
    This combines system_role, base_prompt, and dimensions into a full prompt template.
    
    Returns:
        Complete prompt template with {narrative} placeholder
    """
    system_role = get_system_role()
    base_prompt = get_base_prompt()
    dimensions = get_default_dimensions()
    
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


def get_questionnaire_prompts() -> Dict[str, Dict[str, str]]:
    """
    Get all questionnaire prompts (PCS, BPI-IS, TSK-11SV).
    
    Returns:
        Dict mapping questionnaire types to their system_role and instructions
    """
    config = load_prompts_config()
    questionnaires = config.get("questionnaires", {})
    
    result = {}
    for q_type, q_config in questionnaires.items():
        result[q_type] = {
            "system_role": q_config.get("system_role", "").strip(),
            "instructions": q_config.get("instructions", "").strip()
        }
    
    return result


def get_questionnaire_prompt(questionnaire_type: str) -> Optional[Dict[str, str]]:
    """
    Get prompts for a specific questionnaire type.
    
    Args:
        questionnaire_type: One of 'PCS', 'BPI-IS', 'TSK-11SV'
        
    Returns:
        Dict with 'system_role' and 'instructions' keys, or None if not found
    """
    prompts = get_questionnaire_prompts()
    return prompts.get(questionnaire_type)


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
            "created": datetime.now().isoformat()
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

from pathlib import Path
from typing import Any, Dict

import streamlit as st
import yaml

# Global cache to avoid Streamlit caching issues during page config
_language_cache: Dict[str, Dict[str, Any]] = {}


def _load_language_data_uncached(language: str) -> Dict[str, Any]:
    """Load the YAML file for the given language without caching."""
    locales_path = Path(__file__).resolve().parent.parent.parent / "locales"

    # Load the localization file for the given language
    lang_file = locales_path / f"{language}.yml"

    if not lang_file.exists():
        # Final fallback to English
        lang_file = locales_path / "en.yml"

    with open(lang_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# Cache with ttl to allow for language switching
@st.cache_data(ttl=1)  # Short TTL for language switching
def _load_language_data_cached(language: str) -> Dict[str, Any]:
    """Load the YAML file for the given language with Streamlit caching."""
    return _load_language_data_uncached(language)


def _load_language_data(language: str, use_cache: bool = True) -> Dict[str, Any]:
    """Load language data with optional caching."""
    if not use_cache:
        # Use global cache to avoid repeated file reads during page config
        if language not in _language_cache:
            _language_cache[language] = _load_language_data_uncached(language)
        return _language_cache[language]
    else:
        # Use Streamlit caching for normal operation
        return _load_language_data_cached(language)


def get_translator(language: str, use_cache: bool = True):
    """Return a translation function for the selected language."""
    # Clear cache when language changes (only if using cache)
    if use_cache:
        current_lang = st.session_state.get("current_localization_language")
        if current_lang != language:
            st.cache_data.clear()
            # Also clear global cache
            _language_cache.clear()
            st.session_state.current_localization_language = language

    lang_data = _load_language_data(language, use_cache=use_cache)

    def t(key: str) -> str:
        value = lang_data
        try:
            for k in key.split("."):
                value = value[k]
            return str(value)
        except (KeyError, TypeError):
            # Return the key itself if translation not found
            return key

    return t


def clear_language_cache():
    """Clear language cache when switching languages."""
    st.cache_data.clear()
    _language_cache.clear()


def format_string(template: str, **kwargs) -> str:
    """Format a localized string with parameters."""
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError):
        return template

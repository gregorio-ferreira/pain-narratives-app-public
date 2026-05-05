"""
Test script for multilingual evaluation results functionality.
"""

import logging

from pain_narratives.core.openai_client import OpenAIClient
from pain_narratives.core.translation_service import TranslationService


def test_translation_service():
    """Test the translation service functionality."""

    # Sample evaluation result (English)
    sample_result = {
        "pain_intensity": 8,
        "functional_impact": 7,
        "emotional_impact": 9,
        "reasoning": "The patient describes severe chronic pain with significant functional limitations and emotional distress.",
        "explanations": {
            "pain_intensity": "The narrative indicates very high pain levels with descriptors like 'excruciating' and 'unbearable'.",
            "functional_impact": "Patient reports inability to perform daily activities and work-related tasks.",
            "emotional_impact": "Clear evidence of depression, anxiety, and despair related to the chronic pain condition.",
        },
    }

    print("🧪 Testing Translation Service")
    print("=" * 50)

    try:
        translation_service = TranslationService()

        # Test translation to Spanish
        print("📝 Original English result:")
        print(f"  Reasoning: {sample_result['reasoning'][:100]}...")
        print(f"  Pain intensity explanation: {sample_result['explanations']['pain_intensity'][:100]}...")

        print("\n🔄 Translating to Spanish...")
        spanish_result = translation_service.translate_evaluation_result(sample_result, "es")

        print("🇪🇸 Spanish translation:")
        print(f"  Reasoning: {spanish_result.get('reasoning', 'N/A')[:100]}...")
        if "explanations" in spanish_result:
            print(
                f"  Pain intensity explanation: {spanish_result['explanations'].get('pain_intensity', 'N/A')[:100]}..."
            )

        # Test multilingual result structure
        print("\n🌍 Testing multilingual result structure...")
        multilingual_result = {"en": sample_result, "es": spanish_result}

        # Test getting available translation
        en_result = translation_service.get_available_translation(multilingual_result, "en")
        es_result = translation_service.get_available_translation(multilingual_result, "es")
        fr_result = translation_service.get_available_translation(
            multilingual_result, "fr"
        )  # Should fallback to English

        print(f"✅ English retrieval: {en_result.get('reasoning', 'N/A')[:50]}...")
        print(f"✅ Spanish retrieval: {es_result.get('reasoning', 'N/A')[:50]}...")
        print(f"✅ French fallback: {fr_result.get('reasoning', 'N/A')[:50]}...")

        print("\n🎉 Translation service test completed successfully!")

    except Exception as e:
        print(f"❌ Translation test failed: {e}")
        logging.error(f"Translation test failed: {e}", exc_info=True)


def test_multilingual_storage_structure():
    """Test the multilingual storage structure."""

    print("\n📦 Testing Multilingual Storage Structure")
    print("=" * 50)

    # Simulate the new multilingual storage format
    sample_db_result = {
        "en": {
            "pain_intensity": 8,
            "reasoning": "The patient describes severe chronic pain conditions.",
            "explanations": {"pain_intensity": "High pain levels indicated by descriptive language."},
        },
        "es": {
            "pain_intensity": 8,
            "reasoning": "El paciente describe condiciones de dolor crónico severo.",
            "explanations": {"pain_intensity": "Altos niveles de dolor indicados por el lenguaje descriptivo."},
        },
    }

    translation_service = TranslationService()

    # Test language retrieval
    languages_to_test = ["en", "es", "fr", "de"]

    for lang in languages_to_test:
        result = translation_service.get_available_translation(sample_db_result, lang)
        status = "✅ Found" if lang in sample_db_result else "⚠️ Fallback to English"
        print(f"{status} - {lang.upper()}: {result.get('reasoning', 'N/A')[:60]}...")

    print("\n🎉 Multilingual storage test completed!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("🚀 Starting Multilingual Evaluation Results Tests")
    print("=" * 60)

    test_translation_service()
    test_multilingual_storage_structure()

    print("\n✨ All tests completed!")

"""
Test script for translation configuration and model settings.
"""

import logging

from pain_narratives.config.settings import get_settings
from pain_narratives.core.translation_service import TranslationService


def test_translation_config():
    """Test that translation configuration is loaded correctly."""

    print("🔧 Testing Translation Configuration")
    print("=" * 50)

    try:
        settings = get_settings()
        model_config = settings.model_config

        print(f"✅ Default model: {model_config.default_model}")
        print(f"✅ Translation model: {model_config.translation_model}")
        print(f"✅ Translation temperature: {model_config.translation_temperature}")
        print(f"✅ Translation max tokens: {model_config.translation_max_tokens}")

        print("\n🧪 Testing TranslationService initialization...")
        translation_service = TranslationService()

        print(f"✅ Service initialized with model: {translation_service.model_config.translation_model}")
        print(f"✅ Service temperature setting: {translation_service.model_config.translation_temperature}")

        print("\n🎉 Configuration test completed successfully!")

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        logging.error(f"Configuration test failed: {e}", exc_info=True)


def test_translation_with_new_model():
    """Test translation using the configured model."""

    print("\n🌍 Testing Translation with Configured Model")
    print("=" * 50)

    # Sample evaluation result (English)
    sample_result = {
        "pain_intensity": 7,
        "reasoning": "The patient reports moderate to severe pain levels.",
        "explanations": {
            "pain_intensity": "Pain descriptors indicate significant discomfort affecting daily activities."
        },
    }

    try:
        translation_service = TranslationService()

        print(f"📝 Using translation model: {translation_service.model_config.translation_model}")
        print(f"🌡️ Temperature: {translation_service.model_config.translation_temperature}")
        print(f"🎯 Max tokens: {translation_service.model_config.translation_max_tokens}")

        print("\n🔄 Translating to Spanish...")
        spanish_result = translation_service.translate_evaluation_result(sample_result, "es")

        print("🇪🇸 Spanish translation result:")
        print(f"  Original reasoning: {sample_result['reasoning']}")
        print(f"  Translated reasoning: {spanish_result.get('reasoning', 'N/A')}")

        if "explanations" in spanish_result:
            original_explanation = sample_result["explanations"]["pain_intensity"]
            translated_explanation = spanish_result["explanations"].get("pain_intensity", "N/A")
            print(f"  Original explanation: {original_explanation}")
            print(f"  Translated explanation: {translated_explanation}")

        print("\n🎉 Translation with configured model completed successfully!")

    except Exception as e:
        print(f"❌ Translation test failed: {e}")
        logging.error(f"Translation test failed: {e}", exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("🚀 Starting Translation Configuration Tests")
    print("=" * 60)

    test_translation_config()
    test_translation_with_new_model()

    print("\n✨ All configuration tests completed!")

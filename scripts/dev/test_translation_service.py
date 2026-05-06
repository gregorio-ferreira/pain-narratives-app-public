"""
Test the translation service with GPT-5 models.
"""

import logging

from pain_narratives.core.translation_service import TranslationService


def test_translation_service():
    """Test the translation service with a sample evaluation result."""

    print("🌍 Testing Translation Service with GPT-5")
    print("=" * 50)

    try:
        # Create translation service
        service = TranslationService()

        # Sample evaluation result with English content
        english_result = {
            "explanation": "The patient describes chronic widespread pain lasting over 3 months, affecting multiple body regions including neck, shoulders, back, and legs. This pattern is consistent with fibromyalgia criteria.",
            "reasoning": "Based on the narrative, the patient exhibits key fibromyalgia indicators: widespread pain duration exceeding 3 months, involvement of multiple anatomical regions, and impact on daily functioning.",
            "scores": {"pain_intensity": 8, "functional_impact": 7, "duration_chronicity": 9},
            "dimensions": ["widespread_pain", "chronic_duration", "functional_limitation"],
        }

        print("📝 Original English result:")
        print(f"  Explanation: {english_result['explanation'][:100]}...")
        print(f"  Reasoning: {english_result['reasoning'][:100]}...")
        print(f"  Scores: {english_result['scores']}")

        # Test translation to Spanish
        print("\n🔄 Translating to Spanish...")
        spanish_result = service.translate_evaluation_result(english_result, target_language="es")

        print("✅ Spanish translation received:")
        print(f"  Explanation: {spanish_result.get('explanation', 'Missing')[:100]}...")
        print(f"  Reasoning: {spanish_result.get('reasoning', 'Missing')[:100]}...")
        print(f"  Scores: {spanish_result.get('scores', 'Missing')}")
        print(f"  Dimensions: {spanish_result.get('dimensions', 'Missing')}")

        # Test multilingual result structure
        print("\n📊 Creating multilingual result structure...")
        multilingual_result = {"en": english_result, "es": spanish_result}

        print("✅ Multilingual structure created:")
        print(f"  Languages available: {list(multilingual_result.keys())}")
        print(f"  English explanation length: {len(multilingual_result['en']['explanation'])}")
        print(f"  Spanish explanation length: {len(multilingual_result['es']['explanation'])}")

    except Exception as e:
        print(f"❌ Translation service test failed: {e}")
        logging.error(f"Translation service test failed: {e}", exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("🚀 Starting Translation Service Tests")
    print("=" * 60)

    test_translation_service()

    print("\n✨ Translation service tests completed!")

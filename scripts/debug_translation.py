"""
Debug the translation service to see what's happening with the explanation field.
"""

import json
import logging

from pain_narratives.core.translation_service import TranslationService


def debug_translation():
    """Debug translation process step by step."""
    
    print("🐛 Debugging Translation Service")
    print("=" * 50)
    
    service = TranslationService()
    
    # Sample evaluation result
    english_result = {
        "explanation": "The patient describes chronic widespread pain lasting over 3 months, affecting multiple body regions including neck, shoulders, back, and legs. This pattern is consistent with chronic pain criteria.",
        "reasoning": "Based on the narrative, the patient exhibits key chronic pain indicators: widespread pain duration exceeding 3 months, involvement of multiple anatomical regions, and impact on daily functioning.",
        "scores": {
            "pain_intensity": 8,
            "functional_impact": 7,
            "duration_chronicity": 9
        },
        "dimensions": [
            "widespread_pain",
            "chronic_duration", 
            "functional_limitation"
        ]
    }
    
    print("🔍 Step 1: Check what content is collected for translation")
    
    # Manually run the collection logic
    content_to_translate = {}
    
    # Always include reasoning if present
    if "reasoning" in english_result:
        content_to_translate["reasoning"] = english_result["reasoning"]
        print(f"  ✅ Added reasoning: {len(english_result['reasoning'])} chars")

    # Handle general explanation field
    if "explanation" in english_result:
        content_to_translate["explanation"] = english_result["explanation"]
        print(f"  ✅ Added explanation: {len(english_result['explanation'])} chars")

    # Handle different possible explanation structures
    if "explanations" in english_result:
        content_to_translate["explanations"] = english_result["explanations"]
        print(f"  ✅ Added explanations: {english_result['explanations']}")
    elif "dimension_explanations" in english_result:
        content_to_translate["dimension_explanations"] = english_result["dimension_explanations"]
        print(f"  ✅ Added dimension_explanations: {english_result['dimension_explanations']}")

    # Handle fields ending with _explanation
    for key, value in english_result.items():
        if key.endswith("_explanation") and isinstance(value, str):
            content_to_translate[key] = value
            print(f"  ✅ Added {key}: {len(value)} chars")
    
    print(f"\n📦 Content to translate: {list(content_to_translate.keys())}")
    
    # Create translation prompt manually
    language_names = {"es": "Spanish", "en": "English", "fr": "French", "de": "German", "it": "Italian"}
    target_language_name = language_names.get("es", "es")
    
    translation_content = json.dumps(content_to_translate, indent=2)
    
    translation_prompt = f"""
Please translate the following medical evaluation content from English to {target_language_name}.
Maintain the same JSON structure and keys. Only translate the text values, not the keys.
Preserve medical terminology accuracy.

Content to translate:
{translation_content}

Return the translated explanations in the same JSON format, with the same keys but translated values.
"""
    
    print(f"\n📝 Translation prompt preview:")
    print(translation_prompt[:300] + "..." if len(translation_prompt) > 300 else translation_prompt)
    
    # Now try the actual translation
    print(f"\n🔄 Running actual translation...")
    try:
        spanish_result = service.translate_evaluation_result(english_result, target_language="es")
        
        print("\n✅ Translation completed!")
        print(f"  Original explanation: '{english_result['explanation'][:100]}...'")
        print(f"  Translated explanation: '{spanish_result.get('explanation', 'MISSING')[:100]}...'")
        print(f"  Original reasoning: '{english_result['reasoning'][:100]}...'")  
        print(f"  Translated reasoning: '{spanish_result.get('reasoning', 'MISSING')[:100]}...'")
        
        # Check if they're actually different
        if english_result['explanation'] == spanish_result.get('explanation'):
            print("  ⚠️  WARNING: Explanation was not translated!")
        else:
            print("  ✅ Explanation was successfully translated!")
            
        if english_result['reasoning'] == spanish_result.get('reasoning'):
            print("  ⚠️  WARNING: Reasoning was not translated!")
        else:
            print("  ✅ Reasoning was successfully translated!")
            
    except Exception as e:
        print(f"❌ Translation failed: {e}")
        logging.error(f"Translation failed: {e}", exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    debug_translation()
"""
Quick test to verify multilingual evaluation display functionality.
"""

def test_multilingual_result_structure():
    """Test the expected multilingual result structure."""
    
    # This is what should be in session state after translation
    multilingual_result = {
        "en": {
            "disability_score": 8,
            "disability_score_explanation": "The narrative describes long-standing, worsening pain...",
            "reasoning": "The scores emphasize high but not maximal disability..."
        },
        "es": {
            "disability_score": 8,
            "disability_score_explanation": "La narrativa describe dolor persistente y crónico...",
            "reasoning": "Las puntuaciones enfatizan una discapacidad alta pero no máxima..."
        }
    }
    
    # Test the translation service functionality
    from pain_narratives.core.translation_service import TranslationService
    
    service = TranslationService()
    
    # Test getting Spanish version
    spanish_result = service.get_available_translation(multilingual_result, "es")
    print("Spanish result reasoning:", spanish_result.get("reasoning", "Missing")[:50] + "...")
    
    # Test getting English fallback
    english_result = service.get_available_translation(multilingual_result, "en")
    print("English result reasoning:", english_result.get("reasoning", "Missing")[:50] + "...")
    
    # Test fallback to English for unsupported language
    french_result = service.get_available_translation(multilingual_result, "fr")
    print("French fallback reasoning:", french_result.get("reasoning", "Missing")[:50] + "...")
    
    print("\n✅ Multilingual structure test completed!")

if __name__ == "__main__":
    test_multilingual_result_structure()
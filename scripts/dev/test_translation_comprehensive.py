"""
Comprehensive test of translation service with both questionnaire and assessment result types.
"""

import logging

from pain_narratives.core.translation_service import TranslationService


def test_questionnaire_translation():
    """Test translation of questionnaire results (with model_reasoning)."""
    
    print("📋 Testing Questionnaire Translation")
    print("=" * 50)
    
    # Sample questionnaire result from database
    questionnaire_result = {
        "scores": {
            "1": 3, "2": 2, "3": 2, "4": 2, "5": 3, "6": 2,
            "7": 1, "8": 3, "9": 3, "10": 3, "11": 3, "12": 2, "13": 2
        },
        "model_reasoning": "Based on the pain narrative, the individual describes a persistent, multi-faceted pain that has lasted for years and has significantly impacted their daily life and emotional wellbeing. The person demonstrates ongoing worry about the pain, difficulty in tolerating it, and distress over not being able to control or alleviate it effectively. The pain seems to dominate their thoughts and feelings, especially with mentions of sleepless nights, fatigue, and social isolation due to shame.",
        "prompt": "**Instructions:**\n\n1. Carefully read the pain narrative below..."
    }
    
    print("📝 Original questionnaire result:")
    print(f"  Scores: {questionnaire_result['scores']}")
    print(f"  Model reasoning: {questionnaire_result['model_reasoning'][:100]}...")
    print(f"  Has prompt: {'prompt' in questionnaire_result}")
    
    # Test translation
    service = TranslationService()
    
    try:
        print("\n🔄 Translating questionnaire to Spanish...")
        spanish_result = service.translate_evaluation_result(questionnaire_result, target_language="es")
        
        print("✅ Spanish translation received:")
        print(f"  Scores (unchanged): {spanish_result.get('scores', 'Missing')}")
        print(f"  Model reasoning: {spanish_result.get('model_reasoning', 'Missing')[:100]}...")
        
        # Check if translation occurred
        if (questionnaire_result['model_reasoning'] != spanish_result.get('model_reasoning')):
            print("  ✅ Model reasoning was successfully translated!")
        else:
            print("  ⚠️  WARNING: Model reasoning was not translated!")
            
        return spanish_result
        
    except Exception as e:
        print(f"❌ Questionnaire translation failed: {e}")
        return None


def test_assessment_translation():
    """Test translation of assessment results (with multiple _explanation fields)."""
    
    print("\n🏥 Testing Assessment Translation")
    print("=" * 50)
    
    # Sample assessment result from database
    assessment_result = {
        "severity_score": 5,
        "severity_score_explanation": "The patient describes persistent and worsening pain over many years, characterized by a diffuse, uncomfortable sensation that fluctuates and has become more intense and pervasive. They mention ongoing pain that has affected their quality of life, fatigue, and emotional distress, indicating a high perceived intensity of suffering.",
        "disability_score": 3, 
        "disability_score_explanation": "The narrative indicates significant functional limitations: difficulty in standing up due to pain, fatigue, and emotional burdens such as social withdrawal and feelings of shame. These factors suggest a high level of interference with daily activities and social life, warranting the maximum disability score.",
        "special_needs": 5,
        "special_needs_explanation": "The patient explicitly expresses a desire to learn how to better manage and channel their pain, indicating a need for specific psychological support, pain management strategies, and emotional assistance. While not requesting extensive accommodations, there is a clear need for tailored therapeutic interventions to help cope with the pain and improve quality of life.",
        "reasoning": "Overall, the patient presents with chronic, pervasive pain leading to substantial physical and emotional disability. Despite some coping efforts, the ongoing severity and impact on their personal and social functioning justify high scores across all dimensions. The narrative reflects a complex, long-standing experience of fibromyalgia symptoms with expressed needs for support and management strategies."
    }
    
    print("📝 Original assessment result:")
    print(f"  Severity score: {assessment_result['severity_score']}")
    print(f"  Severity explanation: {assessment_result['severity_score_explanation'][:100]}...")
    print(f"  Disability explanation: {assessment_result['disability_score_explanation'][:100]}...")
    print(f"  Special needs explanation: {assessment_result['special_needs_explanation'][:100]}...")
    print(f"  Reasoning: {assessment_result['reasoning'][:100]}...")
    
    # Test translation
    service = TranslationService()
    
    try:
        print("\n🔄 Translating assessment to Spanish...")
        spanish_result = service.translate_evaluation_result(assessment_result, target_language="es")
        
        print("✅ Spanish translation received:")
        print(f"  Severity score (unchanged): {spanish_result.get('severity_score', 'Missing')}")
        print(f"  Severity explanation: {spanish_result.get('severity_score_explanation', 'Missing')[:100]}...")
        print(f"  Disability explanation: {spanish_result.get('disability_score_explanation', 'Missing')[:100]}...")
        print(f"  Special needs explanation: {spanish_result.get('special_needs_explanation', 'Missing')[:100]}...")
        print(f"  Reasoning: {spanish_result.get('reasoning', 'Missing')[:100]}...")
        
        # Check if translations occurred
        translation_checks = [
            ("severity_score_explanation", "Severity explanation"),
            ("disability_score_explanation", "Disability explanation"), 
            ("special_needs_explanation", "Special needs explanation"),
            ("reasoning", "Reasoning")
        ]
        
        for field, name in translation_checks:
            if (assessment_result[field] != spanish_result.get(field)):
                print(f"  ✅ {name} was successfully translated!")
            else:
                print(f"  ⚠️  WARNING: {name} was not translated!")
                
        return spanish_result
        
    except Exception as e:
        print(f"❌ Assessment translation failed: {e}")
        return None


def test_multilingual_structure():
    """Test creating complete multilingual structure."""
    
    print("\n🌍 Testing Multilingual Structure Creation")
    print("=" * 50)
    
    # Simulate complete database structure
    assessment_en = {
        "severity_score": 5,
        "severity_score_explanation": "The patient describes persistent and worsening pain over many years.",
        "disability_score": 3,
        "disability_score_explanation": "The narrative indicates significant functional limitations.",
        "special_needs": 5,
        "special_needs_explanation": "The patient explicitly expresses a desire to learn pain management.",
        "reasoning": "Overall, the patient presents with chronic, pervasive pain."
    }
    
    service = TranslationService()
    
    try:
        # Translate to Spanish
        assessment_es = service.translate_evaluation_result(assessment_en, target_language="es")
        
        # Create multilingual structure
        multilingual_result = {
            "en": assessment_en,
            "es": assessment_es
        }
        
        print("✅ Multilingual structure created:")
        print(f"  Languages available: {list(multilingual_result.keys())}")
        
        # Test fallback functionality
        print("\n🔄 Testing fallback functionality...")
        
        # Test preferred language retrieval
        spanish_fallback = service.get_available_translation(multilingual_result, "es")
        english_fallback = service.get_available_translation(multilingual_result, "en")
        missing_fallback = service.get_available_translation(multilingual_result, "fr")  # Should fallback to English
        
        print(f"  Spanish retrieval: {'✅ Success' if spanish_fallback else '❌ Failed'}")
        print(f"  English retrieval: {'✅ Success' if english_fallback else '❌ Failed'}")
        print(f"  French fallback to English: {'✅ Success' if missing_fallback else '❌ Failed'}")
        
        return multilingual_result
        
    except Exception as e:
        print(f"❌ Multilingual structure test failed: {e}")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 Starting Comprehensive Translation Tests")
    print("=" * 60)
    
    # Test both result types
    questionnaire_spanish = test_questionnaire_translation()
    assessment_spanish = test_assessment_translation()
    multilingual_result = test_multilingual_structure()
    
    print("\n✨ All comprehensive translation tests completed!")
    
    # Summary
    print("\n📊 Test Summary:")
    print(f"  Questionnaire translation: {'✅ Success' if questionnaire_spanish else '❌ Failed'}")
    print(f"  Assessment translation: {'✅ Success' if assessment_spanish else '❌ Failed'}")
    print(f"  Multilingual structure: {'✅ Success' if multilingual_result else '❌ Failed'}")    print(f"  Multilingual structure: {'✅ Success' if multilingual_result else '❌ Failed'}")
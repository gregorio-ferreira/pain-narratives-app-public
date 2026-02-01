"""
Test script to verify all localization keys are present in both language files.
"""

from pathlib import Path

import yaml


def check_translation_keys():
    """Check if all required translation keys exist in both language files."""
    
    # Load both language files
    en_path = Path("src/pain_narratives/locales/en.yml")
    es_path = Path("src/pain_narratives/locales/es.yml")
    
    with open(en_path, 'r', encoding='utf-8') as f:
        en_data = yaml.safe_load(f)
    
    with open(es_path, 'r', encoding='utf-8') as f:
        es_data = yaml.safe_load(f)
    
    # Required keys we just added
    required_keys = [
        "ui_text.dimensions_updated_success",
        "ui_text.database_update_failed_local_saved", 
        "ui_text.error_updating_group",
        "ui_text.translating_result",
        "ui_text.translation_completed_success",
        "ui_text.translation_failed_english_only"
    ]
    
    print("🔍 Checking Translation Keys")
    print("=" * 40)
    
    all_good = True
    
    for key in required_keys:
        # Navigate nested keys
        key_parts = key.split('.')
        
        # Check English
        en_value = en_data
        es_value = es_data
        
        try:
            for part in key_parts:
                en_value = en_value[part]
                es_value = es_value[part]
            
            print(f"✅ {key}")
            print(f"   EN: {en_value}")
            print(f"   ES: {es_value}")
            print()
            
        except KeyError as e:
            print(f"❌ {key} - Missing key: {e}")
            all_good = False
    
    if all_good:
        print("🎉 All translation keys are present and ready!")
    else:
        print("⚠️  Some translation keys are missing.")
    
    return all_good

if __name__ == "__main__":
    check_translation_keys()
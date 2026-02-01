"""
Test script to verify the new YAML-based prompts configuration system.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pain_narratives.config.prompts import (
    get_base_prompt,
    get_default_dimensions,
    get_default_prompt,
    get_prompt_library,
    get_questionnaire_prompt,
    get_questionnaire_prompts,
    get_system_role,
)


def test_narrative_evaluation_config():
    """Test narrative evaluation configuration loading."""
    print("=" * 80)
    print("Testing Narrative Evaluation Configuration")
    print("=" * 80)
    
    system_role = get_system_role()
    print(f"\n✓ System Role loaded ({len(system_role)} chars)")
    print(f"  Preview: {system_role[:100]}...")
    
    base_prompt = get_base_prompt()
    print(f"\n✓ Base Prompt loaded ({len(base_prompt)} chars)")
    print(f"  Preview: {base_prompt[:100]}...")
    
    dimensions = get_default_dimensions()
    print(f"\n✓ Default Dimensions loaded ({len(dimensions)} dimensions)")
    for idx, dim in enumerate(dimensions, 1):
        print(f"  {idx}. {dim['name']} ({dim['min']}-{dim['max']}) - Active: {dim.get('active', True)}")
    
    full_prompt = get_default_prompt()
    print(f"\n✓ Full Default Prompt generated ({len(full_prompt)} chars)")
    
    return True


def test_questionnaire_prompts():
    """Test questionnaire prompts loading."""
    print("\n" + "=" * 80)
    print("Testing Questionnaire Prompts Configuration")
    print("=" * 80)
    
    all_prompts = get_questionnaire_prompts()
    print(f"\n✓ Questionnaire prompts loaded ({len(all_prompts)} types)")
    
    for q_type in ["PCS", "BPI-IS", "TSK-11SV"]:
        prompt = get_questionnaire_prompt(q_type)
        if prompt:
            print(f"\n  {q_type}:")
            print(f"    System Role: {len(prompt['system_role'])} chars")
            print(f"    Instructions: {len(prompt['instructions'])} chars")
        else:
            print(f"\n  ✗ {q_type}: Not found!")
            return False
    
    return True


def test_prompt_library():
    """Test prompt library loading."""
    print("\n" + "=" * 80)
    print("Testing Prompt Library Configuration")
    print("=" * 80)
    
    library = get_prompt_library()
    print(f"\n✓ Prompt library loaded ({len(library)} templates)")
    
    for template_id, template in library.items():
        print(f"\n  {template_id}:")
        print(f"    Name: {template['name']}")
        print(f"    Category: {template['category']}")
        print(f"    Template: {len(template['template'])} chars")
    
    return True


def test_spanish_dimensions():
    """Test that Spanish dimensions from experiment group 12 are loaded correctly."""
    print("\n" + "=" * 80)
    print("Testing Experiment Group 12 Spanish Dimensions")
    print("=" * 80)
    
    dimensions = get_default_dimensions()
    
    # Check for Spanish dimension names
    expected_names = ["Severidad del dolor", "Discapacidad"]
    actual_names = [dim['name'] for dim in dimensions if dim.get('active', True)]
    
    print(f"\n  Expected dimensions: {expected_names}")
    print(f"  Actual dimensions: {actual_names}")
    
    if set(expected_names) == set(actual_names):
        print("\n✓ Spanish dimensions from experiment group 12 loaded correctly!")
        return True
    else:
        print("\n✗ Dimension names don't match expected values from experiment group 12")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("YAML-BASED PROMPTS CONFIGURATION TEST")
    print("=" * 80)
    
    tests = [
        ("Narrative Evaluation Config", test_narrative_evaluation_config),
        ("Questionnaire Prompts", test_questionnaire_prompts),
        ("Prompt Library", test_prompt_library),
        ("Spanish Dimensions (Group 12)", test_spanish_dimensions),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} FAILED with error:")
            print(f"  {type(e).__name__}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✓ All tests passed! YAML configuration system is working correctly.")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

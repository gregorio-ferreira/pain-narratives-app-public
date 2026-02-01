#!/usr/bin/env python3
"""
Integration test script to verify the centralized configuration system works properly.
"""


def test_configuration():
    """Test that configuration loads correctly."""
    try:
        from pain_narratives.config.settings import get_settings

        settings = get_settings()

        print("✅ Configuration loaded successfully")
        print(f"  - Database URL: {settings.database_url[:50]}...")
        print(f"  - OpenAI API key configured: {bool(settings.openai_api_key)}")
        print(f"  - Default model: {settings.model_config.default_model}")
        print(f"  - Database host: {settings.pg_config.host}")
        assert True
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        assert False, f"Configuration loading failed: {e}"


def test_database():
    """Test database connectivity."""
    try:
        from pain_narratives.core.database import DatabaseManager

        db_manager = DatabaseManager()
        engine = db_manager.engine

        print("✅ Database connection successful")
        print(f"  - Database engine type: {type(engine)}")
        assert True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        assert False, f"Database connection failed: {e}"


def test_openai_client():
    """Test OpenAI client initialization."""
    try:
        from pain_narratives.core.openai_client import OpenAIClient

        openai_client = OpenAIClient()

        print("✅ OpenAI client initialized successfully")
        print(f"  - API key configured: {bool(openai_client._api_key)}")
        print(f"  - Organization ID configured: {bool(openai_client._org_id)}")
        assert True
    except Exception as e:
        print(f"❌ OpenAI client initialization failed: {e}")
        assert False, f"OpenAI client initialization failed: {e}"


def main() -> None:
    """Run all integration tests."""
    print("=== Comprehensive Integration Test ===")
    print("Testing centralized configuration system...\n")

    tests = [
        ("Configuration Loading", test_configuration),
        ("Database Connection", test_database),
        ("OpenAI Client", test_openai_client),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n--- Testing {test_name} ---")
        success = test_func()
        results.append(success)

    print("\n=== Test Results ===")
    if all(results):
        print("🎉 All tests passed! Centralized configuration system is working correctly.")
        print("✅ Configuration loading: PASS")
        print("✅ Database connectivity: PASS")
        print("✅ OpenAI client initialization: PASS")
        print("\n🔧 The pain narratives project is now using a unified configuration approach!")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        for i, (test_name, _) in enumerate(tests):
            status = "PASS" if results[i] else "FAIL"
            print(f"  {test_name}: {status}")


if __name__ == "__main__":
    main()

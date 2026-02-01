#!/usr/bin/env python3
"""
Verification script to test all imports used in the Streamlit app.
"""

import sys


def test_imports():
    """Test all critical imports used in the Streamlit app."""
    try:  # Core imports
        from pain_narratives.config.settings import get_settings  # noqa: F401

        print("✅ pain_narratives.config.settings")

        from pain_narratives.core.database import DatabaseManager  # noqa: F401

        print("✅ pain_narratives.core.database")

        from pain_narratives.core.openai_client import OpenAIClient  # noqa: F401

        print("✅ pain_narratives.core.openai_client")

        from pain_narratives.core.analytics import (  # noqa: F401
            calculate_kappa,
            calculate_mean_absolute_error,
            calculate_rmse,
            evaluate_agreement_metrics,
        )

        print("✅ pain_narratives.core.analytics")

        # App component imports
        from pain_narratives.ui.components.evaluation_logic import NarrativeEvaluator  # noqa: F401

        print("✅ pain_narratives.ui.components.evaluation_logic")

        from pain_narratives.ui.components.batch_processing import run_batch_evaluation  # noqa: F401

        print("✅ pain_narratives.ui.components.batch_processing")

        from pain_narratives.ui.components.prompt_manager import (  # noqa: F401,E501
            get_current_prompt,
            prompt_customization_ui,
        )

        print("✅ pain_narratives.ui.components.prompt_manager")

        print("\n🎉 All imports successful! The Streamlit app should work correctly.")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)

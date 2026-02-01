"""
Quick fix script to clear Streamlit session state and force prompt regeneration.
Run this by refreshing your browser page.
"""

import streamlit as st


# Clear all prompt-related session state
def clear_prompt_cache():
    keys_to_clear = [
        "current_prompt",
        "selected_group_dimensions",
        "selected_group_system_role",
        "selected_group_base_prompt",
        "custom_dimensions",
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    st.success("✅ Prompt cache cleared! Please go to Prompt Studio and click 'Dimensions Definition Ready' again.")


if __name__ == "__main__":
    st.title("🔧 Fix Prompt Formatting Issue")
    st.write("This will clear cached prompts and force regeneration with the fixed format.")

    if st.button("Clear Prompt Cache"):
        clear_prompt_cache()

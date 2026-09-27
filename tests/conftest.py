"""
Shared pytest setup
--------------------
registration.py / log_an_action.py are Streamlit scripts (top-level
UI code runs on import, not gated behind a function or __main__
check) - that's normal for how Streamlit apps work, but it means
importing them outside a real Streamlit runtime prints a lot of
"missing ScriptRunContext" noise. Harmless (Streamlit's own message
says so), just noisy - quieted here so test output stays readable.
"""

import logging

logging.getLogger("streamlit").setLevel(logging.ERROR)

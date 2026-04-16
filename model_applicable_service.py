"""
Canonical provider-agnostic service module for Legal AI.

This file is the neutral import surface for the multi-provider backend. It
re-exports the existing implementation from `gemini_service.py` so the app can
use a provider-agnostic module name while older imports continue to work.
It is provider-agnostic, not provider-free: generation still depends on the
configured model/provider implementation re-exported here.
"""

import gemini_service as _gemini_service
from gemini_service import *  # noqa: F401,F403

# Explicitly forward underscore-prefixed helpers that are imported directly by
# the Streamlit app. Star-import does not re-export these names.
_is_problem_final_conclusion_title = _gemini_service._is_problem_final_conclusion_title
_is_problem_remedies_liability_title = _gemini_service._is_problem_remedies_liability_title

def __getattr__(name):
    return getattr(_gemini_service, name)

def __dir__():
    return sorted(set(globals()) | set(dir(_gemini_service)))

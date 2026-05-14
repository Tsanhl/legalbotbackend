"""
Short neutral import alias for the Legal AI backend service layer.

This keeps `service.py` available as the simplest import name while preserving
the existing provider-agnostic surface in `model_applicable_service.py`.
"""

import model_applicable_service as _service_module
from model_applicable_service import *  # noqa: F401,F403

# Explicitly forward underscore-prefixed helpers that some local callers import
# directly. Star-import does not re-export these names by default.
_is_problem_final_conclusion_title = _service_module._is_problem_final_conclusion_title
_is_problem_remedies_liability_title = _service_module._is_problem_remedies_liability_title


def __getattr__(name):
    return getattr(_service_module, name)


def __dir__():
    return sorted(set(globals()) | set(dir(_service_module)))

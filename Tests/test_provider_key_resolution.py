import os

from gemini_service import get_env_api_key_for_provider, is_placeholder_api_key, resolve_provider_api_key


assert is_placeholder_api_key("your_gemini_api_key_here") is True
assert is_placeholder_api_key("placeholder") is True
assert is_placeholder_api_key("AIzaRealLookingKey") is False

original_gemini = os.environ.get("GEMINI_API_KEY")
try:
    os.environ["GEMINI_API_KEY"] = "your_gemini_api_key_here"
    assert get_env_api_key_for_provider("gemini") == ""
    assert resolve_provider_api_key("gemini", "") == ""

    os.environ["GEMINI_API_KEY"] = "AIzaRealLookingKey"
    assert get_env_api_key_for_provider("gemini") == "AIzaRealLookingKey"
    assert resolve_provider_api_key("gemini", "") == "AIzaRealLookingKey"
finally:
    if original_gemini is None:
        os.environ.pop("GEMINI_API_KEY", None)
    else:
        os.environ["GEMINI_API_KEY"] = original_gemini

print("Provider key resolution checks passed.")

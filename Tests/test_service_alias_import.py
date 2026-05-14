"""
Regression check for the short neutral `service.py` import alias.
"""

import service


def run() -> None:
    assert hasattr(service, "_infer_retrieval_profile")
    profile = service._infer_retrieval_profile("Write a complete answer on company law.")
    assert profile.get("topic") == "company_directors_minorities", profile
    assert callable(service.send_message_with_docs)
    print("Service alias import regression passed.")


if __name__ == "__main__":
    run()

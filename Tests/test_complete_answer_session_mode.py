"""
Regression checks for complete-answer session acceptance cleanup.
"""

import tempfile
from pathlib import Path

from model_applicable_service import (
    detect_complete_answer_session_signal,
    register_complete_answer_cleanup_paths,
    send_message_with_docs,
)


history = [
    {"role": "user", "text": "Write a complete answer to this public law essay question in 2000 words."},
    {"role": "assistant", "text": "Part I: Introduction\n\nPart II: Analysis\n\nPart III: Conclusion"},
]

accept_signal = detect_complete_answer_session_signal(
    "done, accept the answer",
    history,
    active=True,
)
assert accept_signal["is_acceptance"] is True

delivery_accept_signal = detect_complete_answer_session_signal(
    "accept the delivery",
    history,
    active=True,
)
assert delivery_accept_signal["is_acceptance"] is True

done_signal = detect_complete_answer_session_signal(
    "done",
    history,
    active=True,
)
assert done_signal["is_acceptance"] is True

runtime_dir = Path(".codex_runtime")
runtime_dir.mkdir(exist_ok=True)

with tempfile.TemporaryDirectory() as tmp_dir:
    root = Path(tmp_dir)
    helper_dir = root / "task_specific_answer_helper_dir"
    helper_dir.mkdir()
    helper_file = helper_dir / "draft.json"
    helper_file.write_text("{}", encoding="utf-8")

    runtime_hint = runtime_dir / "complete_answer_task_specific_acceptance_test.txt"
    runtime_hint.write_text("temp answer helper", encoding="utf-8")

    project_id = "complete_answer_acceptance_cleanup_test"
    register_complete_answer_cleanup_paths(project_id, [helper_dir])

    (accept_text, _accept_meta), _accept_rag = send_message_with_docs(
        api_key="",
        message="accept the delivery",
        documents=[],
        project_id=project_id,
        history=history,
        stream=False,
    )

    assert "complete-answer session and temporary answer artifacts have been cleared" in accept_text
    assert not helper_dir.exists()
    assert not runtime_hint.exists()

print("Complete-answer session cleanup checks passed.")

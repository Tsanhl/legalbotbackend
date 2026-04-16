"""
Regression checks for one-off amend cleanup targets.
"""

import tempfile
from pathlib import Path

from legal_doc_tools.amend_docx import (
    ONE_OFF_TEMP_DIRS,
    _cleanup_one_off_artifacts_after_amend,
    _collect_one_off_cleanup_targets,
)


with tempfile.TemporaryDirectory() as tmp_dir:
    root = Path(tmp_dir)
    config_path = root / "config.json"
    question_path = root / "question.txt"
    rubric_path = root / "rubric.txt"
    context_path = root / "context.txt"
    instruction_path = root / "doc_specific_instructions.txt"
    prompt_path = root / "doc_specific_prompt.txt"
    helper_test_path = root / "doc_specific_helper_test.py"
    helper_dir = root / "helper_code"
    helper_dir.mkdir()
    helper_file = helper_dir / "helper.py"

    for path in [
        config_path,
        question_path,
        rubric_path,
        context_path,
        instruction_path,
        prompt_path,
        helper_test_path,
        helper_file,
    ]:
        path.write_text("temp", encoding="utf-8")

    config = {
        "one_off_instruction_path": str(instruction_path),
        "one_off_prompt_paths": [str(prompt_path)],
        "one_off_helper_test_paths": [str(helper_test_path)],
        "one_off_helper_code_paths": [str(helper_dir)],
        "cleanup_paths": [],
    }

    targets = _collect_one_off_cleanup_targets(
        config=config,
        config_path=config_path,
        question_path=question_path,
        rubric_path=rubric_path,
        context_out_path=context_path,
    )
    target_set = set(targets)
    assert instruction_path.resolve() in target_set
    assert prompt_path.resolve() in target_set
    assert helper_test_path.resolve() in target_set
    assert helper_dir.resolve() in target_set

    original_one_off_dirs = set(ONE_OFF_TEMP_DIRS)
    try:
        import legal_doc_tools.amend_docx as amend_docx

        amend_docx.ONE_OFF_TEMP_DIRS = {root.parent / "unrelated-temp-root"}
        removed = _cleanup_one_off_artifacts_after_amend(
            config=config,
            config_path=config_path,
            question_path=question_path,
            rubric_path=rubric_path,
            context_out_path=context_path,
        )
    finally:
        amend_docx.ONE_OFF_TEMP_DIRS = original_one_off_dirs

    assert removed >= 4
    assert not instruction_path.exists()
    assert not prompt_path.exists()
    assert not helper_test_path.exists()
    assert not helper_dir.exists()

print("One-off cleanup regression passed.")

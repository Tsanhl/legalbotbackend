"""
Regression checks for temporary amend task-artifact cleanup targets.
"""

import tempfile
from pathlib import Path

import legal_doc_tools.amend_docx as amend_docx
from legal_doc_tools.amend_docx import (
    TEMP_TASK_ARTIFACT_DIRS,
    _cleanup_task_artifacts_after_amend,
    _collect_task_artifact_cleanup_targets,
)


with tempfile.TemporaryDirectory() as tmp_dir:
    root = Path(tmp_dir)
    config_path = root / "doc_specific_config.json"
    question_path = root / "question.txt"
    rubric_path = root / "rubric.txt"
    context_path = root / "context_notes.md"
    instruction_path = root / "doc_specific_instructions.txt"
    prompt_path = root / "doc_specific_prompt.txt"
    helper_test_path = root / "doc_specific_helper_test.py"
    helper_dir = root / "helper_code"
    helper_dir.mkdir()
    helper_file = helper_dir / "helper.py"
    unrelated_readme = root / "README.md"

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
    unrelated_readme.write_text("keep me", encoding="utf-8")

    config = {
        "task_specific_instruction_path": str(instruction_path),
        "task_specific_prompt_paths": [str(prompt_path)],
        "task_specific_helper_test_paths": [str(helper_test_path)],
        "task_specific_helper_code_paths": [str(helper_dir)],
        "cleanup_paths": [],
    }

    original_temp_dirs = set(TEMP_TASK_ARTIFACT_DIRS)
    original_project_root = amend_docx.PROJECT_ROOT
    try:
        amend_docx.PROJECT_ROOT = root
        targets = _collect_task_artifact_cleanup_targets(
            config=config,
            config_path=config_path,
            question_path=question_path,
            rubric_path=rubric_path,
            context_out_path=context_path,
        )
        target_set = {path.expanduser().resolve() for path in targets}
        assert instruction_path.expanduser().resolve() in target_set
        assert prompt_path.expanduser().resolve() in target_set
        assert helper_test_path.expanduser().resolve() in target_set
        assert helper_dir.expanduser().resolve() in target_set
        assert config_path.expanduser().resolve() in target_set
        assert question_path.expanduser().resolve() in target_set
        assert rubric_path.expanduser().resolve() in target_set
        assert context_path.expanduser().resolve() in target_set

        amend_docx.TEMP_TASK_ARTIFACT_DIRS = {root.parent / "unrelated-temp-root"}
        removed = _cleanup_task_artifacts_after_amend(
            config=config,
            config_path=config_path,
            question_path=question_path,
            rubric_path=rubric_path,
            context_out_path=context_path,
        )
    finally:
        amend_docx.TEMP_TASK_ARTIFACT_DIRS = original_temp_dirs
        amend_docx.PROJECT_ROOT = original_project_root

    assert removed >= 8
    assert not config_path.exists()
    assert not question_path.exists()
    assert not rubric_path.exists()
    assert not context_path.exists()
    assert not instruction_path.exists()
    assert not prompt_path.exists()
    assert not helper_test_path.exists()
    assert not helper_dir.exists()
    assert unrelated_readme.exists()

print("Task-artifact cleanup regression passed.")

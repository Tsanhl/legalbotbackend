"""
Regression checks for single-canonical DOCX output policy.
"""

from pathlib import Path
import tempfile

from legal_doc_tools import amend_docx
from legal_doc_tools import refine_docx_from_amended as refine


with tempfile.TemporaryDirectory() as tmp:
    desktop = Path(tmp)
    original_desktop = refine.DESKTOP_ROOT
    refine.DESKTOP_ROOT = desktop
    try:
        source = desktop / "essay.docx"
        expected = desktop / "essay_amended_marked_final.docx"
        expected.write_bytes(b"canonical")
        (desktop / "essay_amended_marked_final_v2.docx").write_bytes(b"v2")
        (desktop / "essay_amended_marked_final_v3.docx").write_bytes(b"v3")

        output, normalized = refine._normalize_to_final_output_path(source, None)
        assert output == expected
        assert normalized is False

        requested = desktop / "custom_name.docx"
        output, normalized = refine._normalize_to_final_output_path(source, requested)
        assert output == expected
        assert normalized is True

        removed = refine._prune_output_versions(expected)
        assert removed == 2
        assert expected.exists()
        assert not (desktop / "essay_amended_marked_final_v2.docx").exists()
        assert not (desktop / "essay_amended_marked_final_v3.docx").exists()

        (desktop / "essay_amended_marked_final_v4.docx").write_bytes(b"v4")
        removed = amend_docx._prune_output_versions(expected)
        assert removed == 1
        assert not (desktop / "essay_amended_marked_final_v4.docx").exists()
    finally:
        refine.DESKTOP_ROOT = original_desktop


print("Output path policy checks passed.")

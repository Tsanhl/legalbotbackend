"""
Regression checks for protected versioned DOCX output policy.
"""

from pathlib import Path
import tempfile

from legal_doc_tools import refine_docx_from_amended as refine


with tempfile.TemporaryDirectory() as tmp:
    desktop = Path(tmp)
    original_desktop = refine.DESKTOP_ROOT
    refine.DESKTOP_ROOT = desktop
    try:
        source = desktop / "essay.docx"
        canonical = desktop / "essay_amended_marked_final.docx"
        expected_v2 = desktop / "essay_amended_marked_final_v2.docx"
        canonical.write_bytes(b"canonical")
        (desktop / "essay_amended_marked_final_v2.docx").write_bytes(b"v2")
        (desktop / "essay_amended_marked_final_v3.docx").write_bytes(b"v3")

        output, normalized = refine._normalize_to_final_output_path(source, None)
        assert output == desktop / "essay_amended_marked_final_v4.docx"
        assert normalized is False

        requested = desktop / "custom_name.docx"
        output, normalized = refine._normalize_to_final_output_path(source, requested)
        assert output == desktop / "essay_amended_marked_final_v4.docx"
        assert normalized is True

        fresh_source = desktop / "fresh.docx"
        fresh_output, fresh_normalized = refine._normalize_to_final_output_path(fresh_source, None)
        assert fresh_output == desktop / "fresh_amended_marked_final.docx"
        assert fresh_normalized is False

        removed = refine._prune_output_versions(expected_v2)
        assert removed == 0
        assert canonical.exists()
        assert (desktop / "essay_amended_marked_final_v2.docx").exists()
        assert (desktop / "essay_amended_marked_final_v3.docx").exists()

        removed = refine._prune_output_versions(expected_v2)
        assert removed == 0
        assert (desktop / "essay_amended_marked_final_v2.docx").exists()
    finally:
        refine.DESKTOP_ROOT = original_desktop


print("Output path policy checks passed.")

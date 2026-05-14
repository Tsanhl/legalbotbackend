"""
Regression checks for explicit Harvard citation-mode support.
"""

from pathlib import Path

import model_applicable_service as gemini
import legal_doc_tools.workflow as workflow


assert gemini._detect_requested_citation_style("Use Harvard referencing with a references list.") == "harvard"
assert gemini._detect_requested_citation_style("Use APA 7 referencing.") == "apa"
assert gemini._detect_requested_citation_style("Use Vancouver referencing.") == "vancouver"
assert gemini._detect_requested_citation_style("Use OSCOLA only.") == "oscola"

harvard_block = gemini._build_active_citation_style_reminder("harvard")
assert "HARVARD AUTHOR-DATE STYLE" in harvard_block
assert "Standard Harvard is not a footnote citation system" in harvard_block
assert "References" in harvard_block
assert "OSCOLA FORMAT TEMPLATES" not in harvard_block

reference_block = gemini._build_requested_reference_section_block("harvard")
assert "REFERENCE LIST REQUEST ACTIVE" in reference_block
assert "`References` section" in reference_block

apa_block = gemini._build_active_citation_style_reminder("apa")
assert "REQUESTED CITATION STYLE — STRICT" in apa_block
assert "APA 7" in apa_block
assert "overrides the default OSCOLA setting" in apa_block

good_harvard_essay = """
Part I: Introduction
Savings adequacy remains uneven across the population, and a coherent answer requires both structural reform and clearer public communication (Smith, 2024).

Part II: Reform Analysis
Smith (2024) argues that households save more consistently when pension communication is joined to short-term resilience tools.

Part III: Conclusion
The better view is that policy should combine long-term pension nudges with short-term savings support rather than treating them as separate behavioural problems.

References
Smith, J. (2024) Title of report. Publisher.
""".strip()
assert gemini.detect_essay_core_policy_violation(
    good_harvard_essay,
    allow_reference_section=True,
    citation_style="harvard",
)[0] is False

captured: dict[str, list[str]] = {}
original_gate = workflow.run_delivery_gates_main
def _capture_gate(argv):
    captured["argv"] = list(argv)
    return 0


workflow.run_delivery_gates_main = _capture_gate
try:
    workflow._run_delivery_gate(
        amended_path=Path("/tmp/amended.docx"),
        original_path=Path("/tmp/original.docx"),
        verification_ledger_path=Path("/tmp/verification_ledger.txt"),
        benchmark_provided=False,
        based_on_comments=False,
        citation_style="harvard",
    )
finally:
    workflow.run_delivery_gates_main = original_gate

assert "--active-style" in captured["argv"]
style_index = captured["argv"].index("--active-style")
assert captured["argv"][style_index + 1] == "Harvard"

print("Harvard citation-mode regression checks passed.")

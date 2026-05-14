from __future__ import annotations

from argparse import Namespace
import os

import scripts.legal_answer_benchmark_qa as benchmark
import model_applicable_service as service


FORMER_WEAK_BENCHMARKS = {
    "cyber_online_safety_ransomware": {
        "topic": "cyber_computer_misuse_harassment",
        "guide": "cybercrime_law",
        "must_include": (
            "Computer Misuse Act 1990",
            "Online Safety Act 2023",
            "intimate image",
            "platform",
        ),
    },
    "environmental_permit_jr_nuisance": {
        "topic": "generic_environmental_law",
        "guide": "environmental_law",
        "must_include": (
            "Environmental Protection Act 1990",
            "Environmental Permitting",
            "Environmental Impact Assessment",
            "Habitats",
        ),
    },
}


def _benchmark_prompt(benchmark_id: str) -> str:
    for item in benchmark.BENCHMARKS:
        if item["id"] == benchmark_id:
            return item["prompt"]
    raise AssertionError(f"benchmark not found: {benchmark_id}")


def test_former_weak_live_benchmark_topics_have_specialist_guide_backstop() -> None:
    for benchmark_id, expected in FORMER_WEAK_BENCHMARKS.items():
        prompt = _benchmark_prompt(benchmark_id)
        profile = service._infer_retrieval_profile(prompt)  # type: ignore[attr-defined]
        assert profile.get("topic") == expected["topic"]

        guide_slug = service._infer_subject_guide_slug(  # type: ignore[attr-defined]
            str(profile.get("topic") or ""),
            prompt,
        )
        assert guide_slug == expected["guide"]

        guide = service._subject_guide_excerpt_for_query(  # type: ignore[attr-defined]
            prompt,
            profile,
            max_lines=80,
        )
        assert guide
        guide_lower = guide.lower()
        for term in expected["must_include"]:
            assert term.lower() in guide_lower

        mix = benchmark._guide_authority_mix(guide)  # type: ignore[attr-defined]
        assert mix["statutes"] >= 1
        assert mix["statutes"] + mix["cases"] >= 3


def test_benchmark_runtime_flags_force_required_env_even_from_empty_env() -> None:
    keys = [
        "LEGAL_AI_FORCE_CODEX_LOCAL_ADAPTER",
        "LEGAL_AI_REQUIRE_ONLINE_VERIFICATION",
        "LEGAL_AI_ONLINE_SEARCH_PROVIDER",
        "LEGAL_AI_ALLOW_KEYLESS_JINA_SEARCH",
    ]
    original = {key: os.environ.get(key) for key in keys}
    try:
        for key in keys:
            os.environ[key] = ""
        report = benchmark.run_benchmark(
            Namespace(
                force_codex=True,
                require_online=True,
                allow_keyless_jina_search=True,
                limit=1,
                live=False,
                audit_only=False,
                audit_max_chars=18000,
                fail_fast=False,
                output="",
                api_key="",
                provider="auto",
                model=None,
            )
        )
        assert os.environ["LEGAL_AI_FORCE_CODEX_LOCAL_ADAPTER"] == "1"
        assert os.environ["LEGAL_AI_REQUIRE_ONLINE_VERIFICATION"] == "1"
        assert os.environ["LEGAL_AI_ONLINE_SEARCH_PROVIDER"] == "jina"
        assert os.environ["LEGAL_AI_ALLOW_KEYLESS_JINA_SEARCH"] == "1"
        assert report["online_search_provider"] == "jina"
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    test_former_weak_live_benchmark_topics_have_specialist_guide_backstop()
    test_benchmark_runtime_flags_force_required_env_even_from_empty_env()
    print("Benchmark audit backstop regression passed.")

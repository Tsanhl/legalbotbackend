import os
from pathlib import Path

import model_applicable_service as service


def _with_env(key, value):
    original = os.environ.get(key)
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value
    return original


original_max = _with_env("LEGAL_AI_CODEX_LOCAL_MAX_PROMPT_CHARS", "26000")
original_compact = _with_env("LEGAL_AI_CODEX_LOCAL_COMPACT_PROMPT", "1")
try:
    huge_source = "\n".join(
        f"Retrieved authority line {idx}: Lena actual occupation and Land Registration Act 2002 priority."
        for idx in range(900)
    )
    huge_guidance = "\n".join(
        f"Topic-specific Land Law guide line {idx}: classify right, exact test, apply, counterargue, remedy."
        for idx in range(700)
    )
    full_message = "\n\n".join(
        [
            "[DIRECT-CODE / BACKEND DELIVERY MODE]\nComplete answer must go to chat, not files.",
            "[TOPIC-SPECIFIC GUIDANCE - LAND LAW]\n" + huge_guidance,
            "[RAG CONTEXT - INDEXED SOURCES]\n" + huge_source,
            "[OSCOLA INLINE HOUSE STYLE OVERRIDE - HIGHEST PRIORITY]\nUse full inline OSCOLA after relevant sentences.",
            "Write a 1500 word registered land priority problem answer for Oakridge.",
        ]
    )
    prompt = service._build_codex_local_exec_prompt(
        system_instruction="[SYSTEM]\n" + ("system rule\n" * 2000),
        full_message=full_message,
        history=[{"role": "user", "text": "Earlier prompt"}],
        project_id="prompt-compact-test",
    )
finally:
    if original_max is None:
        os.environ.pop("LEGAL_AI_CODEX_LOCAL_MAX_PROMPT_CHARS", None)
    else:
        os.environ["LEGAL_AI_CODEX_LOCAL_MAX_PROMPT_CHARS"] = original_max
    if original_compact is None:
        os.environ.pop("LEGAL_AI_CODEX_LOCAL_COMPACT_PROMPT", None)
    else:
        os.environ["LEGAL_AI_CODEX_LOCAL_COMPACT_PROMPT"] = original_compact

assert len(prompt) <= 26000
assert "[LEGAL AI LOCAL CODEX BACKEND ADAPTER - COMPACTED]" in prompt
assert "RAG CONTEXT - INDEXED SOURCES" in prompt
assert "TOPIC-SPECIFIC GUIDANCE - LAND LAW" in prompt
assert "OSCOLA INLINE HOUSE STYLE OVERRIDE" in prompt
assert "Write a 1500 word registered land priority problem answer for Oakridge." in prompt
assert "Complete answer must go to chat, not files." in prompt


commands = []
original_find = service._find_codex_cli
original_run = service.subprocess.run
original_prepare = service._prepare_codex_runtime_home
original_supports = service._codex_exec_supports_option
original_allow = os.environ.get("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED")
original_reasoning = os.environ.get("LEGAL_AI_CODEX_REASONING_EFFORT")
original_assume_network = os.environ.get("LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE")
try:
    service._find_codex_cli = lambda: "/fake/codex"
    service._codex_exec_supports_option = lambda cli, option: False
    os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = "1"
    os.environ["LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE"] = "1"
    os.environ.pop("LEGAL_AI_CODEX_REASONING_EFFORT", None)

    class _Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def _prepare(runtime_root: Path) -> Path:
        home = runtime_root / "codex_home"
        home.mkdir(parents=True, exist_ok=True)
        return home

    def _fake_run(cmd, input, text, capture_output, cwd, env, timeout):
        commands.append(list(cmd))
        Path(cmd[cmd.index("-o") + 1]).write_text("Part I: Introduction\n\nAnswer.", encoding="utf-8")
        return _Result()

    service._prepare_codex_runtime_home = _prepare
    service.subprocess.run = _fake_run
    generated = service._generate_with_codex_local_adapter(
        full_message="Backend prompt.",
        system_instruction="Rules.",
        history=[],
        project_id="reasoning-test",
        allow_web_search=False,
    )
finally:
    service._find_codex_cli = original_find
    service.subprocess.run = original_run
    service._prepare_codex_runtime_home = original_prepare
    service._codex_exec_supports_option = original_supports
    if original_allow is None:
        os.environ.pop("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED", None)
    else:
        os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = original_allow
    if original_reasoning is None:
        os.environ.pop("LEGAL_AI_CODEX_REASONING_EFFORT", None)
    else:
        os.environ["LEGAL_AI_CODEX_REASONING_EFFORT"] = original_reasoning
    if original_assume_network is None:
        os.environ.pop("LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE", None)
    else:
        os.environ["LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE"] = original_assume_network

assert "Part I: Introduction" in generated
assert commands
assert "-c" in commands[0]
reasoning_idx = commands[0].index("-c") + 1
assert commands[0][reasoning_idx] == 'model_reasoning_effort="xhigh"'

original_find = service._find_codex_cli
original_network = os.environ.get("CODEX_SANDBOX_NETWORK_DISABLED")
original_allow = os.environ.get("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED")
original_assume = os.environ.get("LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE")
try:
    service._find_codex_cli = lambda: "/fake/codex"
    os.environ["CODEX_SANDBOX_NETWORK_DISABLED"] = "1"
    os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = "1"
    os.environ.pop("LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE", None)
    try:
        service._generate_with_codex_local_adapter(
            full_message="Backend prompt.",
            system_instruction="Rules.",
            history=[],
            project_id="sandbox-network-guard",
            allow_web_search=False,
        )
        raise AssertionError("Expected sandbox network guard to fail fast")
    except Exception as exc:
        assert "cannot bypass the sandbox network block" in str(exc)
finally:
    service._find_codex_cli = original_find
    if original_network is None:
        os.environ.pop("CODEX_SANDBOX_NETWORK_DISABLED", None)
    else:
        os.environ["CODEX_SANDBOX_NETWORK_DISABLED"] = original_network
    if original_allow is None:
        os.environ.pop("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED", None)
    else:
        os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = original_allow
    if original_assume is None:
        os.environ.pop("LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE", None)
    else:
        os.environ["LEGAL_AI_CODEX_ASSUME_NETWORK_AVAILABLE"] = original_assume

print("Codex local prompt compaction checks passed.")

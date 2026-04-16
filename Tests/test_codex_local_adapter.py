from pathlib import Path
import gemini_service as gs


prompt = gs._build_codex_local_exec_prompt(
    system_instruction="System rule A\nSystem rule B",
    full_message="Current backend message body",
    history=[
        {"role": "user", "text": "First user prompt"},
        {"role": "assistant", "text": "Prior answer"},
    ],
    project_id="proj-123",
)
assert "[LEGAL AI LOCAL CODEX BACKEND ADAPTER]" in prompt
assert "[SYSTEM INSTRUCTIONS]" in prompt
assert "System rule A" in prompt
assert "[RECENT CONVERSATION HISTORY]" in prompt
assert "User:\nFirst user prompt" in prompt
assert "Assistant:\nPrior answer" in prompt
assert "[CURRENT BACKEND REQUEST]" in prompt
assert "Current backend message body" in prompt


assert "network access" in gs._build_codex_local_failure_message(
    "ERROR: stream disconnected before completion: error sending request for url (https://api.openai.com/v1/responses)",
    "",
).lower()
assert "not authenticated" in gs._build_codex_local_failure_message(
    "Please login first",
    "",
).lower()


original_find = gs._find_codex_cli
original_run = gs.subprocess.run
try:
    gs._find_codex_cli = lambda: "/fake/codex"

    class _Result:
        def __init__(self):
            self.returncode = 0
            self.stdout = ""
            self.stderr = ""

    def _fake_run(cmd, input, text, capture_output, cwd, env, timeout):
        assert cmd[0] == "/fake/codex"
        assert "exec" in cmd
        assert "--ephemeral" in cmd
        output_idx = cmd.index("-o") + 1
        out_path = Path(cmd[output_idx])
        out_path.write_text("Part I: Introduction\n\nLocal codex answer.", encoding="utf-8")
        assert "[CURRENT BACKEND REQUEST]" in input
        assert env["CODEX_HOME"]
        return _Result()

    gs.subprocess.run = _fake_run
    generated = gs._generate_with_codex_local_adapter(
        full_message="Backend asks for an essay.",
        system_instruction="Follow the backend rules.",
        history=[{"role": "user", "text": "Old prompt"}],
        project_id="proj-456",
        allow_web_search=False,
    )
    assert "Part I: Introduction" in generated
finally:
    gs._find_codex_cli = original_find
    gs.subprocess.run = original_run


print("Codex local adapter checks passed.")

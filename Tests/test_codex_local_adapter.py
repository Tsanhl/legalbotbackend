import os
import shutil
import tempfile
from pathlib import Path
import model_applicable_service as gs


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


with tempfile.TemporaryDirectory() as existing_dir, tempfile.TemporaryDirectory() as runtime_dir:
    existing_home = Path(existing_dir)
    runtime_root = Path(runtime_dir)
    (existing_home / "auth.json").write_text('{"access_token":"abc"}', encoding="utf-8")
    (existing_home / "config.toml").write_text('model = "gpt-5.4"\n', encoding="utf-8")
    (existing_home / "installation_id").write_text("install-1", encoding="utf-8")
    (existing_home / "version.json").write_text('{"version":"1"}', encoding="utf-8")
    (existing_home / "plugins").mkdir()
    (existing_home / "vendor_imports").mkdir()
    (existing_home / ".tmp").mkdir()

    original_codex_home_env = os.environ.get("CODEX_HOME")
    try:
        os.environ["CODEX_HOME"] = str(existing_home)
        prepared_home = gs._prepare_codex_runtime_home(runtime_root)
    finally:
        if original_codex_home_env is None:
            os.environ.pop("CODEX_HOME", None)
        else:
            os.environ["CODEX_HOME"] = original_codex_home_env

    assert (prepared_home / "auth.json").read_text(encoding="utf-8") == '{"access_token":"abc"}'
    assert (prepared_home / "config.toml").read_text(encoding="utf-8") == 'model = "gpt-5.4"\n'
    assert (prepared_home / "sessions").is_dir()
    assert (prepared_home / "archived_sessions").is_dir()
    assert (prepared_home / "plugins").exists()
    assert (prepared_home / "vendor_imports").exists()


original_network_env = os.environ.get("CODEX_SANDBOX_NETWORK_DISABLED")
original_allow_env = os.environ.get("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED")
try:
    os.environ["CODEX_SANDBOX_NETWORK_DISABLED"] = "1"
    os.environ.pop("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED", None)
    supported, reason = gs._codex_local_subprocess_supported()
    assert supported is False
    assert "subprocess network access is disabled" in reason.lower()
finally:
    if original_network_env is None:
        os.environ.pop("CODEX_SANDBOX_NETWORK_DISABLED", None)
    else:
        os.environ["CODEX_SANDBOX_NETWORK_DISABLED"] = original_network_env
    if original_allow_env is None:
        os.environ.pop("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED", None)
    else:
        os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = original_allow_env


original_find = gs._find_codex_cli
original_run = gs.subprocess.run
original_prepare_runtime_home = gs._prepare_codex_runtime_home
original_network_env = os.environ.get("CODEX_SANDBOX_NETWORK_DISABLED")
original_allow_env = os.environ.get("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED")
try:
    gs._find_codex_cli = lambda: "/fake/codex"
    os.environ.pop("CODEX_SANDBOX_NETWORK_DISABLED", None)
    os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = "1"

    class _Result:
        def __init__(self):
            self.returncode = 0
            self.stdout = ""
            self.stderr = ""

    def _fake_prepare_runtime_home(runtime_root: Path) -> Path:
        home = runtime_root / "codex_home"
        home.mkdir(parents=True, exist_ok=True)
        return home

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

    gs._prepare_codex_runtime_home = _fake_prepare_runtime_home
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
    gs._prepare_codex_runtime_home = original_prepare_runtime_home
    if original_network_env is None:
        os.environ.pop("CODEX_SANDBOX_NETWORK_DISABLED", None)
    else:
        os.environ["CODEX_SANDBOX_NETWORK_DISABLED"] = original_network_env
    if original_allow_env is None:
        os.environ.pop("LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED", None)
    else:
        os.environ["LEGAL_AI_CODEX_ALLOW_NETWORK_DISABLED"] = original_allow_env


print("Codex local adapter checks passed.")

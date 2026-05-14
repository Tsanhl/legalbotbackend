"""Run the offline regression suite under Tests/ with a single command."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    tests_dir = Path(__file__).resolve().parent
    repo_root = tests_dir.parent
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root)

    failed: list[str] = []
    test_files = sorted(tests_dir.glob("test_*.py"))

    for test_file in test_files:
        rel_path = test_file.relative_to(repo_root)
        print(f"=== RUN {rel_path} ===", flush=True)
        result = subprocess.run([sys.executable, str(test_file)], cwd=repo_root, env=env)
        print(f"=== EXIT {rel_path} {result.returncode} ===", flush=True)
        if result.returncode:
            failed.append(str(rel_path))

    print(f"TOTAL {len(test_files)}", flush=True)
    print(f"FAILED {len(failed)}", flush=True)
    if failed:
        print("FAILED_LIST", flush=True)
        for rel_path in failed:
            print(rel_path, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

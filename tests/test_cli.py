import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(extra_args, env_overrides):
    env = os.environ.copy()
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-m", "scripts.collect", *extra_args],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
    )


class TestCli(unittest.TestCase):
    def test_emits_empty_json_when_no_data(self):
        with tempfile.TemporaryDirectory() as base:
            env = {
                "MYFOCUS_BASE_CLAUDE_CODE": str(Path(base) / "claude"),
                "MYFOCUS_BASE_CODEX": str(Path(base) / "codex"),
                "MYFOCUS_BASE_GEMINI": str(Path(base) / "gemini"),
            }
            r = _run(["--window", "1h"], env)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data["window"], "1h")
            self.assertEqual(data["sessions"], [])
            self.assertEqual(set(data["agents_scanned"]), {"claude_code", "codex", "gemini"})

    def test_window_error_exits_nonzero(self):
        r = _run(["--window", "5h30m"], {})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("single-unit", r.stderr)

    def test_list_agents(self):
        r = _run(["--list-agents"], {})
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("claude_code", r.stdout)
        self.assertIn("codex", r.stdout)
        self.assertIn("gemini", r.stdout)

    def test_unknown_agent_recorded_in_errors(self):
        with tempfile.TemporaryDirectory() as base:
            env = {
                "MYFOCUS_BASE_CLAUDE_CODE": str(Path(base) / "claude"),
                "MYFOCUS_BASE_CODEX": str(Path(base) / "codex"),
                "MYFOCUS_BASE_GEMINI": str(Path(base) / "gemini"),
            }
            r = _run(["--agents", "claude_code,nope"], env)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            data = json.loads(r.stdout)
            self.assertTrue(any(e.get("agent") == "nope" for e in data["errors"]))


if __name__ == "__main__":
    unittest.main()

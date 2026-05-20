import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from scripts.scanners import REGISTRY
import scripts.scanners.codex  # noqa: F401


HEADER = {
    "timestamp": "2026-05-20T05:26:38.654Z",
    "type": "session_meta",
    "payload": {"id": "019e43d9", "cwd": "/Users/x/proj"},
}
USER_TURN = {"type": "user", "payload": {"message": "deploy to staging"}}
ASSISTANT_TURN = {"type": "assistant", "payload": {"content": "Staging deploy initiated."}}
RESPONSE_USER = {
    "type": "response_item",
    "payload": {"role": "user", "content": [{"type": "input_text", "text": "actual user prompt"}]},
}
RESPONSE_ASSISTANT = {
    "type": "response_item",
    "payload": {"role": "assistant", "content": [{"type": "output_text", "text": "actual assistant reply"}]},
}
RESPONSE_DEVELOPER = {
    "type": "response_item",
    "payload": {"role": "developer", "content": [{"type": "input_text", "text": "system noise"}]},
}


def _scan():
    return REGISTRY["codex"].fn


class TestScanCodex(unittest.TestCase):
    def test_registers(self):
        self.assertIn("codex", REGISTRY)

    def test_extracts_meta_and_text(self):
        with tempfile.TemporaryDirectory() as base:
            day = Path(base) / "2026" / "05" / "20"
            day.mkdir(parents=True)
            session_file = day / "rollout-2026-05-20T05-26-38-019e43d9.jsonl"
            with session_file.open("w") as f:
                for obj in [HEADER, USER_TURN, ASSISTANT_TURN]:
                    f.write(json.dumps(obj) + "\n")
            digests = _scan()(Path(base), timedelta(hours=24), None, 40, 4000)
            self.assertEqual(len(digests), 1)
            d = digests[0]
            self.assertEqual(d.agent, "codex")
            self.assertEqual(d.cwd, "/Users/x/proj")
            self.assertIn("deploy to staging", d.user_excerpts)
            self.assertIn("Staging deploy initiated.", d.assistant_excerpts)

    def test_response_item_role_routing(self):
        with tempfile.TemporaryDirectory() as base:
            day = Path(base) / "2026" / "05" / "20"
            day.mkdir(parents=True)
            session_file = day / "rollout-resp.jsonl"
            with session_file.open("w") as f:
                for obj in [HEADER, RESPONSE_USER, RESPONSE_ASSISTANT, RESPONSE_DEVELOPER]:
                    f.write(json.dumps(obj) + "\n")
            digests = _scan()(Path(base), timedelta(hours=24), None, 40, 4000)
            self.assertEqual(len(digests), 1)
            d = digests[0]
            self.assertEqual(d.user_excerpts, ["actual user prompt"])
            self.assertEqual(d.assistant_excerpts, ["actual assistant reply"])
            # developer role is ignored
            self.assertNotIn("system noise", d.user_excerpts)
            self.assertNotIn("system noise", d.assistant_excerpts)

    def test_missing_header_null_cwd(self):
        with tempfile.TemporaryDirectory() as base:
            day = Path(base) / "2026" / "05" / "20"
            day.mkdir(parents=True)
            (day / "rollout-x.jsonl").write_text(json.dumps(USER_TURN) + "\n")
            digests = _scan()(Path(base), timedelta(hours=24), None, 40, 4000)
            self.assertEqual(len(digests), 1)
            self.assertIsNone(digests[0].cwd)

    def test_missing_base_returns_empty(self):
        self.assertEqual(_scan()(Path("/no/such/path"), timedelta(hours=24), None, 40, 4000), [])


if __name__ == "__main__":
    unittest.main()

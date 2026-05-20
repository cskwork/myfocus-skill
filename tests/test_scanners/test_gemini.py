import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from scripts.scanners import REGISTRY
import scripts.scanners.gemini  # noqa: F401


LOGS = [
    {"sessionId": "s1", "messageId": 0, "type": "user", "message": "fix bug A"},
    {"sessionId": "s1", "messageId": 1, "type": "model", "message": "Done."},
    {"sessionId": "s1", "messageId": 2, "type": "user", "message": "now bug B"},
]


def _scan():
    return REGISTRY["gemini"].fn


class TestScanGemini(unittest.TestCase):
    def test_registers(self):
        self.assertIn("gemini", REGISTRY)

    def test_alias_resolves(self):
        with tempfile.TemporaryDirectory() as base:
            bp = Path(base)
            (bp / "projects.json").write_text(json.dumps({"projects": {"/Users/x/myproject": "myproject"}}))
            d = bp / "tmp" / "myproject"
            d.mkdir(parents=True)
            (d / "logs.json").write_text(json.dumps(LOGS))
            digests = _scan()(bp, timedelta(hours=24), None, 40, 4000)
            self.assertEqual(len(digests), 1)
            self.assertEqual(digests[0].cwd, "/Users/x/myproject")
            self.assertEqual(digests[0].user_excerpts, ["fix bug A", "now bug B"])
            self.assertEqual(digests[0].assistant_excerpts, ["Done."])

    def test_unknown_alias_null_cwd(self):
        with tempfile.TemporaryDirectory() as base:
            bp = Path(base)
            (bp / "projects.json").write_text(json.dumps({"projects": {}}))
            d = bp / "tmp" / "mystery"
            d.mkdir(parents=True)
            (d / "logs.json").write_text(json.dumps(LOGS))
            digests = _scan()(bp, timedelta(hours=24), None, 40, 4000)
            self.assertEqual(len(digests), 1)
            self.assertIsNone(digests[0].cwd)

    def test_unparseable_logs_skipped(self):
        with tempfile.TemporaryDirectory() as base:
            bp = Path(base)
            (bp / "projects.json").write_text("{}")
            d = bp / "tmp" / "broken"
            d.mkdir(parents=True)
            (d / "logs.json").write_text("not json")
            self.assertEqual(_scan()(bp, timedelta(hours=24), None, 40, 4000), [])

    def test_missing_tmp_returns_empty(self):
        with tempfile.TemporaryDirectory() as base:
            self.assertEqual(_scan()(Path(base), timedelta(hours=24), None, 40, 4000), [])


if __name__ == "__main__":
    unittest.main()

import json
import os
import tempfile
import time
import unittest
from datetime import timedelta
from pathlib import Path

from scripts.scanners import REGISTRY
import scripts.scanners.claude_code  # noqa: F401


SAMPLE_LINES = [
    {"type": "file-history-snapshot", "messageId": "m0"},
    {"type": "user", "message": {"content": [{"type": "text", "text": "rewrite this function"}]}},
    {"type": "assistant", "message": {"content": [{"type": "text", "text": "Here is the rewrite."}]}},
    {"type": "user", "message": {"content": [{"type": "text", "text": "now add tests"}]}},
]


def _scan():
    return REGISTRY["claude_code"].fn


class TestScanClaudeCode(unittest.TestCase):
    def test_registers(self):
        self.assertIn("claude_code", REGISTRY)

    def test_decode_cwd_inline(self):
        from scripts.scanners.claude_code import _decode_cwd
        self.assertEqual(_decode_cwd("-Users-x-myproj"), "/Users/x/myproj")
        self.assertIsNone(_decode_cwd("no-leading-dash"))
        self.assertIsNone(_decode_cwd(""))

    def test_scans_recent_session(self):
        with tempfile.TemporaryDirectory() as base:
            proj_dir = Path(base) / "-Users-x-myproj"
            proj_dir.mkdir()
            session_file = proj_dir / "abc-123.jsonl"
            with session_file.open("w") as f:
                for obj in SAMPLE_LINES:
                    f.write(json.dumps(obj) + "\n")

            digests = _scan()(Path(base), timedelta(hours=1), None, 40, 4000)
            self.assertEqual(len(digests), 1)
            d = digests[0]
            self.assertEqual(d.agent, "claude_code")
            self.assertEqual(d.session_id, "abc-123")
            self.assertEqual(d.cwd, "/Users/x/myproj")
            self.assertIn("now add tests", d.user_excerpts)
            self.assertIn("Here is the rewrite.", d.assistant_excerpts)

    def test_skips_old(self):
        with tempfile.TemporaryDirectory() as base:
            p = Path(base) / "-Users-x-myproj"
            p.mkdir()
            f = p / "old.jsonl"
            f.write_text(json.dumps(SAMPLE_LINES[1]) + "\n")
            old = time.time() - 7200
            os.utime(f, (old, old))
            self.assertEqual(_scan()(Path(base), timedelta(hours=1), None, 40, 4000), [])

    def test_cwd_filter(self):
        with tempfile.TemporaryDirectory() as base:
            for sub in ("-Users-x-myproj", "-Users-x-other"):
                d = Path(base) / sub
                d.mkdir()
                (d / "s.jsonl").write_text(json.dumps(SAMPLE_LINES[1]) + "\n")
            result = _scan()(Path(base), timedelta(hours=1), "/Users/x/myproj", 40, 4000)
            self.assertEqual([d.cwd for d in result], ["/Users/x/myproj"])

    def test_missing_base_returns_empty(self):
        self.assertEqual(_scan()(Path("/no/such/path"), timedelta(hours=1), None, 40, 4000), [])

    def test_cwd_filter_works_for_dashed_paths(self):
        # Regression: when the real path contains dashes (e.g. user folder
        # 'someuser-name'), decoding is lossy. The scanner should still
        # match the user's --cwd filter by re-encoding the filter and
        # comparing against the directory name.
        #
        # Known limitation: the encoded fallback cannot distinguish between
        # 'item-docs/sub' (subdir, should match) and 'item-docs-other'
        # (sibling, should not), because '-' encodes both '/' and literal
        # dashes. The fallback accepts both — false positives over false
        # negatives, since zero-result behavior was worse in practice.
        with tempfile.TemporaryDirectory() as base:
            d = Path(base) / "-Users-someuser-name-work-item-docs"
            d.mkdir()
            (d / "s.jsonl").write_text(json.dumps(SAMPLE_LINES[1]) + "\n")

            result = _scan()(
                Path(base),
                timedelta(hours=1),
                "/Users/someuser-name/work/item-docs",
                40, 4000,
            )
            paths = [r.path for r in result]
            self.assertTrue(
                any("/-Users-someuser-name-work-item-docs/" in p for p in paths),
                msg=f"dashed-path filter found nothing in {paths}",
            )


if __name__ == "__main__":
    unittest.main()

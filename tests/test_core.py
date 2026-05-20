import json as _json
import unittest
from datetime import datetime, timedelta, timezone
from scripts.core import parse_window, WindowParseError, cwd_matches, SessionDigest


class TestParseWindow(unittest.TestCase):
    def test_minutes(self):
        self.assertEqual(parse_window("30m"), timedelta(minutes=30))

    def test_hours(self):
        self.assertEqual(parse_window("5h"), timedelta(hours=5))

    def test_seconds(self):
        self.assertEqual(parse_window("90s"), timedelta(seconds=90))

    def test_days(self):
        self.assertEqual(parse_window("2d"), timedelta(days=2))

    def test_rejects_combined(self):
        with self.assertRaises(WindowParseError) as ctx:
            parse_window("5h30m")
        self.assertIn("single-unit", str(ctx.exception))

    def test_rejects_bad_unit(self):
        with self.assertRaises(WindowParseError):
            parse_window("5x")

    def test_rejects_empty(self):
        with self.assertRaises(WindowParseError):
            parse_window("")


class TestCwdMatches(unittest.TestCase):
    def test_no_filter_accepts_any(self):
        self.assertTrue(cwd_matches("/x/y", None))
        self.assertTrue(cwd_matches(None, None))

    def test_exact(self):
        self.assertTrue(cwd_matches("/x/y", "/x/y"))

    def test_subdir(self):
        self.assertTrue(cwd_matches("/x/y/z", "/x/y"))

    def test_prefix_boundary(self):
        self.assertFalse(cwd_matches("/x/yankee", "/x/y"))

    def test_null_cwd_rejected_when_filter_set(self):
        self.assertFalse(cwd_matches(None, "/x"))

    def test_trailing_slash_in_filter_ok(self):
        self.assertTrue(cwd_matches("/x/y", "/x/y/"))


class TestSessionDigest(unittest.TestCase):
    def test_to_dict_shape(self):
        d = SessionDigest(
            agent="claude",
            session_id="abc-123",
            path="/x/y.jsonl",
            cwd="/home/user/proj",
            mtime=datetime(2026, 5, 20, 14, 0, tzinfo=timezone.utc),
            user_excerpts=["fix bug"],
            assistant_excerpts=["done"],
        )
        out = d.to_dict()
        self.assertEqual(out["agent"], "claude")
        self.assertEqual(out["mtime"], "2026-05-20T14:00:00+00:00")

    def test_round_trip(self):
        d = SessionDigest(
            agent="codex", session_id="s1", path="/x.jsonl", cwd=None,
            mtime=datetime(2026, 1, 1, tzinfo=timezone.utc),
            user_excerpts=[], assistant_excerpts=[],
        )
        self.assertIsNone(_json.loads(_json.dumps(d.to_dict()))["cwd"])


if __name__ == "__main__":
    unittest.main()

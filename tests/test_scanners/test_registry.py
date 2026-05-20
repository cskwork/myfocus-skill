import unittest
from pathlib import Path
from scripts.scanners import REGISTRY, register, ScannerSpec


class TestRegistry(unittest.TestCase):
    def setUp(self):
        self._saved = dict(REGISTRY)
        REGISTRY.clear()

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self._saved)

    def test_register_decorator(self):
        @register("dummy", default_base=Path("/tmp/dummy"))
        def scan_dummy(base_path, window, cwd_filter, max_files, max_chars):
            return []

        self.assertIn("dummy", REGISTRY)
        spec = REGISTRY["dummy"]
        self.assertIsInstance(spec, ScannerSpec)
        self.assertEqual(spec.name, "dummy")
        self.assertEqual(spec.default_base, Path("/tmp/dummy"))
        self.assertEqual(spec.fn(Path("/tmp/dummy"), None, None, 40, 4000), [])

    def test_register_returns_function(self):
        @register("dummy2", default_base=Path("/tmp/d2"))
        def fn(*a, **kw):
            return ["called"]

        self.assertIs(REGISTRY["dummy2"].fn, fn)
        self.assertEqual(fn(None, None, None, 0, 0), ["called"])


if __name__ == "__main__":
    unittest.main()

"""Exercise verify's exit status and coverage with real child processes."""
import pathlib
import subprocess
import sys
import tempfile
import unittest


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "tools").mkdir()
        source = pathlib.Path(__file__).with_name("verify.py").read_text()
        self.write("tools/verify.py", source)
        self.write("tools/assemble.py", "print('trail attempted')\n")
        self.write("tools/check.py", "import sys\nprint(repr(sys.argv[1:]))\n")
        self.write("tools/test_stub.py", "import unittest\nclass Smoke(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n")

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text(text)

    def run_verify(self, *args):
        # Deliberately launch from outside the fixture: root is the script's location.
        return subprocess.run([sys.executable, str(self.root / "tools/verify.py"), *args],
                              capture_output=True, text=True, timeout=30)

    def test_failures_are_aggregated_and_later_checks_still_run(self):
        self.write("jumps/jumps.py", "raise SystemExit(3)\n")
        self.write("observers/observers.py", "print('observers attempted')\n")
        self.write("tools/assemble.py", "print('trail attempted')\nraise SystemExit(1)\n")
        result = self.run_verify()
        self.assertEqual(result.returncode, 1)
        self.assertIn("observers attempted", result.stdout)
        self.assertIn("trail attempted", result.stdout)
        self.assertIn("2 failed: jumps, trail", result.stdout)

    def test_an_absent_project_is_skipped_but_a_missing_checker_fails(self):
        result = self.run_verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SKIP field", result.stdout)
        (self.root / "field").mkdir()
        result = self.run_verify()
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL field", result.stdout)
        self.assertIn("trail attempted", result.stdout)

    def test_refs_are_passed_as_literal_arguments(self):
        result = self.run_verify("--base", "branch with spaces", "--head", "HEAD~2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("['--base', 'branch with spaces', '--head', 'HEAD~2']", result.stdout)

    def test_field_is_checked_without_regeneration_and_unknown_scripts_are_not_run(self):
        self.write("field/field.py", "import sys\nassert sys.argv[1:] == ['--check']\n")
        self.write("unrelated.py", "raise RuntimeError('must never be run')\n")
        result = self.run_verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS field", result.stdout)


if __name__ == "__main__":
    unittest.main()

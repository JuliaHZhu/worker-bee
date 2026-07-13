"""Regression tests for symlink bypass protection (fixes #41)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.safety import is_self_modify_target, WORKER_BEE_ROOT


class TestSymlinkBypass(unittest.TestCase):
    def test_symlink_into_worker_bee_blocked(self):
        """A symlink pointing into worker-bee source must be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a symlink inside tmpdir pointing to worker-bee source
            link_path = Path(tmpdir) / "safety.py"
            link_path.symlink_to(WORKER_BEE_ROOT / "safety.py")
            # Should be blocked because realpath resolves to agent/safety.py
            self.assertTrue(is_self_modify_target(str(link_path)))

    def test_symlink_escaping_worker_bee_allowed(self):
        """A symlink pointing outside worker-bee is allowed (not self-modify)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            real_file = Path(tmpdir) / "outside.txt"
            real_file.write_text("hello")
            link_path = Path(tmpdir) / "link.txt"
            link_path.symlink_to(real_file)
            # Should NOT be blocked because it doesn't point into worker-bee
            self.assertFalse(is_self_modify_target(str(link_path)))

    def test_realpath_prevents_symlink_bypass(self):
        """realpath must resolve before checking containment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a chain of symlinks to reach worker-bee source
            mid = Path(tmpdir) / "mid"
            mid.symlink_to(WORKER_BEE_ROOT)
            final = Path(tmpdir) / "final"
            final.symlink_to(mid / "safety.py")
            # Should still be blocked because realpath resolves into worker-bee
            self.assertTrue(is_self_modify_target(str(final)))


if __name__ == "__main__":
    unittest.main()

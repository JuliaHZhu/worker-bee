"""Regression tests for path traversal protections (fixes #31)."""
import unittest
from pathlib import Path
from unittest.mock import patch

from swarm.file_server import MailboxHandler


class TestPathTraversal(unittest.TestCase):
    def test_translate_path_restricted_to_serve_dir(self):
        """translate_path must reject paths outside SERVE_DIR."""
        with patch("swarm.file_server.SERVE_DIR", Path("/tmp/test-mailbox")):
            handler = MailboxHandler.__new__(MailboxHandler)
            # Path inside serve dir is OK
            result = handler.translate_path("/file.txt")
            self.assertIn("/tmp/test-mailbox/file.txt", result)

            # Path traversal attempt must be blocked
            result = handler.translate_path("/../../etc/passwd")
            self.assertIn("forbidden", result)

    def test_translate_path_blocks_symlink_escape(self):
        """Symlinks that resolve outside SERVE_DIR must be blocked."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            outside = Path(tmpdir) / "secret.txt"
            outside.write_text("secret")
            link = Path("/tmp/test-mailbox") / "escaped.txt"
            # Only test if we can create the symlink
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest("Cannot create symlink in /tmp/test-mailbox")
            with patch("swarm.file_server.SERVE_DIR", Path("/tmp/test-mailbox")):
                handler = MailboxHandler.__new__(MailboxHandler)
                result = handler.translate_path("/escaped.txt")
                self.assertIn("forbidden", result)
            link.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

"""Regression tests for SSRF guard (fixes #18)."""
import unittest

from tools.web import _guard_url


class TestSSRFGuard(unittest.TestCase):
    def test_blocks_localhost(self):
        """localhost must be blocked."""
        with self.assertRaises(ValueError):
            _guard_url("http://localhost/admin")

    def test_blocks_127_0_0_1(self):
        """127.0.0.1 must be blocked."""
        with self.assertRaises(ValueError):
            _guard_url("http://127.0.0.1:8080/api")

    def test_blocks_internal_ips(self):
        """Private IP ranges must be blocked."""
        for ip in ["10.0.0.1", "192.168.1.1", "172.16.0.1"]:
            with self.subTest(ip=ip):
                with self.assertRaises(ValueError):
                    _guard_url(f"http://{ip}/")

    def test_blocks_metadata_endpoint(self):
        """Cloud metadata endpoints must be blocked."""
        with self.assertRaises(ValueError):
            _guard_url("http://169.254.169.254/latest/meta-data/")

    def test_allows_external_https(self):
        """External HTTPS URLs should pass."""
        # Should not raise
        _guard_url("https://api.github.com/users/octocat")

    def test_blocks_file_scheme(self):
        """file:// scheme must be blocked."""
        with self.assertRaises(ValueError):
            _guard_url("file:///etc/passwd")

    def test_blocks_ftp_scheme(self):
        """ftp:// scheme must be blocked."""
        with self.assertRaises(ValueError):
            _guard_url("ftp://internal.server/secret.txt")


if __name__ == "__main__":
    unittest.main()

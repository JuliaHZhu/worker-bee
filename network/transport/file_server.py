#!/usr/bin/env python3
"""Simple HTTP file server for inter-node file sharing.

Serves files from the node's ~/.worker-bee/mailbox directory.
Other nodes can fetch files via HTTP GET with an X-Token header.

Usage:
    FILE_SERVER_TOKEN=secret python network/transport/file_server.py [port]
"""
import hmac
import logging
import http.server
import os
import socketserver
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

SERVE_DIR = Path.home() / ".worker-bee" / "mailbox"
FILE_SERVER_TOKEN = os.environ.get("FILE_SERVER_TOKEN", "")

# PORT is resolved at main() time, not import time, so tests can import safely.
def _get_port() -> int:
    return int(sys.argv[1]) if len(sys.argv) > 1 else 9999


class MailboxHandler(http.server.SimpleHTTPRequestHandler):
    """Serve files from the mailbox directory (token-gated)."""

    def do_GET(self):
        if FILE_SERVER_TOKEN:
            client_token = self.headers.get("X-Token", "")
            if not hmac.compare_digest(client_token, FILE_SERVER_TOKEN):
                self.send_error(403, "Forbidden: Invalid or missing token")
                return
        super().do_GET()

    def translate_path(self, path):
        """Restrict access to the mailbox directory."""
        rel = Path(path).relative_to("/")
        target = SERVE_DIR / rel
        # Use os.path.realpath to resolve symlinks before checking containment
        try:
            real_target = Path(os.path.realpath(target))
            real_serve = Path(os.path.realpath(SERVE_DIR))
            real_target.relative_to(real_serve)
        except (ValueError, OSError):
            return str(SERVE_DIR / "forbidden")
        return str(target)

    def log_message(self, format, *args):
        """Prefix logs."""
        logger.info("[FileServer] %s - %s", self.client_address[0], format % args)


def main():
    if not SERVE_DIR.exists():
        SERVE_DIR.mkdir(parents=True, exist_ok=True)

    if not FILE_SERVER_TOKEN:
        logger.error("[FileServer] FILE_SERVER_TOKEN not set. Set it via environment variable to start the server.")
        sys.exit(1)
    auth_status = "token required"
    logger.info("[FileServer] Serving %s on port %s (%s)", SERVE_DIR, _get_port(), auth_status)
    with socketserver.TCPServer(("", _get_port()), MailboxHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()

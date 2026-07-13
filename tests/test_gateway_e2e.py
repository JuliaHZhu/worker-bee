#!/usr/bin/env python3
"""
Gateway end-to-end test

Spawns the gateway in a subprocess, sends a simulated Feishu webhook,
and asserts the agent reply is received and logged.

Usage:
    python tests/test_gateway_e2e.py
"""

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = PROJECT_ROOT / ".local" / "wb-gateway-e2e.log"
PORT = 8081


def wait_for_port(port: int, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def send_webhook(text: str) -> dict:
    payload = {
        "header": {
            "event_id": "test_evt_e2e",
            "event_type": "im.message.receive_v1",
            "token": "",
        },
        "event": {
            "message": {
                "message_id": "test_msg_e2e",
                "message_type": "text",
                "chat_type": "p2p",
                "content": json.dumps({"text": text}),
            },
            "sender": {
                "sender_id": {
                    "open_id": "ou_test_user_001"
                }
            },
        },
    }
    body = json.dumps(payload)
    request = (
        f"POST /webhook HTTP/1.1\r\n"
        f"Host: 127.0.0.1:{PORT}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
        f"{body}"
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(15)
    try:
        sock.connect(("127.0.0.1", PORT))
        sock.sendall(request.encode())
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
    finally:
        sock.close()

    header, _, body = response.partition(b"\r\n\r\n")
    return json.loads(body)


def main() -> int:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.unlink(missing_ok=True)

    proc = subprocess.Popen(
        [sys.executable, "-m", "agent.cli", "gateway", "start"],
        cwd=PROJECT_ROOT,
        stdout=LOG_PATH.open("w"),
        stderr=subprocess.STDOUT,
    )

    try:
        if not wait_for_port(PORT):
            print("FAIL: gateway did not bind to port", PORT)
            return 1
        print("Gateway up on port", PORT)

        resp = send_webhook("hi")
        print("HTTP response:", resp)
        assert resp.get("code") == 0, f"Unexpected response: {resp}"

        # Give agent time to log
        time.sleep(6)

        log_text = LOG_PATH.read_text()
        print("--- Log tail ---")
        print(log_text[-1000:])

        assert "NATS dispatch failed" in log_text or "swarm.incoming.gateway" in log_text
        assert "Local agent reply" in log_text
        print("PASS: full HTTP -> agent -> reply loop verified")
        return 0
    finally:
        proc.terminate()
        proc.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(main())

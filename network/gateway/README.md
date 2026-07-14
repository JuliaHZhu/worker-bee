# Gateway — External Messaging Bridge

Hermes-style minimal gateway for worker-bee. Bridges external messaging
platforms (Feishu/Lark, etc.) into the internal Agent / NATS layer.

## Architecture

```
┌─────────────┐     ┌───────────────┐     ┌─────────────────┐
│   Feishu    │────▶│ FeishuAdapter │────▶│  MessageEvent   │
│  Webhook    │     │  (web server) │     │ (normalized)    │
└─────────────┘     └───────────────┘     └─────────────────┘
                                                   │
                                                   ▼
                                          ┌─────────────────┐
                                          │  GatewayRunner  │
                                          │  route_incoming │
                                          └─────────────────┘
                                                   │
                      ┌────────────────────────────┼────────────────────────────┐
                      │                            ▼                            │
                      ▼                    ┌─────────────────┐                  ▼
              ┌───────────────┐            │ process_with_agent              ┌───────────────┐
              │  NATS layer   │            │ (Agent / echo)  │               │  Reply back   │
              │  (optional)   │            └─────────────────┘               │  to Feishu    │
              └───────────────┘                      │                        └───────────────┘
                                                     ▼
                                          ┌─────────────────┐
                                          │  SendResult     │
                                          └─────────────────┘
```

## Key Components

| File | Role |
|------|------|
| `base.py` | `BasePlatformAdapter` ABC, `MessageEvent`, `SendResult` |
| `platform_registry.py` | `PlatformRegistry` — self-registration pattern |
| `run.py` | `GatewayRunner` — lifecycle + message routing (thread-safe) |
| `config.py` | `GatewayConfig` — loads from `~/.worker-bee/config.json` |
| `platforms/feishu.py` | Feishu webhook receiver + API sender (self-contained) |

## Adding a New Platform

```python
from network.gateway.base import BasePlatformAdapter, MessageEvent, SendResult
from network.gateway.platform_registry import PlatformEntry, platform_registry

class MyAdapter(BasePlatformAdapter):
    def start(self): ...
    def stop(self): ...
    def send(self, event, text) -> SendResult: ...

platform_registry.register(PlatformEntry(
    name="myplatform",
    label="My Platform",
    adapter_factory=lambda cfg: MyAdapter(cfg),
    check_fn=lambda: True,
))
```

## Configuration

In `~/.worker-bee/config.json`:

```json
{
  "gateway": {
    "enabled": true,
    "platforms": {
      "feishu": {
        "enabled": true,
        "port": 8080,
        "host": "0.0.0.0",
        "extra": {
          "verification_token": "your_feishu_token",
          "app_id": "cli_xxx",
          "app_secret": "xxx"
        }
      }
    }
  }
}
```

## CLI

```bash
wb gateway start   # Start the gateway server (handles SIGTERM + Ctrl+C)
```

## Tests

```bash
python -m pytest tests/test_gateway.py -v
```

17 tests covering registry, config, runner lifecycle, and Feishu webhook smoke tests.

## Design Reference

Architecture pattern adapted from [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) gateway layer.

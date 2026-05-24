"""Integration tests for supervisor skill — full job lifecycle.

These tests simulate how hermes-lite uses the supervisor skill in practice:
- Input: a complete Markdown job file (frontmatter + event stream body)
- Processing: tool handlers read / write the file
- Output: the job file contains an append-only history of events

Architecture under test:
    hermes-lite agent
        |
        +-- Deck: supervisor tools (status, read, create, update, evaluate)
        |
        +-- File: jobs/JOB-XXX.md (text information field)
            - frontmatter: create-time metadata (immutable after creation)
            - body: append-only event stream (source of truth)

All history is preserved. Frontmatter state is a derived cache.
"""

import json
import shutil
from pathlib import Path

import pytest

from tools.supervisor import (
    supervisor_status,
    supervisor_read,
    supervisor_create,
    supervisor_update,
    supervisor_evaluate,
    supervisor_delete,
    JOBS_DIR,
    INDEX_FILE,
)


@pytest.fixture(autouse=True)
def clean_jobs_dir():
    """Wipe jobs/ before each test."""
    if JOBS_DIR.exists():
        shutil.rmtree(JOBS_DIR)
    JOBS_DIR.mkdir()
    yield


# ── Scenario 1: empty board ─────────────────────────────────────────────

def test_scenario_empty_board():
    """User says: '监工，看看进度' → agent calls supervisor_status."""
    result = supervisor_status()
    assert "empty" in result.lower()


# ── Scenario 2: create a job from a complete description ────────────────

def test_scenario_create_job():
    """User says: '新建一个任务：修复 auth' → agent calls supervisor_create.

    The created file must be a complete, readable Markdown document with:
    - YAML frontmatter (all metadata)
    - Task description section
    - Empty append-only event stream section (seeded with 'created' event)
    """
    result = supervisor_create(
        title="修复 SSO 回调 URL 硬编码",
        description="auth.py 中的 callback_url 写死在第 42 行，需要改成配置化。",
        skills=["code-review"],
    )
    assert result.startswith("Created JOB-")
    job_id = result.split(":")[0].replace("Created ", "")

    # Verify file exists and is complete
    path = JOBS_DIR / f"{job_id}.md"
    content = path.read_text()

    # Frontmatter checks
    assert "id: " + job_id in content
    assert "title: 修复 SSO 回调 URL 硬编码" in content
    assert "skills:" in content
    assert "  - code-review" in content
    assert "state: Todo" in content
    assert "priority: 2" in content
    assert "created: " in content
    assert "updated: " in content

    # Body checks
    assert "## 任务描述" in content
    assert "auth.py 中的 callback_url" in content
    assert "## 事件流" in content
    assert "created — state=Todo" in content

    # Verify index is maintained
    index = json.loads(INDEX_FILE.read_text())
    assert index["jobs"][job_id]["state"] == "Todo"
    assert index["jobs"][job_id]["title"] == "修复 SSO 回调 URL 硬编码"


# ── Scenario 3: update state and append logs ────────────────────────

def test_scenario_update_job_lifecycle():
    """User says: '标记 JOB-001 完成' → agent calls supervisor_update.

    The update must:
    - Change the cached frontmatter state
    - Append a state_change event to the event stream
    - Leave all prior events untouched
    """
    supervisor_create("任务A", "做点什么")
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    # Worker starts
    supervisor_update(job_id, state="Running")
    content = supervisor_read(job_id)
    assert "state: Running" in content
    assert "state_change — Todo → Running" in content

    # Worker logs progress
    supervisor_update(job_id, append_log="读了 auth.py，发现硬编码")
    content = supervisor_read(job_id)
    assert "log — 读了 auth.py" in content

    # Worker finishes
    supervisor_update(job_id, state="Done")
    content = supervisor_read(job_id)
    assert "state: Done" in content
    assert "state_change — Running → Done" in content

    # Verify full event stream order
    events = [line for line in content.split("\n") if line.startswith("- [")]
    assert len(events) == 4
    assert "created" in events[0]
    assert "Todo → Running" in events[1]
    assert "读了 auth.py" in events[2]
    assert "Running → Done" in events[3]


# ── Scenario 4: skill-driven evaluation ──────────────────────────────

def test_scenario_evaluate_job():
    """User says: '评估一下 JOB-001' → agent calls supervisor_evaluate.

    Evaluation is skill-driven: eval_skill='design-alignment' is the name of
    the evaluator skill; eval_result='Pass' is its conclusion.
    The result is appended as an immutable eval event.
    """
    supervisor_create("任务B", "做点什么", skills=["code-review"])
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    # Simulate: evaluator skill 'design-alignment' concluded 'NeedClarify'
    result = supervisor_evaluate(job_id, "design-alignment", "NeedClarify")
    assert "Evaluated" in result

    content = supervisor_read(job_id)
    assert "eval — design-alignment: NeedClarify" in content

    # Human intervenes, then second evaluator says Pass
    supervisor_update(job_id, append_log="人类补充了设计文档")
    supervisor_evaluate(job_id, "security-check", "Pass")

    content = supervisor_read(job_id)
    events = [line for line in content.split("\n") if line.startswith("- [")]
    assert len(events) == 4
    assert "eval — design-alignment: NeedClarify" in events[1]
    assert "人类补充了设计文档" in events[2]
    assert "eval — security-check: Pass" in events[3]


# ── Scenario 5: board summary with mixed states ──────────────────────────

def test_scenario_board_with_mixed_states():
    """Multiple jobs in different states → board_status groups them."""
    supervisor_create("任务 Todo", "等待中")
    supervisor_create("任务 Running", "进行中")
    supervisor_create("任务 Blocked", "卡住了")
    supervisor_create("任务 Done", "已完成")

    index = json.loads(INDEX_FILE.read_text())
    ids = list(index["jobs"].keys())

    supervisor_update(ids[1], state="Running")
    supervisor_update(ids[2], state="Blocked")
    supervisor_update(ids[3], state="Done")

    status = supervisor_status()
    assert "## Todo (1)" in status
    assert "## Running (1)" in status
    assert "## Blocked (1)" in status
    assert "## Done (1)" in status
    assert ids[0] in status
    assert ids[1] in status
    assert ids[2] in status
    assert ids[3] in status


# ── Scenario 6: full lifecycle from creation to archival ──────────────────

def test_scenario_full_lifecycle():
    """End-to-end: create → run → evaluate → read full history → delete.

    This is the 'complete file' test: after all operations, the job file
    must be a self-contained document that a human can read and understand
    without any external context.
    """
    result = supervisor_create(
        title="重构 auth 模块",
        description="将 SSO 逻辑拆分成独立模块，保持向后兼容。",
        skills=["code-review", "refactor"],
    )
    job_id = result.split(":")[0].replace("Created ", "")

    # Worker lifecycle
    supervisor_update(job_id, state="Running")
    supervisor_update(job_id, append_log="分析 auth.py 依赖")
    supervisor_update(job_id, append_log="创建 auth/sso.py")
    supervisor_update(job_id, append_log="迁移逻辑 + 测试通过")
    supervisor_update(job_id, state="Done")

    # Evaluator lifecycle
    supervisor_evaluate(job_id, "design-alignment", "Pass")
    supervisor_evaluate(job_id, "security-check", "Pass")

    # Read complete file
    content = supervisor_read(job_id)

    # Verify it is a complete, standalone document
    assert content.startswith("---")
    assert "id: " + job_id in content
    assert "title: 重构 auth 模块" in content
    assert "skills:" in content
    assert "  - code-review" in content
    assert "  - refactor" in content
    assert "state: Done" in content

    # Verify event stream completeness
    assert "## 任务描述" in content
    assert "将 SSO 逻辑拆分成独立模块" in content

    assert "## 事件流" in content
    events = [line for line in content.split("\n") if line.startswith("- [")]
    assert len(events) == 8  # created + state_change + 3 logs + state_change + 2 evals
    assert "created — state=Todo" in events[0]
    assert "state_change — Todo → Running" in events[1]
    assert "分析 auth.py" in events[2]
    assert "创建 auth/sso.py" in events[3]
    assert "迁移逻辑" in events[4]
    assert "state_change — Running → Done" in events[5]
    assert "eval — design-alignment: Pass" in events[6]
    assert "eval — security-check: Pass" in events[7]

    # Delete and verify cleanup
    supervisor_delete(job_id)
    assert not (JOBS_DIR / f"{job_id}.md").exists()
    index = json.loads(INDEX_FILE.read_text())
    assert job_id not in index["jobs"]

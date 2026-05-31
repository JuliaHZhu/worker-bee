"""Integration tests for job_supervisor skill — full lifecycle with checkpoints."""

import json
import re
import shutil

import pytest

from tools.job_supervisor import (
    job_supervisor_status,
    job_supervisor_read,
    job_supervisor_create,
    job_supervisor_update,
    job_supervisor_checkpoint,
    job_supervisor_self_check,
    job_supervisor_evaluate,
    job_supervisor_delete,
    JOBS_DIR,
    INDEX_FILE,
)


@pytest.fixture(autouse=True)
def clean_jobs_dir():
    if JOBS_DIR.exists():
        shutil.rmtree(JOBS_DIR)
    JOBS_DIR.mkdir()
    yield


def test_scenario_empty_board():
    result = job_supervisor_status()
    assert "empty" in result.lower()


def test_scenario_create_job_with_four_elements():
    result = job_supervisor_create(
        title="修复 SSO 回调 URL 硬编码",
        description="auth.py 中的 callback_url 写死在第 42 行，需要改成配置化。",
        skills=["code-review"],
        owner="agent-001",
        reviewer="human",
        deliverables=["auth/sso.py", "tests/test_sso.py"],
        acceptance=["向后兼容", "覆盖率>80%"],
    )
    assert result.startswith("Created JOB-")
    job_id = result.split(":")[0].replace("Created ", "")

    path = JOBS_DIR / f"{job_id}.md"
    content = path.read_text()

    # Four elements
    assert "owner: agent-001" in content
    assert "reviewer: human" in content
    assert "- [ ] auth/sso.py" in content
    assert "- [ ] 向后兼容" in content

    # Event stream
    assert "created — state=Todo" in content

    # Index
    index = json.loads(INDEX_FILE.read_text())
    assert index["jobs"][job_id]["phase"] == "created"


def test_scenario_full_lifecycle_with_checkpoints():
    """End-to-end: create → confirmed → planned → executing → self_checked → reviewed → done."""
    result = job_supervisor_create(
        title="重构 auth 模块",
        description="将 SSO 逻辑拆分成独立模块，保持向后兼容。",
        skills=["code-review", "refactor"],
        owner="agent-001",
        reviewer="human",
        deliverables=["auth/sso.py", "tests/test_sso.py", "migration_guide.md"],
        acceptance=["向后兼容", "测试覆盖率>80%", "不改 public API"],
    )
    job_id = result.split(":")[0].replace("Created ", "")

    # Phase 2: confirmed
    job_supervisor_checkpoint(job_id, "confirmed", "agent-001", "理解了任务和交付标准")

    # Phase 3: planned
    job_supervisor_checkpoint(job_id, "planned", "agent-001", "方案：先迁移函数，再补测试")

    # Phase 4: executing
    job_supervisor_update(job_id, state="Running")
    job_supervisor_update(job_id, append_log="分析 auth.py 依赖")
    job_supervisor_update(job_id, append_log="创建 auth/sso.py")
    job_supervisor_update(job_id, append_log="迁移逻辑 + 测试通过")

    # Phase 5: self_checked
    job_supervisor_self_check(
        job_id,
        deliverables_done=["auth/sso.py", "tests/test_sso.py", "migration_guide.md"],
        acceptance_passed=["向后兼容", "测试覆盖率>80%", "不改 public API"],
    )

    # Phase 6: reviewed
    job_supervisor_checkpoint(job_id, "reviewed", "human", "验收通过")
    job_supervisor_evaluate(job_id, "design-alignment", "Pass")

    # Phase 7: done
    job_supervisor_checkpoint(job_id, "done", "system", "archived")
    job_supervisor_update(job_id, state="Done")

    # Verify complete file
    content = job_supervisor_read(job_id)

    # Frontmatter
    assert "state: Done" in content
    assert "phase: done" in content
    assert "owner: agent-001" in content

    # Checklists updated
    assert "- [x] auth/sso.py" in content
    assert "- [x] 向后兼容" in content

    # Event stream: only lines with timestamps (not checklist items)
    events = [line for line in content.split("\n") if re.match(r"^- \[\d{2}:\d{2}\]", line)]
    assert len(events) == 12  # created + confirmed + planned + state_change + 3 logs + self_check + checkpoint + eval + checkpoint + state_change

    assert "created — state=Todo" in events[0]
    assert "checkpoint — phase=confirmed" in events[1]
    assert "checkpoint — phase=planned" in events[2]
    assert "state_change — Todo → Running" in events[3]
    assert "分析 auth.py" in events[4]
    assert "self_check — deliverables 3/3, acceptance 3/3" in events[7]
    assert "checkpoint — phase=reviewed" in events[8]
    assert "eval — design-alignment: Pass" in events[9]
    assert "checkpoint — phase=done" in events[10]
    assert "state_change — Running → Done" in events[11]

    # Cleanup
    job_supervisor_delete(job_id)
    assert not (JOBS_DIR / f"{job_id}.md").exists()


def test_scenario_board_with_mixed_phases():
    job_supervisor_create("任务 Todo", "等待中")
    job_supervisor_create("任务 Running", "进行中")
    job_supervisor_create("任务 Blocked", "卡住了")
    job_supervisor_create("任务 Done", "已完成")

    index = json.loads(INDEX_FILE.read_text())
    ids = list(index["jobs"].keys())

    job_supervisor_update(ids[1], state="Running")
    job_supervisor_checkpoint(ids[1], "executing", "agent-001")
    job_supervisor_update(ids[2], state="Blocked")
    job_supervisor_update(ids[3], state="Done")

    status = job_supervisor_status()
    assert "## Todo (1)" in status
    assert "## Running (1)" in status
    assert "(executing)" in status
    assert "## Blocked (1)" in status
    assert "## Done (1)" in status


def test_scenario_evaluate_then_human_review():
    job_supervisor_create("任务B", "做点什么", skills=["code-review"])
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    # First evaluator says NeedClarify
    job_supervisor_evaluate(job_id, "design-alignment", "NeedClarify")

    # Human clarifies
    job_supervisor_update(job_id, append_log="人类补充了设计文档")
    job_supervisor_checkpoint(job_id, "confirmed", "human", "补充了设计限制")

    # Second evaluator says Pass
    job_supervisor_evaluate(job_id, "security-check", "Pass")

    content = job_supervisor_read(job_id)
    events = [line for line in content.split("\n") if line.startswith("- [")]
    assert len(events) == 5
    assert "eval — design-alignment: NeedClarify" in events[1]
    assert "人类补充了设计文档" in events[2]
    assert "eval — security-check: Pass" in events[4]

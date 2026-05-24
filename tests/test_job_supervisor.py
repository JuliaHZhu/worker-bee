"""Tests for job_supervisor toolset."""
import json
import shutil
from pathlib import Path

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


def test_status_empty_board():
    assert "empty" in job_supervisor_status().lower()


def test_create_job_with_four_elements():
    result = job_supervisor_create(
        title="Fix auth",
        description="SSO callback broken",
        skills=["code-review"],
        owner="agent-001",
        reviewer="human",
        deliverables=["auth/sso.py", "tests/test_sso.py"],
        acceptance=["向后兼容", "覆盖率>80%"],
    )
    assert result.startswith("Created JOB-")
    job_id = result.split(":")[0].replace("Created ", "")
    path = JOBS_DIR / f"{job_id}.md"
    assert path.exists()
    content = path.read_text()
    assert "owner: agent-001" in content
    assert "reviewer: human" in content
    assert "- [ ] auth/sso.py" in content
    assert "- [ ] 向后兼容" in content
    assert "phase: created" in content
    assert "created — state=Todo" in content


def test_create_increments_id():
    r1 = job_supervisor_create("A", "desc")
    r2 = job_supervisor_create("B", "desc")
    id1 = r1.split(":")[0].replace("Created ", "")
    id2 = r2.split(":")[0].replace("Created ", "")
    assert id2 > id1


def test_status_shows_phase_and_owner():
    job_supervisor_create("Task A", "do A", owner="agent-001")
    status = job_supervisor_status()
    assert "Task A" in status
    assert "@agent-001" in status


def test_read_existing_job():
    job_supervisor_create("Task A", "do A")
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]
    content = job_supervisor_read(job_id)
    assert "Task A" in content
    assert "交付物" in content
    assert "验收标准" in content


def test_read_missing_job():
    assert "not found" in job_supervisor_read("JOB-999")


def test_update_state_appends_event():
    job_supervisor_create("Task A", "do A")
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    result = job_supervisor_update(job_id, state="Running")
    assert "Updated" in result

    content = job_supervisor_read(job_id)
    assert "state: Running" in content
    assert "state_change — Todo → Running" in content


def test_checkpoint_records_phase():
    job_supervisor_create("Task A", "do A")
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    result = job_supervisor_checkpoint(job_id, "confirmed", "agent-001", "understood")
    assert "Checkpoint" in result

    content = job_supervisor_read(job_id)
    assert "phase: confirmed" in content
    assert "checkpoint — phase=confirmed, who=agent-001, note=understood" in content


def test_checkpoint_invalid_phase_rejected():
    job_supervisor_create("Task A", "do A")
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    result = job_supervisor_checkpoint(job_id, "invalid", "agent-001")
    assert "Error" in result


def test_self_check_updates_checklists():
    job_supervisor_create(
        "Task A", "do A",
        deliverables=["file.py"],
        acceptance=["test passes"],
    )
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    result = job_supervisor_self_check(
        job_id,
        deliverables_done=["file.py"],
        acceptance_passed=["test passes"],
    )
    assert "Self-check" in result

    content = job_supervisor_read(job_id)
    assert "- [x] file.py" in content
    assert "- [x] test passes" in content
    assert "phase: self_checked" in content
    assert "self_check — deliverables 1/1, acceptance 1/1" in content


def test_evaluate_appends_event():
    job_supervisor_create("Task B", "do B")
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    result = job_supervisor_evaluate(job_id, "design-alignment", "Pass")
    assert "Evaluated" in result

    content = job_supervisor_read(job_id)
    assert "eval — design-alignment: Pass" in content


def test_delete_job():
    job_supervisor_create("Task A", "do A")
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    result = job_supervisor_delete(job_id)
    assert "Deleted" in result
    assert not (JOBS_DIR / f"{job_id}.md").exists()

    index = json.loads(INDEX_FILE.read_text())
    assert job_id not in index["jobs"]


def test_self_check_filters_unknown_items():
    """P1: deliverables_done with items not in expected list → filtered."""
    job_supervisor_create(
        "Task A", "do A",
        deliverables=["file.py"],
        acceptance=["test passes"],
    )
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    result = job_supervisor_self_check(
        job_id,
        deliverables_done=["file.py", "extra.py"],
        acceptance_passed=["test passes", "extra check"],
    )
    # Should report 1/1 not 2/1
    assert "deliverables 1/1" in result
    assert "acceptance 1/1" in result

    content = job_supervisor_read(job_id)
    assert "self_check — deliverables 1/1, acceptance 1/1" in content
    # Only expected items are checked
    assert "- [x] file.py" in content
    assert "- [ ] extra.py" not in content  # never existed


def test_index_recovery_after_deletion():
    """P0: _index.json deleted → next create scans disk, no ID collision."""
    # Create two jobs
    r1 = job_supervisor_create("First", "desc")
    id1 = r1.split(":")[0].replace("Created ", "")
    r2 = job_supervisor_create("Second", "desc")
    id2 = r2.split(":")[0].replace("Created ", "")

    # Delete index
    INDEX_FILE.unlink()
    assert not INDEX_FILE.exists()

    # Create third job → should scan disk, get JOB-003 not JOB-001
    r3 = job_supervisor_create("Third", "desc")
    id3 = r3.split(":")[0].replace("Created ", "")
    assert id3 == "JOB-003"

    # Verify old jobs still exist
    assert (JOBS_DIR / f"{id1}.md").exists()
    assert (JOBS_DIR / f"{id2}.md").exists()
    assert (JOBS_DIR / f"{id3}.md").exists()


def test_delete_missing_job():
    assert "not found" in job_supervisor_delete("JOB-999")

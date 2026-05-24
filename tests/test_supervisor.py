"""Tests for supervisor toolset."""
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


def test_status_empty_board():
    assert "empty" in supervisor_status().lower()


def test_create_job_returns_id():
    result = supervisor_create("Fix auth", "SSO callback broken", skills=["code-review"])
    assert result.startswith("Created JOB-")
    job_id = result.split(":")[0].replace("Created ", "")
    path = JOBS_DIR / f"{job_id}.md"
    assert path.exists()
    content = path.read_text()
    assert "Fix auth" in content
    assert "code-review" in content
    assert "state: Todo" in content
    assert "事件流" in content
    assert "created — state=Todo" in content


def test_create_increments_id():
    r1 = supervisor_create("A", "desc")
    r2 = supervisor_create("B", "desc")
    id1 = r1.split(":")[0].replace("Created ", "")
    id2 = r2.split(":")[0].replace("Created ", "")
    assert id2 > id1


def test_status_shows_jobs():
    supervisor_create("Task A", "do A")
    supervisor_create("Task B", "do B", skills=["web-research"])
    status = supervisor_status()
    assert "Task A" in status
    assert "Task B" in status
    assert "Todo" in status


def test_read_existing_job():
    supervisor_create("Task A", "do A")
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]
    content = supervisor_read(job_id)
    assert "Task A" in content
    assert "任务描述" in content
    assert "事件流" in content


def test_read_missing_job():
    assert "not found" in supervisor_read("JOB-999")


def test_update_state_appends_event():
    supervisor_create("Task A", "do A")
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    result = supervisor_update(job_id, state="Running")
    assert "Updated" in result

    content = supervisor_read(job_id)
    assert "state: Running" in content
    assert "state_change — Todo → Running" in content


def test_update_append_log():
    supervisor_create("Task A", "do A")
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    supervisor_update(job_id, append_log="started work")
    content = supervisor_read(job_id)
    assert "log — started work" in content


def test_evaluate_appends_event():
    supervisor_create("Task A", "do A")
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    result = supervisor_evaluate(job_id, "design-alignment", "Pass")
    assert "Evaluated" in result

    content = supervisor_read(job_id)
    assert "eval — design-alignment: Pass" in content


def test_multiple_events_preserved():
    supervisor_create("Task A", "do A")
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    supervisor_update(job_id, state="Running")
    supervisor_update(job_id, append_log="step 1 done")
    supervisor_update(job_id, state="Done")
    supervisor_evaluate(job_id, "security-check", "NeedClarify")

    content = supervisor_read(job_id)
    events = [line for line in content.split("\n") if line.startswith("- [")]
    assert len(events) == 5  # created + state_change + log + state_change + eval
    assert "created" in events[0]
    assert "state_change — Todo → Running" in events[1]
    assert "log — step 1 done" in events[2]
    assert "state_change — Running → Done" in events[3]
    assert "eval — security-check: NeedClarify" in events[4]


def test_delete_job():
    supervisor_create("Task A", "do A")
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    result = supervisor_delete(job_id)
    assert "Deleted" in result
    assert not (JOBS_DIR / f"{job_id}.md").exists()

    index = json.loads(INDEX_FILE.read_text())
    assert job_id not in index["jobs"]


def test_delete_missing_job():
    assert "not found" in supervisor_delete("JOB-999")

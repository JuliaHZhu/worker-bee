"""Tests for supervisor toolset."""
import json
import shutil
import time
from pathlib import Path

import pytest

from tools.supervisor import (
    supervisor_status,
    supervisor_read,
    supervisor_create,
    supervisor_update,
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
    # leave teardown to next test's setup


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
    # find the id from index
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]
    content = supervisor_read(job_id)
    assert "Task A" in content
    assert "## 任务描述" in content


def test_read_missing_job():
    assert "not found" in supervisor_read("JOB-999")


def test_update_state():
    supervisor_create("Task A", "do A")
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    result = supervisor_update(job_id, state="Running")
    assert "Updated" in result

    content = supervisor_read(job_id)
    assert "state: Running" in content


def test_update_append_log():
    supervisor_create("Task A", "do A")
    index = json.loads(INDEX_FILE.read_text())
    job_id = list(index["jobs"].keys())[0]

    supervisor_update(job_id, append_log="started work")
    content = supervisor_read(job_id)
    assert "started work" in content


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

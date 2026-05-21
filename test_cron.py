#!/usr/bin/env python3
"""Quick smoke test for the cron subsystem."""

import json
import os
import shutil
import sys
import tempfile
import time

# Patch HERMES_DIR to a temp dir so we don't touch real data
from pathlib import Path
TEST_DIR = Path(tempfile.mkdtemp(prefix="hermes-lite-test-"))

import cron.jobs as jobs
jobs.HERMES_DIR = TEST_DIR
jobs.CRON_DIR = TEST_DIR / "cron"
jobs.JOBS_FILE = jobs.CRON_DIR / "jobs.json"
jobs.OUTPUT_DIR = jobs.CRON_DIR / "output"
jobs.ensure_dirs()


def test_create_and_list():
    print("--- test_create_and_list ---")
    job = jobs.create_job(
        prompt="Say hello",
        schedule="5m",
        name="hello-test",
    )
    print(f"Created: {job['id']} — {job['name']}")
    assert job["schedule"]["kind"] == "once"
    assert job["repeat"]["times"] == 1

    all_jobs = jobs.list_jobs()
    assert len(all_jobs) == 1
    print(f"Listed: {len(all_jobs)} job(s)")
    print("PASS\n")


def test_recurring():
    print("--- test_recurring ---")
    job = jobs.create_job(
        prompt="Heartbeat",
        schedule="every 10m",
        name="heartbeat",
    )
    assert job["schedule"]["kind"] == "interval"
    assert job["repeat"]["times"] is None
    print(f"Recurring job next_run_at: {job['next_run_at']}")
    print("PASS\n")


def test_resolve_and_trigger():
    print("--- test_resolve_and_trigger ---")
    job = jobs.create_job(
        prompt="Trigger me",
        schedule="1h",
        name="triggerable",
    )
    ref = jobs.resolve_job_ref(job["id"])
    assert ref is not None
    assert ref["id"] == job["id"]

    # Trigger (run now)
    updated = jobs.trigger_job(job["id"])
    assert updated is not None
    assert updated["next_run_at"] is not None
    print(f"Triggered, next_run_at: {updated['next_run_at']}")

    # Pause / resume
    paused = jobs.pause_job(job["id"], reason="testing")
    assert paused["state"] == "paused"
    print(f"Paused: {paused['state']}")

    resumed = jobs.resume_job(job["id"])
    assert resumed["state"] == "scheduled"
    print(f"Resumed: {resumed['state']}")
    print("PASS\n")


def test_due_jobs():
    print("--- test_due_jobs ---")
    # Create a job scheduled for now
    job = jobs.create_job(
        prompt="Run now",
        schedule="0m",  # should be due immediately
        name="due-now",
    )
    # The job should be due
    due = jobs.get_due_jobs()
    ids = [j["id"] for j in due]
    assert job["id"] in ids, f"Expected {job['id']} in due jobs, got {ids}"
    print(f"Due jobs: {len(due)} — includes {job['id']}")
    print("PASS\n")


def test_remove():
    print("--- test_remove ---")
    job = jobs.create_job(
        prompt="Remove me",
        schedule="1d",
        name="removable",
    )
    ok = jobs.remove_job(job["id"])
    assert ok
    assert jobs.get_job(job["id"]) is None
    print(f"Removed {job['id']}")
    print("PASS\n")


def test_cron_tool():
    print("--- test_cron_tool ---")
    from tools.cronjob import cronjob

    # Create via tool
    result = cronjob(
        action="create",
        prompt="Tool test",
        schedule="30m",
        name="tool-test",
        deliver="local",
    )
    data = json.loads(result)
    assert data["success"]
    job_id = data["job_id"]
    print(f"Tool created: {job_id}")

    # List via tool
    result = cronjob(action="list")
    data = json.loads(result)
    assert data["success"]
    print(f"Tool listed: {data['count']} job(s)")

    # Trigger via tool
    result = cronjob(action="run", job_id=job_id)
    data = json.loads(result)
    assert data["success"]
    print(f"Tool triggered: {data['job']['next_run_at']}")

    # Remove via tool
    result = cronjob(action="remove", job_id=job_id)
    data = json.loads(result)
    assert data["success"]
    print(f"Tool removed: {job_id}")
    print("PASS\n")


def test_scheduler_tick():
    print("--- test_scheduler_tick ---")
    from cron import scheduler

    # Create a due job with no_agent + script that just prints something
    script_path = TEST_DIR / "hello.sh"
    script_path.write_text("#!/bin/bash\necho 'Hello from cron script'", encoding="utf-8")
    os.chmod(script_path, 0o755)

    job = jobs.create_job(
        prompt="",
        schedule="0m",
        name="scheduler-test",
        no_agent=True,
        script=str(script_path),
    )

    # Mock config
    config = {
        "model": "test-model",
        "provider": "test",
        "api_key": "test-key",
        "base_url": "https://example.com",
        "max_iterations": 5,
        "system_prompt": "test",
        "tools": [],
    }

    count = scheduler.tick(config)
    print(f"Scheduler tick executed {count} job(s)")
    assert count >= 1

    # Check output was saved
    outputs = list(jobs.OUTPUT_DIR.glob(f"{job['id']}/*.md"))
    assert len(outputs) > 0, "Expected output file to be created"
    content = outputs[0].read_text(encoding="utf-8")
    assert "Hello from cron script" in content
    print(f"Output saved: {outputs[0].name}")
    print("PASS\n")


def cleanup():
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    print(f"Cleaned up {TEST_DIR}")


if __name__ == "__main__":
    try:
        test_create_and_list()
        test_recurring()
        test_resolve_and_trigger()
        test_due_jobs()
        test_remove()
        test_cron_tool()
        test_scheduler_tick()
        print("=" * 40)
        print("All tests PASSED ✅")
    except Exception as e:
        print(f"FAILED ❌: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cleanup()

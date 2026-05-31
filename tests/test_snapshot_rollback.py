"""Tests for snapshot / rollback mechanism in tools/file.py."""


from tools.file import (
    fs_write_file,
    fs_rollback_file,
    save_snapshot,
    _snapshot_path,
)


class TestSnapshot:
    def test_snapshot_created_on_write(self, tmp_path, monkeypatch):
        import tools.file
        monkeypatch.setattr(tools.file, "_SNAPSHOT_DIR", tmp_path / "snapshots")
        monkeypatch.setattr(tools.file, "_WORKSPACE", str(tmp_path))

        target = tmp_path / "doc.txt"
        target.write_text("original")
        fs_write_file(str(target), "modified")
        snap = _snapshot_path(str(target))
        assert snap.exists()
        assert snap.read_text() == "original"

    def test_no_snapshot_for_new_file(self, tmp_path, monkeypatch):
        import tools.file
        monkeypatch.setattr(tools.file, "_SNAPSHOT_DIR", tmp_path / "snapshots")
        monkeypatch.setattr(tools.file, "_WORKSPACE", str(tmp_path))

        target = tmp_path / "newfile.txt"
        fs_write_file(str(target), "hello")
        snap = _snapshot_path(str(target))
        assert not snap.exists()

    def test_snapshot_overwrites_previous(self, tmp_path, monkeypatch):
        import tools.file
        monkeypatch.setattr(tools.file, "_SNAPSHOT_DIR", tmp_path / "snapshots")
        monkeypatch.setattr(tools.file, "_WORKSPACE", str(tmp_path))

        target = tmp_path / "versioned.txt"
        target.write_text("v1")
        fs_write_file(str(target), "v2")
        fs_write_file(str(target), "v3")
        snap = _snapshot_path(str(target))
        assert snap.read_text() == "v2"  # snapshot of v2 before v3 write

    def test_save_snapshot_explicit(self, tmp_path, monkeypatch):
        import tools.file
        monkeypatch.setattr(tools.file, "_SNAPSHOT_DIR", tmp_path / "snapshots")

        target = tmp_path / "manual.txt"
        target.write_text("before")
        save_snapshot(str(target))
        snap = _snapshot_path(str(target))
        assert snap.exists()
        assert snap.read_text() == "before"


class TestRollback:
    def test_rollback_restores_content(self, tmp_path, monkeypatch):
        import tools.file
        monkeypatch.setattr(tools.file, "_SNAPSHOT_DIR", tmp_path / "snapshots")
        monkeypatch.setattr(tools.file, "_WORKSPACE", str(tmp_path))

        target = tmp_path / "doc.txt"
        target.write_text("original")
        fs_write_file(str(target), "modified")
        assert target.read_text() == "modified"

        result = fs_rollback_file(str(target))
        assert "Rolled back" in result
        assert target.read_text() == "original"

    def test_rollback_no_snapshot(self, tmp_path, monkeypatch):
        import tools.file
        monkeypatch.setattr(tools.file, "_SNAPSHOT_DIR", tmp_path / "snapshots")

        target = tmp_path / "nosnap.txt"
        target.write_text("whatever")
        result = fs_rollback_file(str(target))
        assert "No snapshot found" in result

    def test_rollback_creates_parent_dirs(self, tmp_path, monkeypatch):
        import tools.file
        monkeypatch.setattr(tools.file, "_SNAPSHOT_DIR", tmp_path / "snapshots")
        monkeypatch.setattr(tools.file, "_WORKSPACE", str(tmp_path))

        target = tmp_path / "deep" / "nested" / "file.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("deep original")
        fs_write_file(str(target), "deep modified")

        # Delete the file (simulate corruption)
        target.unlink()
        result = fs_rollback_file(str(target))
        assert "Rolled back" in result
        assert target.read_text() == "deep original"

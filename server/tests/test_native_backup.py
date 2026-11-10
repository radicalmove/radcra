import importlib.util
from pathlib import Path
import tarfile

import pytest


def module():
    spec = importlib.util.spec_from_file_location(
        "backup_native", Path(__file__).resolve().parents[2] / "deploy/scripts/backup-native.py"
    )
    backup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backup)
    return backup


def test_attachment_archive_includes_only_snapshot_objects(tmp_path):
    storage = tmp_path / "files"
    storage.mkdir()
    name = "a" * 32 + ".png"
    (storage / name).write_bytes(b"sample")
    (storage / "orphan").write_bytes(b"not referenced")
    archive = tmp_path / "backup.tar.gz"
    module().archive_attachments(storage, [(name, 6)], archive)
    with tarfile.open(archive) as tar:
        assert tar.getnames() == ["attachments", f"attachments/{name}"]
        assert tar.extractfile(f"attachments/{name}").read() == b"sample"


@pytest.mark.parametrize("bad", ["missing", "symlink", "wrong-size", "traversal"])
def test_invalid_snapshot_object_prevents_backup(tmp_path, bad):
    storage = tmp_path / "files"
    storage.mkdir()
    name = "a" * 32 + ".png"
    if bad == "symlink":
        other = tmp_path / "other"
        other.write_bytes(b"sample")
        (storage / name).symlink_to(other)
    elif bad == "wrong-size":
        (storage / name).write_bytes(b"bad")
    elif bad == "traversal":
        name = "../other"
    with pytest.raises((ValueError, OSError)):
        module().archive_attachments(storage, [(name, 6)], tmp_path / "backup.tar.gz")

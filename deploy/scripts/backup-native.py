"""Publish a private, snapshot-consistent native Sphere backup without downtime."""

import argparse
from datetime import UTC, datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tarfile
from tempfile import TemporaryDirectory

from dotenv import dotenv_values
from psycopg import connect
from sqlalchemy.engine import make_url

PG = Path("/usr/lib/postgresql/16/bin")
OPTIONS = "-c default_transaction_read_only=on -c lock_timeout=5000 -c statement_timeout=300000"


def archive_attachments(storage, rows, archive):
    with tarfile.open(archive, "w:gz") as tar:
        directory = tarfile.TarInfo("attachments")
        directory.type, directory.mode = tarfile.DIRTYPE, 0o700
        tar.addfile(directory)
        for name, size in rows:
            if not re.fullmatch(r"[a-f0-9]{32}\.(png|jpg|pdf|docx?)", name):
                raise ValueError("Invalid attachment object name")
            fd = os.open(storage / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, "rb") as source:
                st = os.fstat(source.fileno())
                if not stat.S_ISREG(st.st_mode) or st.st_size != size:
                    raise ValueError("Attachment does not match the database snapshot")
                item = tarfile.TarInfo(f"attachments/{name}")
                item.size, item.mode = size, 0o600
                tar.addfile(item, source)


def sync(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def backup(server, destination):
    config = dotenv_values(server / ".env", interpolate=False)
    url = make_url(config["DATABASE_URL"])
    if (url.get_backend_name() != "postgresql" or url.host not in {"localhost", "127.0.0.1", None}
            or not url.database or url.query):
        raise ValueError("Expected a local native PostgreSQL database")
    storage = (server / Path(config.get("ATTACHMENT_STORAGE_DIR") or "var/attachments").expanduser()).resolve()
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    mode = destination.stat()
    if destination.is_symlink() or mode.st_uid != os.getuid() or mode.st_mode & 0o077:
        raise ValueError("Backup destination must be private and owned by the service user")
    pg_env = {"PATH": os.defpath, "PGCONNECT_TIMEOUT": "5", "PGOPTIONS": OPTIONS}
    params = dict(dbname=url.database, host=url.host, user=url.username, password=url.password, port=url.port)
    params = {key: value for key, value in params.items() if value is not None}
    for key, pg_key in dict(dbname="PGDATABASE", host="PGHOST", user="PGUSER", password="PGPASSWORD", port="PGPORT").items():
        if key in params:
            pg_env[pg_key] = str(params[key])
    with (destination / ".native-backup.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        created = datetime.now(UTC)
        final = destination / created.strftime("%Y%m%dT%H%M%S.%fZ-native")
        with TemporaryDirectory(prefix=".native-", dir=destination) as name:
            stage = Path(name)
            with connect(**params, options=OPTIONS, connect_timeout=5) as db:
                db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                snapshot = db.execute("SELECT pg_export_snapshot()").fetchone()[0]
                revisions = [row[0] for row in db.execute("SELECT version_num FROM alembic_version")]
                rows = db.execute("SELECT object_name, size_bytes FROM attachments ORDER BY object_name").fetchall()
                counts = {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                          for table in ("users", "courses", "course_memberships", "comments", "attachments")}
                archive_attachments(storage, rows, stage / "attachments.tar.gz")
                subprocess.run([PG / "pg_dump", "--format=custom", "--no-owner", "--no-acl",
                                "--snapshot", snapshot, "--file", stage / "database.dump"],
                               env=pg_env, check=True, timeout=360)
            subprocess.run([PG / "pg_restore", "--list", stage / "database.dump"],
                           stdout=subprocess.DEVNULL, check=True, timeout=30)
            (stage / "manifest.json").write_text(json.dumps({
                "created_utc": created.isoformat(), "revisions": revisions,
                "counts": counts, "format": "native-postgres-snapshot-v1",
            }, indent=2) + "\n")
            checksums = []
            for filename in ("database.dump", "attachments.tar.gz", "manifest.json"):
                with (stage / filename).open("rb") as handle:
                    checksums.append(f"{hashlib.file_digest(handle, 'sha256').hexdigest()}  {filename}\n")
                sync(stage / filename)
            (stage / "SHA256SUMS").write_text("".join(checksums))
            sync(stage / "SHA256SUMS")
            sync(stage)
            stage.rename(final)
            sync(destination)
        return final


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("server", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    print(f"Sphere native backup saved: {backup(args.server, args.destination)}")

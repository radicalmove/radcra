"""Operator-only rehearsal: run on the database host, never a test-suite import."""

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlsplit

from dotenv import dotenv_values
from psycopg import connect, sql
from sqlalchemy.engine import make_url

PG_BIN = Path("/usr/lib/postgresql/16/bin")
LIVE_CONFIG = Path("/home/fldadmin/beta-testing-app/server/.env")


def run(name, *args, env=None):
    subprocess.run([PG_BIN / name, *args], env=env, check=True, stdout=subprocess.DEVNULL)


def fingerprint(db, tables=None):
    if tables is None:
        tables = {}
        for table, column in db.execute("""
            SELECT table_name, column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name <> 'alembic_version'
            ORDER BY ordinal_position
        """):
            if table != "courses" or column not in {"moodle_origin", "moodle_course_id"}:
                tables.setdefault(table, []).append(column)
    report = {}
    for table, columns in tables.items():
        query = sql.SQL("SELECT row_to_json(r)::text FROM (SELECT {} FROM {}) r").format(
            sql.SQL(",").join(map(sql.Identifier, columns)), sql.Identifier(table))
        hashes = sorted(hashlib.sha256(row.encode()).digest() for (row,) in db.execute(query))
        report[table] = (len(hashes), hashlib.sha256(b"".join(hashes)).digest())
    return tables, report


def main():
    source = make_url(dotenv_values(LIVE_CONFIG)["DATABASE_URL"])
    if source.get_backend_name() != "postgresql" or source.host not in {"localhost", "127.0.0.1", None}:
        raise SystemExit("Expected the configured local PostgreSQL source")
    pg_env = {"PATH": os.defpath, "PGOPTIONS": "-c default_transaction_read_only=on -c lock_timeout=5000",
              "PGCONNECT_TIMEOUT": "5"}
    for key, value in {"PGHOST": source.host, "PGPORT": source.port, "PGUSER": source.username,
                       "PGPASSWORD": source.password, "PGDATABASE": source.database}.items():
        if value is not None:
            pg_env[key] = str(value)
    with tempfile.TemporaryDirectory(prefix="sphere-upgrade-", dir="/tmp") as tmp:
        root = Path(tmp)
        dump = root / "snapshot.dump"
        data = root / "pg"
        # No production credentials are passed to any process except the read-only dump.
        run("pg_dump", "--format=custom", "--no-owner", "--no-acl", "--file", dump, env=pg_env)
        run("initdb", "--auth=peer", "--no-locale", "--encoding=UTF8", "-D", data)
        run("pg_ctl", "-D", data, "-o", f"-c listen_addresses= -k {tmp}", "-l", root / "pg.log", "-w", "start")
        try:
            run("createdb", "-h", tmp, "sphere_rehearsal")
            run("pg_restore", "--exit-on-error", "--no-owner", "--no-acl", "-h", tmp, "-d", "sphere_rehearsal", dump)
            target = f"postgresql:///sphere_rehearsal?host={tmp}"
            with connect(target) as db:
                before = db.execute("SELECT version_num FROM alembic_version").fetchall()
                tables, baseline = fingerprint(db)
            print("Source schema:", ", ".join(row[0] for row in before), flush=True)
            env = {"PATH": os.defpath, "DATABASE_URL": target.replace("postgresql:", "postgresql+psycopg:", 1)}
            subprocess.run([os.sys.executable, "-m", "alembic", "upgrade", "head"], env=env, check=True)
            with connect(target) as db:
                assert db.execute("SELECT version_num FROM alembic_version").fetchall() == [("20261110_17",)]
                _, migrated = fingerprint(db, tables)
                for table, original in baseline.items():
                    assert migrated[table] == original, f"Unexpected row change: {table}"
                rows = db.execute("SELECT moodle_course_id, moodle_origin, normalized_url FROM courses WHERE moodle_course_id IS NOT NULL")
                for course_id, origin, url in rows:
                    parsed = urlsplit(url)
                    expected = f"{parsed.scheme}://{parsed.hostname}"
                    if parsed.port not in (None, {"http": 80, "https": 443}[parsed.scheme]):
                        expected += f":{parsed.port}"
                    assert origin == expected and course_id == str(int(course_id)), "Invalid migrated course identity"
                for name, (count, _) in sorted(migrated.items()):
                    print(f"Preserved {name}: {count}", flush=True)
            subprocess.run([os.sys.executable, "-m", "tests.rehearse_sphere_permissions"], env=env, check=True)
        finally:
            run("pg_ctl", "-D", data, "-m", "fast", "-w", "stop")


if __name__ == "__main__":
    main()

"""Exercise revision 16 against a disposable revision-15-equivalent SQLite schema.

Earlier revisions include PostgreSQL-only ALTERs, so build the predecessor schema
from copied metadata with its original, unnamed global course-ID constraint.
"""
import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Comment, Course, PageLocation, User, UserRole
from app.security import utc_now
from app.services.access import create_invitation, redeem_invitation


@pytest.mark.parametrize("legacy_origin,legacy_id,unsafe_url,collision,error", [
    ("https://my.uconline.ac.nz", "3598", None, False, None),
    (None, "3598", None, False, None),
    ("HTTPS://MY.UCONLINE.AC.NZ:443", "3598", None, False, None),
    ("https://my.uconline.ac.nz", "03598", None, False, None),
    ("https://learn.canterbury.ac.nz", "3598", None, False, "mismatched"),
    ("https://user:password@my.uconline.ac.nz", "3598", None, False, "unsafe"),
    (None, "3598", "https://user:password@my.uconline.ac.nz/course/view.php?id=3598", False, "unsafe"),
    (None, "3598", "https://my.uconline.ac.nz:invalid/course/view.php?id=3598", False, "Port"),
    ("https://my.uconline.ac.nz", "3598", None, True, "collision"),
    ("https://my.uconline.ac.nz", "03598", None, "other-host", None),
    ("https://my.uconline.ac.nz", "000", None, False, "positive"),
])
def test_revision16_preserves_all_rows_and_references_and_allows_host_collision(tmp_path, legacy_origin, legacy_id, unsafe_url, collision, error):
    metadata = sa.MetaData()
    for table in Base.metadata.sorted_tables:
        table.to_metadata(metadata)
    courses = metadata.tables["courses"]
    for constraint in list(courses.constraints):
        if isinstance(constraint, sa.UniqueConstraint) and list(constraint.columns.keys()) in (["moodle_origin", "moodle_course_id"], ["moodle_course_id"]):
            courses.constraints.remove(constraint)
    courses.append_constraint(sa.UniqueConstraint("moodle_course_id"))
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'revision15.sqlite'}")
    metadata.create_all(engine)
    with Session(engine) as db:
        now = utc_now()
        admin = User(email="admin@example.test", password_hash="unused", role=UserRole.ADMIN, approved_at=now, created_at=now)
        uco = Course(moodle_course_id="3598", moodle_origin="https://my.uconline.ac.nz", normalized_url="https://my.uconline.ac.nz/course/view.php?id=3598", title="UCO", identity_title="uco", is_confirmed=True, confirmed_at=now, created_at=now)
        db.add_all([admin, uco])
        db.commit()
        _, invitation = create_invitation(db, admin, uco, "reviewer@example.test", UserRole.BETA_TESTER)
        joined = redeem_invitation(db, course_id=uco.id, display_name="Reviewer", email="reviewer@example.test", role=UserRole.BETA_TESTER, invitation_code=invitation)
        location = PageLocation(course_id=uco.id, page_url=uco.normalized_url, page_title="Page", anchor_type="text_highlight", created_at=now)
        db.add(location)
        db.flush()
        db.add(Comment(course_id=uco.id, location_id=location.id, author_user_id=joined.membership.user_id, body="Keep me", category="general", status="open", created_at=now, updated_at=now))
        uco.moodle_origin = legacy_origin
        uco.moodle_course_id = legacy_id
        if unsafe_url:
            uco.normalized_url = unsafe_url
        if collision:
            host = "https://learn.canterbury.ac.nz" if collision == "other-host" else "https://my.uconline.ac.nz"
            extra_id = "3598" if collision == "other-host" else "03598"
            db.add(Course(moodle_course_id=extra_id, moodle_origin=host, normalized_url=f"{host}/course/view.php?id={extra_id}", title="Collision", identity_title="collision", is_confirmed=True, created_at=now))
        db.commit()
    with engine.connect() as connection:
        before = {table.name: [dict(row) for row in connection.execute(sa.select(table)).mappings()] for table in metadata.sorted_tables}
    migration_path = Path("alembic/versions/20261110_16_course_origin_identity.py")
    assert migration_path.exists(), "revision 16 course identity migration is required"
    spec = importlib.util.spec_from_file_location("course_identity_revision16", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "20261107_15"
    if error:
        with engine.begin() as connection:
            constraints = sa.inspect(connection).get_unique_constraints("courses")
            with Operations.context(MigrationContext.configure(connection)):
                with pytest.raises(ValueError, match=error):
                    migration.upgrade()
            for table in metadata.sorted_tables:
                assert [dict(row) for row in connection.execute(sa.select(table)).mappings()] == before[table.name]
            assert sa.inspect(connection).get_unique_constraints("courses") == constraints
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        return
    before["courses"][0]["moodle_origin"] = "https://my.uconline.ac.nz"
    before["courses"][0]["moodle_course_id"] = "3598"
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        for table in metadata.sorted_tables:
            assert [dict(row) for row in connection.execute(sa.select(table)).mappings()] == before[table.name]
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    with Session(engine) as db:
        from app.services.courses import register_course
        learn = register_course(db, moodle_course_id=3598, course_url="https://learn.canterbury.ac.nz/course/view.php?id=3598", title="LEARN")
        assert learn.id != before["courses"][0]["id"]
        duplicate = Course(moodle_course_id="3598", moodle_origin=learn.moodle_origin, normalized_url="https://learn.canterbury.ac.nz/other", title="Duplicate", identity_title="duplicate", is_confirmed=True, created_at=utc_now())
        db.add(duplicate)
        with pytest.raises(sa.exc.IntegrityError):
            db.commit()
        db.rollback()
    # Downgrade must fail closed, not merge or delete equal-ID courses.
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            with pytest.raises(ValueError, match="duplicate"):
                migration.downgrade()
        assert connection.scalar(sa.select(sa.func.count()).select_from(courses)) == 2

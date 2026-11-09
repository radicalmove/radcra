"""Scope stable Moodle course identity to its origin, preserving UUIDs."""
from urllib.parse import urlsplit

from alembic import op
import sqlalchemy as sa

revision = "20261110_16"
down_revision = "20261107_15"
branch_labels = None
depends_on = None

_GLOBAL = "uq_courses_moodle_course_id"
_COMPOSITE = "uq_courses_moodle_origin_id"
_NAMING = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def _origin(value):
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("Cannot migrate unsafe Moodle course origin")
    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    port = parsed.port
    if port is not None and port != {"http": 80, "https": 443}[parsed.scheme]:
        host = f"{host}:{port}"
    return f"{parsed.scheme}://{host}"


def upgrade():
    # SQLite's original constraint is unnamed; reflection needs a naming
    # convention to drop it. PostgreSQL supplies its generated constraint name.
    connection = op.get_bind()
    courses = sa.table("courses", sa.column("id", sa.Uuid()), sa.column("moodle_course_id", sa.String()), sa.column("moodle_origin", sa.String()), sa.column("normalized_url", sa.Text()))
    updates = []
    for course in connection.execute(sa.select(courses).where(courses.c.moodle_course_id.is_not(None))).mappings():
        origin = _origin(course["normalized_url"])
        if course["moodle_origin"] is not None and _origin(course["moodle_origin"]) != origin:
            # A legacy origin move must be investigated, never guessed or merged.
            raise ValueError("Cannot migrate course with mismatched Moodle origin and URL")
        if course["moodle_origin"] != origin:
            updates.append((course["id"], origin))
    for course_id, origin in updates:
        connection.execute(courses.update().where(courses.c.id == course_id).values(moodle_origin=origin))
    unique = next(item for item in sa.inspect(connection).get_unique_constraints("courses")
                  if item["column_names"] == ["moodle_course_id"])
    with op.batch_alter_table("courses", naming_convention=_NAMING) as batch:
        batch.drop_constraint(unique["name"] or _GLOBAL, type_="unique")
        batch.create_unique_constraint(_COMPOSITE, ["moodle_origin", "moodle_course_id"])


def downgrade():
    connection = op.get_bind()
    duplicate = connection.execute(sa.text(
        "SELECT moodle_course_id FROM courses WHERE moodle_course_id IS NOT NULL "
        "GROUP BY moodle_course_id HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicate:
        raise ValueError("Cannot downgrade course identity while duplicate numeric IDs exist across origins")
    with op.batch_alter_table("courses", naming_convention=_NAMING) as batch:
        batch.drop_constraint(_COMPOSITE, type_="unique")
        batch.create_unique_constraint(_GLOBAL, ["moodle_course_id"])

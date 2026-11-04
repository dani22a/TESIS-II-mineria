"""DB-level append-only guard for audit_log (PostgreSQL and SQLite)."""
from sqlalchemy import text

PG = [
    """CREATE OR REPLACE FUNCTION audit_log_immutable() RETURNS trigger AS $$
       BEGIN RAISE EXCEPTION 'audit_log is append-only'; END; $$ LANGUAGE plpgsql""",
    "DROP TRIGGER IF EXISTS audit_log_no_change ON audit_log",
    """CREATE TRIGGER audit_log_no_change BEFORE UPDATE OR DELETE ON audit_log
       FOR EACH ROW EXECUTE FUNCTION audit_log_immutable()""",
    "DROP TRIGGER IF EXISTS audit_log_no_truncate ON audit_log",
    """CREATE TRIGGER audit_log_no_truncate BEFORE TRUNCATE ON audit_log
       FOR EACH STATEMENT EXECUTE FUNCTION audit_log_immutable()""",
]
SQLITE = [
    "DROP TRIGGER IF EXISTS audit_log_no_update",
    "DROP TRIGGER IF EXISTS audit_log_no_delete",
    """CREATE TRIGGER audit_log_no_update BEFORE UPDATE ON audit_log
       BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END""",
    """CREATE TRIGGER audit_log_no_delete BEFORE DELETE ON audit_log
       BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END""",
]


def install(conn) -> None:
    stmts = PG if conn.dialect.name == "postgresql" else SQLITE
    for s in stmts:
        conn.execute(text(s))

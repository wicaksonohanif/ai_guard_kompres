import os, sqlite3
from contextlib import contextmanager

BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..')
)

DB_PATH = os.getenv(
    'AI_GUARD_DB_PATH',
    os.path.join(BASE, 'data', 'ai_guard.db')
)

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    c = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )

    c.row_factory = sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    return c

@contextmanager
def get_db():
    c = get_connection()

    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def init_db():
    with get_db() as c:
        with open(
            os.path.join(os.path.dirname(__file__), 'schema.sql'),
            encoding='utf8'
        ) as f:
            c.executescript(f.read())
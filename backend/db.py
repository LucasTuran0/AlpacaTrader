from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.getenv("DB_DIR", BASE_DIR)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'alpaca_trader_v3.db')}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
)

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

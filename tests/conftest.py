import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from backend.db import Base


@pytest.fixture
def db_session():
    """In-memory SQLite session with all tables created."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

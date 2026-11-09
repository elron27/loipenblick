import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from loipen.models import Base


@pytest.fixture
def session() -> Session:
    """SQLite im Speicher reicht fuer Modell- und Logiktests."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s

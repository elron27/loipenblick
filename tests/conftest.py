"""Gemeinsame Test-Fixtures.

- Markierung @pytest.mark.req("P6", ak=2): schreibt die geprueften Anforderungen als
  JUnit-Eigenschaften reqseq:element / reqseq:criterion. `reqseq evidence enrich-junit`
  macht daraus Nachweise in ReqSeq (siehe Testkonzept).
- Kein Test darf ins Netz: echte Verbindungen ausser zur lokalen Datenbank schlagen fehl.
- `session`: echte PostgreSQL (D6). Jeder Test laeuft in einer Transaktion, die danach
  zurueckgerollt wird.
"""

import os
import socket
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from loipen.models import Base

ROOT = Path(__file__).resolve().parent.parent
TEST_DATABASE_URL = os.environ.get(
    "LOIPEN_TEST_DATABASE_URL", "postgresql+psycopg://loipen:loipen@localhost:5432/loipen_test"
)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "req(kennung, ak=None): Anforderung (und Akzeptanzkriterium), die der Test prueft"
    )


@pytest.fixture(autouse=True)
def _reqseq_properties(request, record_property):
    for mark in request.node.iter_markers("req"):
        for kennung in mark.args:
            record_property("reqseq:element", kennung)
            ak = mark.kwargs.get("ak")
            for nummer in ak if isinstance(ak, (list, tuple)) else ([ak] if ak else []):
                record_property("reqseq:criterion", f"{kennung}:{nummer}")


_LOKAL = {"localhost", "127.0.0.1", "::1"}
_echtes_connect = socket.socket.connect


def _nur_lokal(self, address):
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, str) and host not in _LOKAL and not host.startswith("/"):
        raise RuntimeError(f"Test wollte ins Netz: {address!r}. Tests laufen nur mit Fixtures.")
    return _echtes_connect(self, address)


@pytest.fixture(autouse=True)
def _kein_netz(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _nur_lokal)


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    # Schutz: die Tests leeren die Datenbank, also nie gegen die echte laufen
    assert engine.url.database.endswith("_test"), "Testdatenbank muss auf _test enden"
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    with engine.connect() as conn:
        trans = conn.begin()
        s = Session(bind=conn, join_transaction_mode="create_savepoint")
        try:
            yield s
        finally:
            s.close()
            trans.rollback()

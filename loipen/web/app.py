"""Web-Container. In Schritt 1 nur Health-Check und eine Platzhalter-Startseite."""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select, text

from loipen.db import session_scope
from loipen.models import Loipe

app = FastAPI(title="Loipen")


@app.get("/health")
def health() -> dict:
    with session_scope() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    with session_scope() as session:
        count = session.scalar(select(func.count()).select_from(Loipe))
    return (
        "<!doctype html><html lang='de'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Loipen</title>"
        f"<p>Loipen in der Datenbank: {count}</p></html>"
    )

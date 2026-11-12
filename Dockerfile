FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# pg_dump fuer den naechtlichen Dump (B14). Gleiche Hauptversion wie der db-Dienst (postgres:16),
# sonst kann pg_restore im db-Container den Dump nicht lesen ("unsupported version in file header").
# Debian liefert nur die neueste Version, daher das Paketarchiv von postgresql.org.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(. /etc/os-release && echo $VERSION_CODENAME)-pgdg main" \
       > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-16 \
    && apt-get purge -y curl && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && pg_dump --version | grep -q " 16\."

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY migrations migrations
COPY loipen loipen
COPY config config

CMD ["python", "-m", "loipen.worker"]

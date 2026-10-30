FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Web und Worker nutzen dasselbe Image, docker-compose.yml waehlt den Befehl
CMD ["uvicorn", "loipen.web.app:app", "--host", "0.0.0.0", "--port", "8000"]

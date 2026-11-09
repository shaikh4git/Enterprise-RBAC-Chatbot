# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HF_HOME=/home/appuser/.cache/huggingface
WORKDIR /app

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY --chown=10001:10001 app/ ./app/
EXPOSE 8505
USER 10001
CMD ["streamlit", "run", "app/app.py", "--server.address=0.0.0.0", "--server.port=8505", "--server.headless=true"]
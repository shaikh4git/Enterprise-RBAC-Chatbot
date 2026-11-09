FROM python:3.11-slim

# Apply current security updates to the Debian packages in the base image.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV HF_HOME=/home/appuser/.cache/huggingface

WORKDIR /app

# Create a non-root application user.
RUN useradd \
    --create-home \
    --uid 10001 \
    --shell /usr/sbin/nologin \
    appuser

# Install Python dependencies.
COPY requirements.txt .

RUN pip install \
    --no-cache-dir \
    -r requirements.txt

# Copy application code.
COPY --chown=10001:10001 app/ ./app/

# Streamlit port.
EXPOSE 8505

USER 10001

CMD ["streamlit", "run", "app/app.py","--server.address=0.0.0.0","--server.port=8505","--server.headless=true"]
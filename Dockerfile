FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt

COPY . /app

RUN chmod +x /app/docker/start-web.sh /app/docker/start-bot.sh /app/docker/start-updater.sh && \
    mkdir -p /data && \
    python /app/web/manage.py collectstatic --noinput

CMD ["/app/docker/start-web.sh"]

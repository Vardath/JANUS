FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python tools/rebuild_server.py
RUN python tools/patch_url_media_ingestion.py
RUN python tools/patch_maintenance_owner_api.py
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
CMD ["sh", "-c", "uvicorn bootstrap:app --host 0.0.0.0 --port ${PORT:-8000}"]

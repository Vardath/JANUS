FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
CMD ["sh", "-c", "uvicorn server_v2.entrypoint:app --host 0.0.0.0 --port ${PORT:-8000}"]

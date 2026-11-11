FROM python:3.12.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/apps/api:/app/apps/worker
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home civis
COPY apps/api apps/api
COPY apps/worker apps/worker
COPY content/dev-fake content/dev-fake
COPY content/owner-supplied content/owner-supplied
COPY scripts scripts
USER 10001
CMD ["uvicorn", "civis.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]

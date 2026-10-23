FROM node:22-alpine AS frontend
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY backend/ ./backend/
COPY data/synthetic.json ./data/synthetic.json
COPY alembic.ini ./
COPY --from=frontend /web/dist ./frontend/dist/
RUN useradd --create-home app && mkdir -p /app/runtime && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["sh","-c","python -m backend.bootstrap && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]

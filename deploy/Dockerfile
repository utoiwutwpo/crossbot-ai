FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 8000
# Railway/Render 等平台注入动态 $PORT；本地构建默认 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import os,httpx; httpx.get(f\"http://localhost:{os.environ.get('PORT','8000')}/health\").raise_for_status()"

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

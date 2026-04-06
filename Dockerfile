# LexGuard MCP — Streamable HTTP (FastAPI + Uvicorn)
FROM python:3.11-slim-bookworm

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=9099

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

EXPOSE 9099

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9099/health', timeout=4)" || exit 1

CMD ["uvicorn", "src.main:api", "--host", "0.0.0.0", "--port", "9099"]

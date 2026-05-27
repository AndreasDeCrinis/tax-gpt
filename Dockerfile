FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/taxgpt.sqlite3 \
    UPLOAD_FOLDER=/data/uploads \
    PORT=8000

WORKDIR /app

RUN addgroup --system taxgpt && adduser --system --ingroup taxgpt taxgpt

COPY pyproject.toml README.md VERSION ./
COPY taxgpt ./taxgpt

RUN pip install --no-cache-dir .

RUN mkdir -p /data/uploads && chown -R taxgpt:taxgpt /data /app
USER taxgpt

EXPOSE 8000

CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT} 'taxgpt:create_app()'"]

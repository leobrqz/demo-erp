# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri

FROM python:3.12-slim AS builder

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini requirements.txt ./

RUN addgroup --system appuser && adduser --system --ingroup appuser appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

RUN groupadd --gid 10001 appgroup \
    && useradd \
        --uid 10001 \
        --gid 10001 \
        --create-home \
        --shell /usr/sbin/nologin \
        appuser

COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data
COPY models ./models
COPY config ./config
COPY scripts ./scripts
COPY reports/observability ./reports/observability
COPY reports/hardening ./reports/hardening
COPY deployment ./deployment

RUN python -m compileall -q src scripts \
    && chown -R 10001:10001 /app

USER 10001:10001

ENTRYPOINT ["python"]
CMD ["scripts/run_agent_orchestrator.py"]

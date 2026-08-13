FROM ghcr.io/astral-sh/uv:0.8.22 AS uv
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
WORKDIR /app
COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY alembic.ini ./
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "answer_controller.boot.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

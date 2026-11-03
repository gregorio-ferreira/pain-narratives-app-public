FROM ghcr.io/astral-sh/uv:0.13.3@sha256:bee0a2a458fd956c5df7b8b4c5fed2257b0af34866e3da7b51db0be3acb375d1 AS uv
FROM python:3.13.16-slim-trixie@sha256:98ce6fb13b3803744fbca11434f00818f1e300e4e48a4f204e07b2c928b6218e AS builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project --python /usr/local/bin/python

FROM python:3.13.16-slim-trixie@sha256:98ce6fb13b3803744fbca11434f00818f1e300e4e48a4f204e07b2c928b6218e AS runtime
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall -y setuptools wheel pip \
    && useradd --uid 1000 --create-home --shell /usr/sbin/nologin appuser
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
COPY scripts/run_app.py ./scripts/run_app.py
RUN python -m compileall -q src scripts
# Runtime code remains owned by root; appuser writes only to explicitly mounted paths/tmp.
ARG APP_REVISION=unknown
ENV OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    PATH="/app/.venv/bin:$PATH" PYTHONPATH=/app/src PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 PAIN_NARRATIVES_REVISION=$APP_REVISION \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false STREAMLIT_CLIENT_SHOW_ERROR_DETAILS=none \
    STREAMLIT_SERVER_ENABLE_CORS=true STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true \
    STREAMLIT_SERVER_MAX_UPLOAD_SIZE=5 STREAMLIT_SERVER_HEADLESS=true
USER 1000:1000
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).close()"]
CMD ["streamlit", "run", "scripts/run_app.py", "--server.port=8501", "--server.address=0.0.0.0"]

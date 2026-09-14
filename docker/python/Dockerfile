FROM python:3.13-slim-trixie@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285

ARG APP_UID=1000
ARG APP_GID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd --gid "${APP_GID}" app \
    && useradd \
        --uid "${APP_UID}" \
        --gid "${APP_GID}" \
        --create-home \
        --shell /usr/sbin/nologin \
        app

WORKDIR /app

COPY requirements.lock ./

RUN python -m pip install \
    --no-cache-dir \
    --requirement requirements.lock

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN python -m pip install \
    --no-cache-dir \
    --no-deps \
    . \
    && python -m pip check

USER app

CMD ["python", "--version"]

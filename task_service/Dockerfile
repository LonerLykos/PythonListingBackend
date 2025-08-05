FROM python:3.12-slim

LABEL maintainer='LonerLykos'
LABEL version="1.0"
LABEL description="Image for Celery tasks"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=2.1.3 \
    POETRY_NO_INTERACTION=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app/task_service:/app

WORKDIR /app

RUN pip install poetry==$POETRY_VERSION

COPY shared /app/shared
COPY task_service /app/task_service
COPY ./auth_service/app/models /app/auth_service/app/models
COPY ./listing_service/app/models/exchange_rate.py /app/listing_service/app/models/
COPY ./listing_service/app/models/base.py /app/listing_service/app/models/
COPY ./listing_service/app/models/__init__.py /app/listing_service/app/models/

WORKDIR /app/task_service

RUN poetry config virtualenvs.create false && \
    poetry install --no-root

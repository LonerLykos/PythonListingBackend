FROM python:3.12-slim

LABEL maintainer='LonerLykos'
LABEL version="1.0"
LABEL description="Backend image for listing microservice"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=2.1.3 \
    POETRY_NO_INTERACTION=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app/listing_service

WORKDIR /app

RUN pip install poetry==$POETRY_VERSION

COPY shared /app/shared
COPY listing_service /app/listing_service

WORKDIR /app/listing_service

RUN poetry config virtualenvs.create false && \
    poetry install --no-root

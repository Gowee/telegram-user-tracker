FROM python:slim

RUN set -eux; \
    apt-get update; \
    apt-get install -y curl; \
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py; \
    pip install poetry
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false; \
    poetry install
COPY . .
ENTRYPOINT ["/usr/bin/env", "python", "-m", "telegram_user_tracker"]
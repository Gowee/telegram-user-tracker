FROM python:slim

RUN set -eux; \
    apt-get update; \
    apt-get install -y curl; \
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py; \
    pip install poetry
WORKDIR /app
VOLUME ["/app/session"]
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false; \
    poetry install
COPY . .
RUN chmod +x entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

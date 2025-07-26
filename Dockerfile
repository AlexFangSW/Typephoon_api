FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app

COPY ./uv.lock \ 
  ./README.md \
  ./pyproject.toml \
  ./alembic.ini \
  /app/

RUN uv sync --no-editable --locked --no-install-project

COPY ./data/ /app/data
COPY ./migration/ /app/migration
COPY ./src/ /app/src

RUN uv sync --no-editable --locked

CMD [ ".venv/bin/typephoon-api", "--init" ]

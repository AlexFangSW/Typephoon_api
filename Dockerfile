FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app

COPY ./uv.lock \ 
  ./README.md \
  ./pyproject.toml \
  ./alembic.ini \
  /app/

RUN uv sync --frozen

COPY ./data/ /app/data
COPY ./migration/ /app/migration
COPY ./src/ /app/src

CMD [ "uv", "run", "typephoon-api", "--init" ]

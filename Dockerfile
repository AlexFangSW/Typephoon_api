FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app

COPY ./uv.lock \ 
  ./README.md \
  ./pyproject.toml \
  ./alembic.ini \
  /app/

COPY ./data/ /app/data
COPY ./migration/ /app/migration
COPY ./src/ /app/src

RUN uv sync --frozen

CMD [ "uv", "run", "typephoon-api", "--init" ]

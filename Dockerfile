FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app

COPY . /app

RUN uv sync --frozen

CMD [ "uv", "run", "typephoon-api", "--init" ]

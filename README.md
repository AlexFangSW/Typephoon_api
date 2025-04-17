# Typephoon Backend
## Development
### Install dependencies 
```bash
uv sync --group dev
```
### Activate virtual enviroment
```bash
source .venv/bin/activate
```
### Start DB, cache...etc
```
docker compose up -d
```
### Run
```
typephoon-api --help
```
### Test
```
pytest
```

# Typephoon Backend
## Development
### Setup
Poetry auto export
- generates `test-requirements.txt` and `requirements.txt` for CI/CD pipelines
```
pipx inject poetry poetry-auto-export
```
Activate environment
```
poetry shell
```
Install dependencies
```
poetry install
```
Start DB, cache...etc
```
docker compose up -d
```
### Run
```
python3 -m typephoon_api --help
```

### Test
```
pytest -v
```

## TODO
Features:
- lobby:
    - [ ] api for frontend to get lobby info

QOL:
- [ ] request id
    - use or generate request id for each request and use it in our logger
    - https://github.com/snok/asgi-correlation-id

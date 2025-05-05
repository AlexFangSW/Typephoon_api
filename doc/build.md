# Build
TODO: provide links
## Technologies Used
- Language: **Python**
- Package Manager: **UV**
- Backend framework: **FastAPI**
- ORM: **SQLAlchemy**
- Database Migration: **Alembic**
- Database: **PostgreSQL**
- Key value store: **Redis**
- Message Queue: **RabbitMQ**
- CI/CD: 
    - **GitHub Actions**: test and build docker image
    - **Drone ci**: helm packaging
- Miscellaneous:
    - **Docker**
    - **Docker compose** (Local development)
    - **Kubernetes**
    - **Helm**

## Code Structure
```

```

## Project Architecture
That pic

## Development
### Install dependencies 
```bash
uv sync --group dev --locked
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
typephoon-api --init
```
Get full information for startup with `--help` 
```
typephoon-api --help
```
### Test
```
pytest
```

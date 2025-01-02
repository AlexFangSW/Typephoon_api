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

## Notes
- Lobby
    - user join
    - user reconnect
    - game start on countdown end
    - game start on game full
    - [TODO] send reconnect msg on server shoutdown
        - lifespan
    - [TODO] api for lobby info
        - player list
    - [TODO] api for coutdown
        - return seconds
    - [TODO] api for user leave
        - remove from cache
        - substract player count
        - remove background task
    - [TODO] FE:
        - get event and do stuff
            - reconnect
            - update
            - game start
        - button to leave
        - button to queue in

## TODO
Features:
- lobby:
    - api for frontend to get lobby info

- RabbitMQ deadletter policy for lobby countdown
    - random 
    - team

QOL:
- request id
    - use or generate request id for each request and use it in our logger
    - https://github.com/snok/asgi-correlation-id

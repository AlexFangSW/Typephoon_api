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
    - [OK] send reconnect msg on server shoutdown
        - lifespan
    - [OK] api for lobby info
        - player list
    - [OK] api for coutdown
        - return seconds
    - [OK] api for user leave
        - remove from cache
        - substract player count
        - remove background task
        - send `USER_LEAVE` notification
    - [TODO] FE:
        - get event and do stuff
            - reconnect
            - update
            - game start
        - button to leave
        - button to queue in

- In game
    - websocket for in game
        - needs access_token (cookie) and game_id (query)
    - no reconnect, unless server says so, same as lobby reconnect.
    - In game countdown api
        - start time + N seconds
        - game type in query
    - In game
        - send each key stoke to server, server than broadcasts it 
            to all users. Frontend renders player location on reciving event.
            ```json
            {
                "game_id": xxxx,
                "user_id": xxxx,
                "word_index": xxx,
                "char_index": xxx
            }
            ```
    - Game end:
        - when players reaches the end of the last word, doesn't need to be correct,
            just needs to be in the same index.
        - server does the checking on each key stroke, and sends end event to user.
            - the ranking is decided here with `finished_players` field in the games table.
            - ranking and finish time is "cached"
        - Api to receive game statistics, saved to cache and creates a "game result" record in the DB,
            ```json
            {
                "game_id": xxx,
                "user_id": xxx,
                "wpm": xxx,
                "wpm_raw": xxx,
                "acc": xxx,
                "acc_raw": xxx
            }
            ```
    - Result page 
        - the game id will be in the url query
        - API to get result page statistics
            - data should exist in cache

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

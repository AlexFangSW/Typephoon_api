# Build
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
    - **WebSockets**
    - **Docker**
    - **Docker compose** (Local development)
    - **Kubernetes**
    - **Helm**

## Project Structure
```
.
└── src
    └── typephoon_api
        ├── api/            # API routes
        ├── consumers/      # RabbitMQ Consumers
        ├── lib/            # Utilities used throughout the codebase
        ├── __main__.py     # The main entrypoint
        ├── orm/            # SQAlchemy classes
        ├── repositories/   # Access to database and cache 
        ├── services/       # API logic
        ├── tests/
        └── types/          # Type definitions (ex: pydantic models, dataclasses)
```

## Architecture
![architecture-diagram](./pics/typing_game_design-Architecture.drawio.svg)

### Frontend And Backend
The frontend and backend share the same domain, requests that have a route prefix of 
`/api/v1` are routed to the backend, while all other requsets are routed to the 
frontend.  
Frontend and backend comminicate through REST API and WebSockets.  
- **REST API**: Typical reqests.  
- **WebSockets**: Event triggers and real-time data transfer.  
    - **Event triggers**
        - User joins / leaves the lobby, frontend is triggered to request lobby info.
        - When Lobby countdown finishes, frontend recives a trigger to redirect users to the 'game' page.
        - On Game start, frontend is triggerd to set event listener for keystrokes.
    - **Real-time data**
        - User in game keystrokes.

### RabbitMQ
The core purpose of RabbitMQ are:
- Communication between servers
- Distributed countdown timer

#### Communication between servers
Users in the same game might have their WebSockets connected to different servers.  
For users in the same game to recive keystrokes from other players, when the server
recives a keystroke from the user, it broadcasts it to other servers through a FANOUT
exchange.
> If we have a large amount of servers, FANOUT exchange
will create a lot of unnecessary messages, improvements can be done here. Mabe include what server 
the users have their WebSockets connected in the cache to remove the use of FANOUT exchange.  

#### Distributed countdown timer
This is used for 'delayed events' that needs to be exacuted after a certain timeout.  
It is achieved through RabbitMQ's 'Deadletter Policies'
- **Lobby Countdown**: Once the contdown ends, all users will be simultaneously redirected to the 'game' page
- **Game Start**: Once the contdown ends, frontend is notified to set event listener for keystoke 
- **Game Cleanup**: Games will be cleaned up after a set period of time (default 15 minutes)

### Redis
Used as a cache for lobby and in-game data.  
- Player info for lobby and in-game
- Timestamp for lobby and in-game countdown, this timestamp is the end time for those countdowns.
    - While the actual trigger for countdown events are sent from the server, the countdown number themselves
      are retrived by 'poolling' the server.

### PostgreSQL
Persists long lasting data.
- User
- Game
- Game result for each user

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

## Start for frontend development
```
docker compose up backend --build
```
Backend is hosted on http://locahost:8080

## Related Projects
- [Typephoon Frontend](https://github.com/AlexFangSW/Typephoon)

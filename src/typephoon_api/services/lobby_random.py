from collections import defaultdict
from datetime import UTC, datetime, timedelta
from logging import getLogger
from fastapi import WebSocket
from jwt import PyJWTError
from pamqp.commands import Basic
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repositories.game_cache import GameCacheRepo

from ..types.errors import PublishNotAcknowledged

from ..repositories.game import GameRepo

from ..repositories.guest_token import GuestTokenRepo

from ..types.common import LobbyUserInfo

from ..lib.util import gen_guest_user_info

from ..types.enums import CookieNames, GameStatus, UserType, WSCloseReason

from ..lib.lobby.lobby_manager import LobbyBackgroundManager

from ..lib.lobby.lobby_random_background import LobbyRandomBackground
from aio_pika.abc import AbstractExchange
from aio_pika import Message

from ..lib.token_generator import TokenGenerator
from ..lib.token_validator import TokenValidator
from ..types.setting import Setting

logger = getLogger(__name__)


class LobbyRandomService:
    """
    Lobby service for 'Ramdom' game mode

    -   Generate temp auth cookies for guests, just for identifiying who they are
        in latter stages. Users will recive an event though this websocket that 
        guides them to request their cookies though an endpoint.

    -   Match making. Tigger update when new team is found.

    -   Trigger update when new user comes in

    -   Trigger game start
        -   When contdown ends 
        -   When all users click 'just start'
    """

    def __init__(
        self,
        setting: Setting,
        token_generator: TokenGenerator,
        token_validator: TokenValidator,
        background_bucket: defaultdict[str, LobbyBackgroundManager],
        guest_token_repo: GuestTokenRepo,
        sessionmaker: async_sessionmaker[AsyncSession],
        amqp_lobby_exchange: AbstractExchange,
        amqp_countdown_exchange: AbstractExchange,
        game_cache_repo: GameCacheRepo,
    ) -> None:
        self._setting = setting
        self._token_generator = token_generator
        self._background_bucket = background_bucket
        self._token_validator = token_validator
        self._guest_token_repo = guest_token_repo
        self._sessionmaker = sessionmaker
        self._amqp_countdown_exchange = amqp_countdown_exchange
        self._amqp_lobby_exchange = amqp_lobby_exchange
        self._game_cache_repo = game_cache_repo
        # match making
        pass

    async def queue_in(self, websocket: WebSocket):
        logger.debug("queue_in")

        access_token = websocket.cookies.get(CookieNames.ACCESS_TOKEN, None)

        guest_token_key: str | None = None

        if access_token is None:
            user_info = gen_guest_user_info()
            token = self._token_generator.gen_access_token(
                user_id=user_info.id,
                username=user_info.name,
                user_type=UserType.GUEST)
            guest_token_key = await self._guest_token_repo.store(token)
        else:
            try:
                assert access_token
                info = self._token_validator.validate(access_token)
                user_info = LobbyUserInfo(id=info.sub, name=info.name)
            except PyJWTError:
                await websocket.close(reason=WSCloseReason.INVALID_TOKEN)
                return

        # match making, find or create game
        async with self._sessionmaker() as session:
            game_repo = GameRepo(session)
            game = await game_repo.get_one(status=GameStatus.LOBBY, lock=True)
            game_id: int | None = None

            if game:
                logger.debug("found game, id: %s", game.id)
                game_id = game.id
                await game_repo.add_player()
                await self._game_cache_repo.add_player(game_id=game.id,
                                                       user_info=user_info)
            else:
                game = await game_repo.create()
                logger.debug("create game, id: %s", game.id)
                game_id = game.id
                await game_repo.add_player()
                await self._game_cache_repo.add_player(game_id=game.id,
                                                       user_info=user_info)

                # send self descruct/game start signal
                msg = Message(b"")
                confirm = await self._amqp_countdown_exchange.publish(
                    msg, routing_key="")
                if not isinstance(confirm, Basic.Ack):
                    raise PublishNotAcknowledged(
                        "publish countdown message failed")

                # set start time in redis for user countdown pooling
                start_time = datetime.now(UTC) + timedelta(seconds=30)
                await self._game_cache_repo.set_start_time(
                    game_id=game.id, start_time=start_time)

            await session.commit()

        # put into background bucket
        bg = LobbyRandomBackground(websocket=websocket, user_info=user_info)
        await bg.prepare()
        await self._background_bucket[str(game_id)].add(bg)
        if guest_token_key:
            # notify user to get their cookie
            await bg.notifiy("")

        # notify users on other servers
        msg = Message(b"")
        confirm = await self._amqp_lobby_exchange.publish(msg, routing_key="")
        if not isinstance(confirm, Basic.Ack):
            raise PublishNotAcknowledged("publish lobby update message failed")

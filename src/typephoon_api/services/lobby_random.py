from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from logging import getLogger
from fastapi import WebSocket
from jwt import PyJWTError
from pamqp.commands import Basic
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..lib.lobby.base import LobbyBGNotifyMsg

from ..types.amqp import LobbyCountdownMsg, LobbyNotifyType, LobbyNotifyMsg

from ..orm.game import Game, GameStatus, GameType

from ..lib.lobby.lobby_background_random import LobbyBackground

from ..repositories.game_cache import GameCacheRepo

from ..types.errors import PublishNotAcknowledged

from ..repositories.game import GameRepo

from ..repositories.guest_token import GuestTokenRepo

from ..types.common import LobbyUserInfo

from ..lib.util import gen_guest_user_info

from ..types.enums import CookieNames, QueueInType, WSCloseReason

from ..lib.lobby.lobby_manager import LobbyBackgroundManager

from aio_pika.abc import AbstractExchange
from aio_pika import Message

from ..lib.token_generator import TokenGenerator, UserType
from ..lib.token_validator import TokenValidator
from ..types.setting import Setting

logger = getLogger(__name__)


@dataclass(slots=True)
class ProcessTokenRet:
    user_info: LobbyUserInfo
    guest_token_key: str | None = None


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
        amqp_notify_exchange: AbstractExchange,
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
        self._amqp_notify_exchange = amqp_notify_exchange
        self._game_cache_repo = game_cache_repo

    async def _process_token(self, access_token: str | None) -> ProcessTokenRet:
        """
        Validate token, create one for guest if needed
        """

        if access_token is None:
            user_info = gen_guest_user_info()
            token = self._token_generator.gen_access_token(
                user_id=user_info.id,
                username=user_info.name,
                user_type=UserType.GUEST)
            guest_token_key = await self._guest_token_repo.store(token)
            return ProcessTokenRet(user_info=user_info,
                                   guest_token_key=guest_token_key)

        else:
            assert access_token
            info = self._token_validator.validate(access_token)
            user_info = LobbyUserInfo(id=info.sub, name=info.name)
            return ProcessTokenRet(user_info=user_info)

    async def _find_game(self, game_repo: GameRepo, queue_in_type: QueueInType,
                         prev_game_id: int | None,
                         user_info: LobbyUserInfo) -> Game | None:

        if queue_in_type == QueueInType.RECONNECT and prev_game_id is not None:
            prev_game_id = int(prev_game_id)
            new_player = await self._game_cache_repo.is_new_player(
                game_id=prev_game_id, user_id=user_info.id)

            game = await game_repo.is_available(id=prev_game_id,
                                                lock=True,
                                                new_player=new_player)
            return game

        else:
            game = await game_repo.get_one_available(lock=True)
            return game

    async def _join_game(self, game_repo: GameRepo, game_id: int,
                         user_info: LobbyUserInfo):
        logger.debug("_join_game, game_id: %s", game_id)
        new_player = await self._game_cache_repo.add_player(game_id=game_id,
                                                            user_info=user_info)
        if new_player:
            await game_repo.add_player(game_id)

    async def _send_countdown_signal(self, game_id: int):
        msg = LobbyCountdownMsg(game_id=game_id).model_dump_json().encode()
        amqp_msg = Message(msg)

        confirm = await self._amqp_countdown_exchange.publish(
            amqp_msg,
            routing_key=self._setting.amqp.lobby_random_countdown_wait_queue)

        if not isinstance(confirm, Basic.Ack):
            raise PublishNotAcknowledged("publish countdown message failed")

    async def _set_start_ts_cache(self, game_id: int):
        start_time = datetime.now(UTC) + timedelta(seconds=30)
        await self._game_cache_repo.set_start_time(game_id=game_id,
                                                   start_time=start_time)

    async def _create_game(self, game_repo: GameRepo) -> int:
        game = await game_repo.create(game_type=GameType.RANDOM,
                                      status=GameStatus.LOBBY)

        logger.debug("_create_game, id: %s", game.id)

        # send countdown signal
        await self._send_countdown_signal(game.id)

        # set start time in redis for user countdown pooling
        await self._set_start_ts_cache(game.id)

        return game.id

    async def _add_bg_event_loop(self,
                                 websocket: WebSocket,
                                 user_info: LobbyUserInfo,
                                 game_id: int,
                                 guest_token_key: str | None = None):

        bg = LobbyBackground(websocket=websocket, user_info=user_info)
        await self._background_bucket[str(game_id)].add(bg)

        # notify guest user to get their token
        if guest_token_key:
            msg = LobbyBGNotifyMsg(notify_type=LobbyNotifyType.GET_TOKEN,
                                   guest_token_key=guest_token_key)
            await bg.notifiy(msg)

    async def _notify_other_servers(self, game_id: int):
        msg = LobbyNotifyMsg(notify_type=LobbyNotifyType.USER_JOINED,
                             game_id=game_id).model_dump_json().encode()
        amqp_msg = Message(msg)
        confirm = await self._amqp_notify_exchange.publish(
            amqp_msg, routing_key=self._setting.amqp.lobby_random_notify_queue)
        if not isinstance(confirm, Basic.Ack):
            raise PublishNotAcknowledged("publish lobby notify message failed")

    async def queue_in(self, websocket: WebSocket, queue_in_type: QueueInType,
                       prev_game_id: int | None):
        logger.debug("queue_in")

        try:
            access_token = websocket.cookies.get(CookieNames.ACCESS_TOKEN, None)
            process_token_ret = await self._process_token(access_token)
        except PyJWTError:
            await websocket.close(reason=WSCloseReason.INVALID_TOKEN)
            return

        # match making, find or create game
        async with self._sessionmaker() as session:
            game_repo = GameRepo(session)
            game_id: int | None = None

            game = await self._find_game(game_repo=game_repo,
                                         queue_in_type=queue_in_type,
                                         prev_game_id=prev_game_id,
                                         user_info=process_token_ret.user_info)

            if game:
                game_id = game.id
                await self._join_game(game_repo=game_repo,
                                      game_id=game_id,
                                      user_info=process_token_ret.user_info)
            else:
                game_id = await self._create_game(game_repo=game_repo)
                await self._join_game(game_repo=game_repo,
                                      game_id=game_id,
                                      user_info=process_token_ret.user_info)

            await session.commit()

        await self._add_bg_event_loop(
            websocket=websocket,
            user_info=process_token_ret.user_info,
            game_id=game_id,
            guest_token_key=process_token_ret.guest_token_key)

        await self._notify_other_servers(game_id)

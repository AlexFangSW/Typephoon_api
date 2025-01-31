from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from logging import getLogger
from fastapi import WebSocket
from jwt import PyJWTError
from pamqp.commands import Basic
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..lib.background_tasks.base import BGManager
from ..lib.background_tasks.lobby import LobbyBG, LobbyBGMsg, LobbyBGMsgEvent

from ..repositories.game_cache import GameCacheRepo

from ..types.amqp import LobbyCountdownMsg, LobbyNotifyMsg

from ..orm.game import Game, GameStatus, GameType

from ..repositories.lobby_cache import LobbyCacheRepo

from ..types.errors import PublishNotAcknowledged

from ..repositories.game import GameRepo

from ..repositories.guest_token import GuestTokenRepo

from ..types.common import LobbyUserInfo

from ..lib.util import gen_guest_user_info

from ..types.enums import CookieNames, QueueInType, WSCloseReason


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


class QueueInService:
    """
    Queue in service for 'Ramdom' game mode
    """

    def __init__(
        self,
        setting: Setting,
        token_generator: TokenGenerator,
        token_validator: TokenValidator,
        bg_manager: BGManager[LobbyBGMsg, LobbyBG],
        guest_token_repo: GuestTokenRepo,
        sessionmaker: async_sessionmaker[AsyncSession],
        amqp_notify_exchange: AbstractExchange,
        amqp_default_exchange: AbstractExchange,
        lobby_cache_repo: LobbyCacheRepo,
        game_cache_repo: GameCacheRepo,
    ) -> None:
        self._setting = setting
        self._token_generator = token_generator
        self._bg_manager = bg_manager
        self._token_validator = token_validator
        self._guest_token_repo = guest_token_repo
        self._sessionmaker = sessionmaker
        self._amqp_default_exchange = amqp_default_exchange
        self._amqp_notify_exchange = amqp_notify_exchange
        self._lobby_cache_repo = lobby_cache_repo
        self._game_cache_repo = game_cache_repo

    async def _process_token(self, access_token: str | None) -> ProcessTokenRet:
        """
        Validate token, create one for guest if needed
        """
        logger.debug("_process_token")

        if access_token is None:
            user_info = gen_guest_user_info()
            token = self._token_generator.gen_access_token(
                user_id=user_info.id, username=user_info.name, user_type=UserType.GUEST
            )
            guest_token_key = await self._guest_token_repo.store(token)
            return ProcessTokenRet(user_info=user_info, guest_token_key=guest_token_key)

        else:
            assert access_token
            info = self._token_validator.validate(access_token)
            user_info = LobbyUserInfo(id=info.sub, name=info.name)
            return ProcessTokenRet(user_info=user_info)

    async def _find_game(
        self,
        game_repo: GameRepo,
        queue_in_type: QueueInType,
        prev_game_id: int | None,
        user_info: LobbyUserInfo,
    ) -> Game | None:
        logger.debug(
            "queue_in_type: %s, prev_game_id: %s, user_info: %s",
            queue_in_type,
            prev_game_id,
            user_info,
        )

        if queue_in_type == QueueInType.RECONNECT and prev_game_id is not None:
            logger.debug("try reconnect, prev_game_id: %s", prev_game_id)
            prev_game_id = int(prev_game_id)
            new_player = await self._lobby_cache_repo.is_new_player(
                game_id=prev_game_id, user_id=user_info.id
            )

            game = await game_repo.is_available(
                id=prev_game_id, lock=True, new_player=new_player
            )
            return game

        else:
            logger.debug("get_one_available")
            game = await game_repo.get_one_available(lock=True)
            return game

    async def _join_game(
        self, game_repo: GameRepo, game_id: int, user_info: LobbyUserInfo
    ) -> bool:
        logger.debug("game_id: %s, user_info: %s", game_id, user_info)

        async with self._lobby_cache_repo.lock(game_id):
            new_player = await self._lobby_cache_repo.add_player(
                game_id=game_id, user_info=user_info
            )

        if new_player:
            logger.debug("new player, game_id: %s, user_info: %s", game_id, user_info)

            game = await game_repo.increase_player_count(game_id)
            assert game

            logger.debug(
                "current player count: %s, game_id: %s", game.player_count, game_id
            )

            if game.player_count >= self._setting.game.player_limit:
                return True

        return False

    async def _send_countdown_signal(self, game_id: int):
        logger.debug("game_id: %s", game_id)

        msg = LobbyCountdownMsg(game_id=game_id).model_dump_json().encode()
        amqp_msg = Message(msg)

        confirm = await self._amqp_default_exchange.publish(
            message=amqp_msg,
            routing_key=self._setting.amqp.lobby_multi_countdown_wait_queue,
        )

        if not isinstance(confirm, Basic.Ack):
            raise PublishNotAcknowledged("publish countdown message failed")

    async def _set_start_ts_cache(self, game_id: int):
        logger.debug("game_id: %s", game_id)

        start_time = datetime.now(UTC) + timedelta(
            seconds=self._setting.game.lobby_countdown
        )
        await self._lobby_cache_repo.set_start_time(
            game_id=game_id, start_time=start_time
        )

    async def _create_game(self, game_repo: GameRepo) -> int:
        game = await game_repo.create(game_type=GameType.MULTI, status=GameStatus.LOBBY)

        logger.debug("id: %s", game.id)

        # send countdown signal
        await self._send_countdown_signal(game.id)

        # set start time in redis for user countdown pooling
        await self._set_start_ts_cache(game.id)

        return game.id

    async def _add_bg_event_loop(
        self,
        websocket: WebSocket,
        user_info: LobbyUserInfo,
        game_id: int,
        guest_token_key: str | None = None,
    ):
        logger.debug(
            "user_info: %s, game_id: %s, guest_token_key: %s",
            user_info,
            game_id,
            guest_token_key,
        )

        # notify user their game id
        bg = LobbyBG(ws=websocket, user_id=user_info.id)
        bg_group = await self._bg_manager.get(game_id)
        assert bg_group
        await bg_group.add(
            bg=bg, init_msg=LobbyBGMsg(event=LobbyBGMsgEvent.INIT, game_id=game_id)
        )

        # notify guest user to get their token
        if guest_token_key:
            logger.debug(
                "notify guest user to get token, user_info: %s, game_id: %s, guest_token_key: %s",
                user_info,
                game_id,
                guest_token_key,
            )
            await bg.put_msg(
                LobbyBGMsg(
                    event=LobbyBGMsgEvent.GET_TOKEN, guest_token_key=guest_token_key
                )
            )

    async def _notify_user_join(self, game_id: int):
        logger.debug("game_id: %s", game_id)

        msg = (
            LobbyNotifyMsg(notify_type=LobbyBGMsgEvent.USER_JOINED, game_id=game_id)
            .slim_dump_json()
            .encode()
        )
        amqp_msg = Message(msg)
        confirm = await self._amqp_notify_exchange.publish(
            message=amqp_msg, routing_key=""
        )
        if not isinstance(confirm, Basic.Ack):
            raise PublishNotAcknowledged("publish user join message failed")

    async def _send_start_msg(self, game_id: int):
        logger.debug("game_id: %s", game_id)

        msg = (
            LobbyNotifyMsg(notify_type=LobbyBGMsgEvent.GAME_START, game_id=game_id)
            .slim_dump_json()
            .encode()
        )
        amqp_msg = Message(msg)
        confirm = await self._amqp_notify_exchange.publish(
            message=amqp_msg, routing_key=self._setting.amqp.lobby_notify_queue
        )
        if not isinstance(confirm, Basic.Ack):
            raise PublishNotAcknowledged("publish start msg failed")

    async def queue_in(
        self,
        websocket: WebSocket,
        queue_in_type: QueueInType,
        prev_game_id: int | None = None,
    ):
        logger.debug("queue_in_type: %s, prev_game_id: %s", queue_in_type, prev_game_id)

        try:
            access_token = websocket.cookies.get(CookieNames.ACCESS_TOKEN, None)
            process_token_ret = await self._process_token(access_token)
            await websocket.accept()
        except PyJWTError as ex:
            logger.warning("invalid token, error: %s", str(ex))
            await websocket.close(reason=WSCloseReason.INVALID_TOKEN)
            return

        # match making, find or create game
        async with self._sessionmaker() as session:
            game_repo = GameRepo(
                session=session, player_limit=self._setting.game.player_limit
            )
            game_id: int | None = None

            game = await self._find_game(
                game_repo=game_repo,
                queue_in_type=queue_in_type,
                prev_game_id=prev_game_id,
                user_info=process_token_ret.user_info,
            )

            if game:
                game_id = game.id
                game_full = await self._join_game(
                    game_repo=game_repo,
                    game_id=game_id,
                    user_info=process_token_ret.user_info,
                )
            else:
                game_id = await self._create_game(game_repo=game_repo)
                game_full = await self._join_game(
                    game_repo=game_repo,
                    game_id=game_id,
                    user_info=process_token_ret.user_info,
                )

            await session.commit()

        await self._add_bg_event_loop(
            websocket=websocket,
            user_info=process_token_ret.user_info,
            game_id=game_id,
            guest_token_key=process_token_ret.guest_token_key,
        )

        await self._notify_user_join(game_id)

        if game_full:
            logger.debug("game full, game_id: %s", game_id)

            # set game status
            async with self._sessionmaker() as session:
                game_repo = GameRepo(
                    session=session, player_limit=self._setting.game.player_limit
                )
                await game_repo.start_game(game_id)
                await session.commit()

            # populate game cache
            await self._game_cache_repo.populate_with_lobby_cache(
                game_id=game_id,
                lobby_cache_repo=self._lobby_cache_repo,
                auto_clean=True,
            )

            await self._send_start_msg(game_id)

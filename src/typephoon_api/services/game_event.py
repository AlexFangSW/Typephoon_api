from logging import getLogger
from aio_pika.abc import AbstractExchange
from fastapi import WebSocket
from jwt.exceptions import PyJWTError

from ..types.setting import Setting

from ..lib.background_tasks.base import BGManager
from ..lib.background_tasks.game import GameBG, GameBGMsg

from ..repositories.game_cache import GameCacheRepo

from ..types.enums import CookieNames, WSCloseReason
from ..lib.token_validator import TokenValidator

logger = getLogger(__name__)


class GameEventService:

    def __init__(
        self,
        token_validator: TokenValidator,
        game_cache_repo: GameCacheRepo,
        bg_manager: BGManager[GameBGMsg, GameBG],
        keystroke_exchange: AbstractExchange,
        setting: Setting,
    ) -> None:
        self._token_validator = token_validator
        self._game_cache_repo = game_cache_repo
        self._bg_manager = bg_manager
        self._keystroke_exchange = keystroke_exchange
        self._setting = setting

    async def process(
        self,
        websocket: WebSocket,
        game_id: int,
    ):
        logger.debug("in game ws connection, game_id: %s", game_id)

        # check token (must have token)
        try:
            access_token = websocket.cookies.get(CookieNames.ACCESS_TOKEN, None)
            if not access_token:
                logger.warning("no access token")
                await websocket.close(reason=WSCloseReason.ACCESS_TOKEN_NOT_FOUND)
                return

            current_user = self._token_validator.validate(access_token)

            await websocket.accept()
        except PyJWTError as ex:
            logger.warning("invalid token, error: %s", str(ex))
            await websocket.close(reason=WSCloseReason.INVALID_TOKEN)
            return

        # check if user is in this game
        players = await self._game_cache_repo.get_players(game_id)
        if players is None:
            logger.warning("game not found, game_id: %s", game_id)
            await websocket.close(reason=WSCloseReason.GAME_NOT_FOUND)
            return

        user_id = current_user.sub
        if user_id not in players:
            logger.warning(
                "user does not participate in this game, game_id: %s, user_id: %s, users in this game: %s",
                game_id,
                user_id,
                players.keys(),
            )
            await websocket.close(reason=WSCloseReason.NOT_A_PARTICIPANT)
            return

        # add to background task
        game_bg_manager = await self._bg_manager.get(game_id)
        bg = GameBG(
            ws=websocket,
            user_id=user_id,
            exchange=self._keystroke_exchange,
            setting=self._setting,
            game_id=game_id,
            server_name=self._setting.server_name,
        )
        await game_bg_manager.add(bg)

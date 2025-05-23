from logging import getLogger

from aio_pika.abc import AbstractExchange
from fastapi import WebSocket
from jwt.exceptions import ExpiredSignatureError, PyJWTError

from ..lib.background_tasks.base import BGManager
from ..lib.background_tasks.game import GameBG, GameBGMsg
from ..lib.token_validator import TokenValidator
from ..repositories.game_cache import GameCacheRepo
from ..types.enums import CookieNames, WSCloseReason
from ..types.setting import Setting

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

    async def subscribe(
        self,
        websocket: WebSocket,
        game_id: int,
    ) -> GameBG | None:
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
        except ExpiredSignatureError as ex:
            logger.warning("expired token: %s", str(ex))
            await websocket.close(reason=WSCloseReason.TOKEN_EXPIRED)
            return
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
                "user does not participant in this game, game_id: %s, user_id: %s, users in this game: %s",
                game_id,
                user_id,
                players.keys(),
            )
            await websocket.close(reason=WSCloseReason.NOT_A_PARTICIPANT)
            return

        # add to background task
        bg = GameBG(
            ws=websocket,
            user_id=user_id,
            exchange=self._keystroke_exchange,
            setting=self._setting,
            game_id=game_id,
            server_name=self._setting.server_name,
        )
        await self._bg_manager.add(game_id=game_id, bg=bg)
        return bg

    async def close_wait(self, bg: GameBG):
        await bg.close_wait()
        await self._bg_manager.remove_user(game_id=bg.game_id, user_id=bg.user_id)

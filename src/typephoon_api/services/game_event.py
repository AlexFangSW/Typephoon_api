from collections import defaultdict
from logging import getLogger
from fastapi import WebSocket, background
from jwt.exceptions import PyJWTError

from ..lib.game.game_background import GameBackground
from ..types.common import GameUserInfo

from ..lib.game.game_manager import GameBackgroundManager

from ..repositories.game_cache import GameCacheRepo

from ..types.enums import CookieNames, WSCloseReason
from ..lib.token_validator import TokenValidator

logger = getLogger(__name__)


class GameEventService:

    def __init__(
            self, token_validator: TokenValidator,
            game_cache_repo: GameCacheRepo,
            background_bucket: defaultdict[int, GameBackgroundManager]) -> None:
        self._token_validator = token_validator
        self._game_cache_repo = game_cache_repo
        self._background_bucket = background_bucket

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
                await websocket.close(
                    reason=WSCloseReason.ACCESS_TOKEN_NOT_FOUND)
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
                game_id, user_id, players.keys())
            await websocket.close(reason=WSCloseReason.NOT_A_PARTICIPANT)
            return

        # add to background task
        bg = GameBackground(websocket=websocket, user_info=players[user_id])
        await bg.start()
        await self._background_bucket[game_id].add(bg)

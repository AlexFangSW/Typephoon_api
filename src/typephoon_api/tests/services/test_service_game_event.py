from asyncio import Future
from ...types.common import LobbyUserInfo
from ...repositories.lobby_cache import LobbyCacheRepo
from ...types.enums import CookieNames, UserType, WSCloseReason
from ...lib.background_tasks.base import BGManager
from ...lib.background_tasks.game import GameBG, GameBGMsg
from ...lib.token_generator import TokenGenerator
from ...lib.token_validator import TokenValidator
from ...repositories.game_cache import GameCacheRepo
from ...services.game_event import GameEventService
from unittest.mock import AsyncMock, MagicMock
from ..helper import *


@pytest.mark.asyncio
async def test_service_game_event_no_access_token(setting: Setting, redis_conn: Redis):
    game_id = 123
    token_validator = TokenValidator(setting)
    game_cache_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)
    bg_manager = BGManager[GameBGMsg, GameBG]()
    keystroke_exchange = AsyncMock()
    websocket = AsyncMock()
    websocket.cookies = {}
    websocket.close = AsyncMock()

    service = GameEventService(
        token_validator=token_validator,
        game_cache_repo=game_cache_repo,
        bg_manager=bg_manager,
        keystroke_exchange=keystroke_exchange,
        setting=setting,
    )

    bg = await service.subscribe(websocket=websocket, game_id=game_id)
    assert bg is None

    assert websocket.close.called
    assert (
        websocket.close.call_args.kwargs["reason"]
        == WSCloseReason.ACCESS_TOKEN_NOT_FOUND
    )


@pytest.mark.asyncio
async def test_service_game_event_invalid_access_token(
    setting: Setting, redis_conn: Redis
):
    game_id = 123
    token_validator = TokenValidator(setting)
    game_cache_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)
    bg_manager = BGManager[GameBGMsg, GameBG]()
    keystroke_exchange = AsyncMock()
    websocket = AsyncMock()
    websocket.cookies = {CookieNames.ACCESS_TOKEN: "www.ccc.aaa"}
    websocket.close = AsyncMock()

    service = GameEventService(
        token_validator=token_validator,
        game_cache_repo=game_cache_repo,
        bg_manager=bg_manager,
        keystroke_exchange=keystroke_exchange,
        setting=setting,
    )

    bg = await service.subscribe(websocket=websocket, game_id=game_id)
    assert bg is None

    assert websocket.close.called
    assert websocket.close.call_args.kwargs["reason"] == WSCloseReason.INVALID_TOKEN


@pytest.mark.asyncio
async def test_service_game_event_game_not_found(setting: Setting, redis_conn: Redis):
    game_id = 123
    user_id = "123"
    username = "123-name"
    token_generator = TokenGenerator(setting)
    token_validator = TokenValidator(setting)
    game_cache_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)
    bg_manager = BGManager[GameBGMsg, GameBG]()
    keystroke_exchange = AsyncMock()

    access_token = token_generator.gen_access_token(
        user_id=user_id, username=username, user_type=UserType.REGISTERED
    )

    websocket = AsyncMock()
    websocket.cookies = {CookieNames.ACCESS_TOKEN: access_token}
    websocket.close = AsyncMock()

    service = GameEventService(
        token_validator=token_validator,
        game_cache_repo=game_cache_repo,
        bg_manager=bg_manager,
        keystroke_exchange=keystroke_exchange,
        setting=setting,
    )

    bg = await service.subscribe(websocket=websocket, game_id=game_id)
    assert bg is None

    assert websocket.close.called
    assert websocket.close.call_args.kwargs["reason"] == WSCloseReason.GAME_NOT_FOUND


@pytest.mark.asyncio
async def test_service_game_event_not_a_participant(
    setting: Setting, redis_conn: Redis
):
    game_id = 123
    user_id = "123"
    username = "123-name"
    token_generator = TokenGenerator(setting)
    token_validator = TokenValidator(setting)
    game_cache_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)
    bg_manager = BGManager[GameBGMsg, GameBG]()
    keystroke_exchange = AsyncMock()

    access_token = token_generator.gen_access_token(
        user_id=user_id, username=username, user_type=UserType.REGISTERED
    )

    websocket = AsyncMock()
    websocket.cookies = {CookieNames.ACCESS_TOKEN: access_token}
    websocket.close = AsyncMock()

    service = GameEventService(
        token_validator=token_validator,
        game_cache_repo=game_cache_repo,
        bg_manager=bg_manager,
        keystroke_exchange=keystroke_exchange,
        setting=setting,
    )

    # prepare cache
    lobby_cache_repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    await lobby_cache_repo.add_player(
        game_id=game_id,
        user_info=LobbyUserInfo(id=f"not-{user_id}", name=f"not-{username}"),
    )
    game_cache_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)
    await game_cache_repo.populate_with_lobby_cache(
        game_id=game_id, lobby_cache_repo=lobby_cache_repo, auto_clean=True
    )

    bg = await service.subscribe(websocket=websocket, game_id=game_id)
    assert bg is None

    assert websocket.close.called
    assert websocket.close.call_args.kwargs["reason"] == WSCloseReason.NOT_A_PARTICIPANT


@pytest.mark.asyncio
async def test_service_game_event_success(setting: Setting, redis_conn: Redis):
    game_id = 123
    user_id = "123"
    username = "123-name"
    token_generator = TokenGenerator(setting)
    token_validator = TokenValidator(setting)
    game_cache_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)
    bg_manager = BGManager[GameBGMsg, GameBG]()
    keystroke_exchange = AsyncMock()

    access_token = token_generator.gen_access_token(
        user_id=user_id, username=username, user_type=UserType.REGISTERED
    )

    websocket = AsyncMock()
    websocket.cookies = {CookieNames.ACCESS_TOKEN: access_token}
    websocket.close = AsyncMock()
    websocket.receive_text = MagicMock(return_value=Future())

    service = GameEventService(
        token_validator=token_validator,
        game_cache_repo=game_cache_repo,
        bg_manager=bg_manager,
        keystroke_exchange=keystroke_exchange,
        setting=setting,
    )

    # prepare cache
    lobby_cache_repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    await lobby_cache_repo.add_player(
        game_id=game_id,
        user_info=LobbyUserInfo(id=user_id, name=username),
    )
    game_cache_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)
    await game_cache_repo.populate_with_lobby_cache(
        game_id=game_id, lobby_cache_repo=lobby_cache_repo, auto_clean=True
    )

    bg = await service.subscribe(websocket=websocket, game_id=game_id)
    assert bg is not None

    assert websocket.accept.called
    assert websocket.close.called is False
    game_connections = bg_manager._pool.get(game_id, None)
    assert game_connections
    assert game_connections.get(user_id, None)

    await bg.stop()

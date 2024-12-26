from collections import defaultdict
from fastapi import WebSocket

from ..lib.lobby.lobby_manager import LobbyBackgroundManager

from ..lib.lobby.lobby_random_background import LobbyRandomBackground

from ..lib.token_generator import TokenGenerator
from ..types.setting import Setting


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
        background_bucket: defaultdict[str, LobbyBackgroundManager],
    ) -> None:
        self._setting = setting
        self._token_generator = token_generator
        self._background_bucket = background_bucket
        # match making
        pass

    async def queue_in(self, websocket: WebSocket):
        # hmm... proberbaly done in background.prepare()
        # get and validate cookies
        # gen token if needed
        # match making

        # put into background bucket

        # notify users on other servers
        ...

    ...

from logging import getLogger
from random import shuffle

from ..types.setting import Setting

logger = getLogger(__name__)


class WordGenerator:
    """
    Generates words for game
    """

    def __init__(self, setting: Setting) -> None:
        self._setting = setting
        pass

    def load_words(self):
        with open(self._setting.game.word_file, "r") as f:
            self._words: list[str] = f.read().split("\n")

        logger.info(
            "load words from: %s, word count: %s",
            self._setting.game.word_file,
            len(self._words),
        )

    def generate(self, word_count: int = 25) -> str:
        shuffle(self._words)
        return " ".join(self._words[:word_count])

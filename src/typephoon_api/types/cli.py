from dataclasses import dataclass
from typing import Literal


@dataclass
class CLIArgs:
    """
    Properties:
    - setting: Path to setting.json file.
    - init: Run init actions such as db migrations.
    """
    setting: str
    init: bool
    log_level: Literal["DEBUG", "INFO", "TRACE"]

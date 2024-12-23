from dataclasses import dataclass


@dataclass
class CLIArgs:
    """
    Properties:
    - setting: Path to setting.yaml file.
    - secret_setting: Path to setting.secret.yaml file
    - init: Run init actions such as db migrations.
    """
    setting: str
    secret_setting: str
    init: bool

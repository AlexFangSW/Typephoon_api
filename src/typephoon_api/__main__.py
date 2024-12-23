from argparse import ArgumentParser

import uvicorn

from .types.cli import CLIArgs

from .lib.server_setup import create_server

from .lib.util import db_migration, init_logger, load_setting


def main():
    parser = ArgumentParser("Typephoon API",
                            usage="Starts the backend server",
                            description="The backend for Typephoon project")
    parser.add_argument("-c",
                        "--setting",
                        help="Path to setting.yaml file",
                        dest="setting",
                        default="setting.yaml")
    parser.add_argument("-sc",
                        "--secret-setting",
                        help="Path to setting.secret.yaml file",
                        dest="secret_setting",
                        default="setting.secret.yaml")
    parser.add_argument("--init",
                        help="Run init actions such as db migrations",
                        dest="init",
                        action="store_true")
    args = parser.parse_args(namespace=CLIArgs)

    setting = load_setting(args.setting, args.secret_setting)
    init_logger(setting)

    if args.init:
        db_migration(setting)

    # start the server
    app = create_server(setting)
    uvicorn.run(app,
                host="0.0.0.0",
                port=setting.server.port,
                log_config=setting.logger)


if __name__ == "__main__":
    main()

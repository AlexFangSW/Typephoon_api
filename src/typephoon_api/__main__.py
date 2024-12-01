from argparse import ArgumentParser

from .lib.util import db_migration, init_logger, load_setting

from .types.cli import CLIArgs


def main():
    parser = ArgumentParser("Typephoon API",
                            usage="Starts the backend server",
                            description="The backend for Typephoon project")
    parser.add_argument("-c",
                        "--setting",
                        help="Path to setting.json file",
                        dest="setting",
                        required=True)
    parser.add_argument("--init",
                        help="Run init actions such as db migrations",
                        dest="init",
                        action="store_true")
    args = parser.parse_args(namespace=CLIArgs)

    setting = load_setting(args.setting)
    init_logger(setting)

    if args.init:
        db_migration(setting)


if __name__ == "__main__":
    main()

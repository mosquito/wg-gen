import configparser
import logging
from pathlib import Path

import rich.logging

from .db import init_db, db_connection
from .cli import Parser


def main():
    xdg_path = Path("~/.local/share/wg-gen").expanduser()
    config_path = xdg_path / "config.ini"
    parser = Parser(
        config_files=[config_path],
        auto_env_var_prefix="WG_GEN_"
    )
    parser.parse_args()

    logging.basicConfig(
        level=parser.log_level,
        handlers=[rich.logging.RichHandler(rich_tracebacks=True, show_time=False)],
        format="%(message)s",
    )

    if parser.db_path is None:
        db_path = xdg_path / "database.sqlite3"
        config = configparser.ConfigParser()

        config.set("DEFAULT", "db_path", str(db_path))
        xdg_path.mkdir(parents=True, exist_ok=True)
        with config_path.open("w") as config_file:
            config.write(config_file)
        parser.db_path = db_path

    with db_connection(parser.db_path) as conn:
        init_db(conn)
        retcode = parser(conn)
    exit(retcode)


if __name__ == "__main__":
    main()
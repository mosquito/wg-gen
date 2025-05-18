from pathlib import Path

import argclass
from argclass import Argument

from .base import BaseParser
from .client import ClientCommands
from .interface import InterfaceCommands
from .render import RenderParser


class Parser(BaseParser):
    log_level = argclass.LogLevel
    db_path: Path = Argument(default=None, help="Path to the database file")
    output_format: str = Argument(
        "--output-format", "-f",
        default="table",
        choices=["table", "json", "csv", "tsv"],
        help="Output format",
    )

    interface: InterfaceCommands = InterfaceCommands()
    client: ClientCommands = ClientCommands()
    render: RenderParser = RenderParser(description="Render server config files")

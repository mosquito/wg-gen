from pathlib import Path

import argclass
from argclass import Argument

from .base import BaseParser
from .interface import InterfaceCommands
from .client import ClientCommands
from .render import RenderParser


class Parser(BaseParser):
    log_level = argclass.LogLevel
    db_path: Path = Argument(default=None, help="Path to the database file")

    interface: InterfaceCommands = InterfaceCommands()
    client: ClientCommands = ClientCommands()
    render: RenderParser = RenderParser(description="Render server config files")

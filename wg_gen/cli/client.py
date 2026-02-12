import configparser
import errno
import io
import logging
import sqlite3

import argclass

from argclass import Argument
from qrcode.main import QRCode
from rich import get_console
from rich.panel import Panel

from .base import BaseParser
from wg_gen.db import Client, Interface
from wg_gen.table import SimpleTable


class ClientBaseParser(BaseParser):
    """Base class for interface-related commands"""

    interface: str = Argument("interface", help="WireGuard interface name")


class ClientAddParser(ClientBaseParser):
    """Add a new client to an interface"""

    alias: str = Argument("alias", help="Client alias (unique per interface)")
    preshared_key: bool = False
    force: bool = False
    qr: bool = False

    def __call__(self, conn: sqlite3.Connection) -> int:
        try:
            interface = Interface.load(conn, self.interface)
        except LookupError:
            print(f"Error: Interface '{self.interface}' not found")
            return 1

        try:
            Client.load(conn, self.alias, self.interface)
        except LookupError:
            pass
        else:
            if not self.force:
                logging.error(
                    "Error: Client '%s' already exists for interface '%s', use --force to overwrite",
                    self.alias,
                    self.interface,
                )
                return 1

        try:
            client, private_key = interface.create_client(
                conn,
                alias=self.alias,
                preshared_key=self.preshared_key,
            )
        except ValueError as e:
            logging.error("%s", e)
            return 1

        config = configparser.RawConfigParser()
        config.optionxform = str

        config.add_section("Interface")
        config.add_section("Peer")

        addresses = []
        if client.ipv4:
            addresses.append(str(client.ipv4))
        if client.ipv6:
            addresses.append(str(client.ipv6))

        config.set("Interface", "Address", ", ".join(addresses))
        config.set("Interface", "PrivateKey", private_key)
        config.set("Interface", "DNS", ",".join(map(str, interface.dns)))
        config.set("Interface", "MTU", str(interface.mtu))
        if client.preshared_key:
            config.set("Peer", "PresharedKey", client.preshared_key)

        config.set("Peer", "PublicKey", interface.public_key)
        config.set("Peer", "AllowedIPs", ", ".join(map(str, interface.allowed_ips)))
        config.set("Peer", "Endpoint", interface.endpoint)
        config.set("Peer", "PersistentKeepalive", str(interface.persistent_keepalive))

        with io.StringIO() as fp:
            config.write(fp)
            client_conf = fp.getvalue()

        console = get_console()
        if self.qr:
            qr = QRCode()
            qr.add_data(client_conf)
            with io.StringIO() as fp:
                qr.print_ascii(out=fp)
                qr_code = fp.getvalue()
            console.print(Panel(qr_code, title="Client QR", style="black on white"))
        else:
            console.print(client_conf)

        return 0


class ClientRemoveParser(ClientBaseParser):
    aliases: str = Argument(
        "aliases",
        default=[],
        nargs=argclass.Nargs.ONE_OR_MORE,
        help="Clients alias to remove",
    )

    def __call__(self, conn: sqlite3.Connection) -> int:
        for alias in self.aliases:
            try:
                client = Client.load(conn, alias, self.interface)
            except LookupError:
                logging.error(
                    "Error: Client '%s' not found in interface '%s'",
                    alias,
                    self.interface,
                )
                continue
            logging.info("Removing client '%s'", alias)
            client.remove(conn)
        return 0


class ClientListParser(BaseParser):
    """List all clients for an interface"""

    def __call__(self, conn: sqlite3.Connection) -> int:
        table = SimpleTable(
            "Interface",
            "Client",
            "IPv4",
            "IPv6",
            "Public Key",
            title="WireGuard Clients",
        )

        for interface in Interface.list(conn):
            for client in interface.clients(conn):
                table.add_row(
                    interface.name,
                    client.alias,
                    str(client.ipv4) if client.ipv4 else "",
                    str(client.ipv6) if client.ipv6 else "",
                    client.public_key,
                )

        table.print(self.__parent__.__parent__.output_format)
        return 0


class ClientCommands(BaseParser):
    """Manage clients for WireGuard interfaces"""

    add: ClientAddParser = ClientAddParser()
    remove: ClientRemoveParser = ClientRemoveParser()
    list: ClientListParser = ClientListParser()

    def __call__(self, *args, **kwargs):
        self.print_help()
        exit(errno.EINVAL)

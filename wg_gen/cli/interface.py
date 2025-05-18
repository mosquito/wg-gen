import errno
import ipaddress
import logging
import sqlite3

import rich
from argclass import Argument, Nargs

from wg_gen.cli import BaseParser
from wg_gen.cli.client import ClientBaseParser
from wg_gen.db import Interface
from wg_gen.keygen import keygen
from wg_gen.table import SimpleTable


class InterfaceAddParser(BaseParser):
    """Add a new WireGuard interface"""
    name: str = Argument(help="Interface name (e.g. wg0)")
    ipv4: ipaddress.IPv4Interface | None = Argument(
        default=None,
        help="IPv4 interface for server, all subnet addresses wil be used for clients (e.g. 10.0.0.1/24)",
        type=ipaddress.IPv4Interface,
    )
    ipv6: ipaddress.IPv6Interface | None = Argument(
        default=None,
        help="IPv6 interface for server, all subnet addresses wil be used for clients (e.g. fd00::1/64)",
        type=ipaddress.IPv6Interface,
    )
    mtu: int = Argument(default=1420, help="MTU to use for the interface")
    listen_port: int = Argument(default=51820, help="Server listen port")
    endpoint: str = Argument(required=True, help="Server endpoint host:port for clients")
    dns: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = Argument(
        nargs=Nargs.ONE_OR_MORE,
        default=["1.1.1.1", "8.8.8.8"],
        help="DNS servers for clients",
        type=ipaddress.ip_address,
    )
    allowed_ips: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = Argument(
        nargs=Nargs.ONE_OR_MORE,
        default=["0.0.0.0/0", "2000::/3", "64:ff9b::/96"],
        help="Allowed IPs for peers",
    )
    persistent_keepalive: int = Argument(default=15, help="Persistent keepalive seconds")

    def __call__(self, conn: sqlite3.Connection) -> int:
        private_key, public_key = keygen()
        interface = Interface(
            name=self.name,
            ipv4=self.ipv4,
            ipv6=self.ipv6,
            mtu=self.mtu,
            listen_port=self.listen_port,
            endpoint=self.endpoint,
            dns=self.dns,
            allowed_ips=self.allowed_ips,
            persistent_keepalive=self.persistent_keepalive,
            public_key=public_key,
            private_key=private_key,
        )
        interface.save(conn)


class InterfaceListParser(BaseParser):
    """List all interfaces"""

    def __call__(self, conn: sqlite3.Connection) -> int:
        table = SimpleTable(
            "Interface",
            "Endpoint",
            "Public Key",
            "IPv4",
            "IPv6",
            "MTU",
            "Listen Port",
            "DNS",
            "Allowed IPs",
            "Address Shift",
            title="WireGuard Interfaces",
        )
        interfaces = Interface.list(conn)
        for interface in interfaces:
            table.add_row(
                interface.name,
                interface.endpoint,
                interface.public_key,
                str(interface.ipv4),
                str(interface.ipv6),
                str(interface.mtu),
                str(interface.listen_port),
                "\n".join(str(dns) for dns in interface.dns),
                "\n".join(str(allowed_ip) for allowed_ip in interface.allowed_ips),
                str(interface.address_shift),
            )

        table.print(self.__parent__.__parent__.output_format)
        return 0


class InterfaceRemoveParser(ClientBaseParser):
    def __call__(self, conn: sqlite3.Connection) -> int:
        try:
            interface = Interface.load(conn, self.interface)
        except LookupError:
            logging.error("Interface %s was not found", self.interface)
            return 1

        logging.info("Removing interface %s", self.interface)
        interface.remove(conn)
        return 0


class InterfaceCommands(BaseParser):
    """Manage WireGuard interfaces"""
    add: InterfaceAddParser = InterfaceAddParser()
    remove: InterfaceRemoveParser = InterfaceRemoveParser()
    list: InterfaceListParser = InterfaceListParser()

    def __call__(self, *args, **kwargs):
        self.print_help()
        exit(errno.EINVAL)
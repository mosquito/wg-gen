import errno
import ipaddress
import logging
import sqlite3
from random import randint

from argclass import Argument, Nargs

from wg_gen.cli import BaseParser
from wg_gen.cli.client import ClientBaseParser
from wg_gen.db import Interface
from wg_gen.keygen import keygen
from wg_gen.table import SimpleTable


NON_LOCAL_NETS = frozenset(
    map(
        ipaddress.ip_network,
        [
            "1.0.0.0/8",
            "2.0.0.0/8",
            "3.0.0.0/8",
            "4.0.0.0/6",
            "8.0.0.0/7",
            "11.0.0.0/8",
            "12.0.0.0/6",
            "16.0.0.0/4",
            "32.0.0.0/3",
            "64.0.0.0/2",
            "128.0.0.0/3",
            "160.0.0.0/5",
            "168.0.0.0/6",
            "172.0.0.0/12",
            "172.32.0.0/11",
            "172.64.0.0/10",
            "172.128.0.0/9",
            "173.0.0.0/8",
            "174.0.0.0/7",
            "176.0.0.0/4",
            "192.0.0.0/9",
            "192.128.0.0/11",
            "192.160.0.0/13",
            "192.169.0.0/16",
            "192.170.0.0/15",
            "192.172.0.0/14",
            "192.176.0.0/12",
            "192.192.0.0/10",
            "193.0.0.0/8",
            "194.0.0.0/7",
            "196.0.0.0/6",
            "200.0.0.0/5",
            "208.0.0.0/4",
            "2000::/3",
        ],
    )
)


class InterfaceAddParser(BaseParser):
    """Add a new WireGuard interface"""

    name: str = Argument("name", help="Interface name (e.g. wg0)")
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
    listen_port: int = Argument(
        default=0,
        help="Server listen port, if not specified a random port between 1024 and 65000 will be used",
    )
    endpoint: str = Argument(
        required=True, help="Server endpoint host:port for clients"
    )
    dns: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = Argument(
        nargs=Nargs.ONE_OR_MORE,
        default=["1.1.1.1", "8.8.8.8"],
        help="DNS servers for clients",
        type=ipaddress.ip_address,
    )
    allowed_ips: list[str] = Argument(
        nargs=Nargs.ONE_OR_MORE,
        default=["0.0.0.0/0", "2000::/3"],
        help="Allowed IPs for peers. Special value 'non-local' can be used to set all non-local networks",
        type=str,
    )
    persistent_keepalive: int = Argument(
        default=15, help="Persistent keepalive seconds"
    )

    def __call__(self, conn: sqlite3.Connection) -> int:  # type: ignore[override]
        private_key, public_key = keygen()
        allowed_ips: set[ipaddress.IPv4Network | ipaddress.IPv6Network] = set()

        for allowed_ip in self.allowed_ips:
            if allowed_ip == "non-local":
                allowed_ips.update(NON_LOCAL_NETS)
            else:
                allowed_ips.add(ipaddress.ip_network(allowed_ip))

        listen_port = self.listen_port if self.listen_port else randint(1024, 65000)

        interface = Interface(
            name=self.name,
            ipv4=self.ipv4,
            ipv6=self.ipv6,
            mtu=self.mtu,
            listen_port=listen_port,
            endpoint=self.endpoint,
            dns=self.dns,
            allowed_ips=sorted(allowed_ips, key=str),
            persistent_keepalive=self.persistent_keepalive,
            public_key=public_key,
            private_key=private_key,
        )
        try:
            interface.save(conn)
        except ValueError as e:
            logging.error("%s", e)
            return 1
        return 0


class InterfaceListParser(BaseParser):
    """List all interfaces"""

    def __call__(self, conn: sqlite3.Connection) -> int:  # type: ignore[override]
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

        table.print(self.__parent__.__parent__.output_format)  # type: ignore[union-attr]
        return 0


class InterfaceRemoveParser(ClientBaseParser):
    def __call__(self, conn: sqlite3.Connection) -> int:  # type: ignore[override]
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

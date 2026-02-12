import contextlib
import ipaddress
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .keygen import keygen, preshared_keygen


def init_db(conn: sqlite3.Connection):
    cur = conn.cursor()
    # interfaces table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS interfaces (
            name TEXT PRIMARY KEY UNIQUE NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ipv4 TEXT DEFAULT NULL,
            ipv6 TEXT DEFAULT NULL,
            address_shift INTEGER NOT NULL DEFAULT 1,
            private_key TEXT NOT NULL,
            public_key TEXT NOT NULL,
            mtu INTEGER NOT NULL,
            listen_port INTEGER,
            endpoint TEXT NOT NULL,
            dns TEXT NOT NULL,
            allowed_ips TEXT NOT NULL,
            persistent_keepalive INTEGER NOT NULL
        )
        """,
    )

    # clients table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interface TEXT NOT NULL,
            alias TEXT NOT NULL,
            public_key TEXT NOT NULL,
            preshared_key TEXT DEFAULT NULL,
            ipv4 TEXT DEFAULT NULL,
            ipv6 TEXT DEFAULT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (interface) REFERENCES interfaces(name),
            UNIQUE (interface, alias)
        )""",
    )

    conn.commit()


@contextlib.contextmanager
def db_connection(db_path: Path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("BEGIN IMMEDIATE TRANSACTION")
    try:
        yield conn
    except:
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        conn.close()


@dataclass(frozen=False)
class Interface:
    name: str
    ipv4: ipaddress.IPv4Interface
    ipv6: ipaddress.IPv6Interface
    private_key: str
    public_key: str
    mtu: int
    listen_port: int
    endpoint: str
    dns: list[ipaddress.IPv4Address | ipaddress.IPv6Address]
    allowed_ips: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = field(
        default_factory=list
    )
    address_shift: int = 1
    persistent_keepalive: int = 15
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def load(cls, conn: sqlite3.Connection, interface_name: str) -> "Interface":
        """Load an interface from the database"""
        cur = conn.cursor()
        cur.execute("SELECT * FROM interfaces WHERE name = ?", (interface_name,))
        result = cur.fetchone()
        if not result:
            raise LookupError("Interface not found")

        return cls(
            name=result["name"],
            created_at=datetime.strptime(result["created_at"], "%Y-%m-%d %H:%M:%S"),
            ipv4=ipaddress.IPv4Interface(result["ipv4"]) if result["ipv4"] else None,
            ipv6=ipaddress.IPv6Interface(result["ipv6"]) if result["ipv6"] else None,
            address_shift=result["address_shift"],
            private_key=result["private_key"],
            public_key=result["public_key"],
            mtu=result["mtu"],
            listen_port=result["listen_port"],
            endpoint=result["endpoint"],
            dns=list(map(ipaddress.ip_address, result["dns"].split(","))),
            allowed_ips=list(
                map(ipaddress.ip_network, result["allowed_ips"].split(","))
            ),
            persistent_keepalive=result["persistent_keepalive"],
        )

    def check_address_space(self) -> None:
        """Check that server address is in the network and there is room
        for at least one client address (server + shift=1)."""
        if self.ipv4:
            first_client = self.ipv4 + 1
            if first_client.ip not in self.ipv4.network:
                raise ValueError(
                    f"IPv4 network {self.ipv4.network} has no room "
                    f"for client addresses (server address {self.ipv4.ip})",
                )
        if self.ipv6:
            first_client = self.ipv6 + 1
            if first_client.ip not in self.ipv6.network:
                raise ValueError(
                    f"IPv6 network {self.ipv6.network} has no room "
                    f"for client addresses (server address {self.ipv6.ip})",
                )

    def check_ip_conflicts(self, conn: sqlite3.Connection) -> None:
        """Check that IPv4/IPv6 subnets don't overlap with other interfaces"""
        cur = conn.cursor()
        cur.execute(
            "SELECT name, ipv4, ipv6 FROM interfaces WHERE name != ?",
            (self.name,),
        )
        for row in cur.fetchall():
            if self.ipv4 and row["ipv4"]:
                existing = ipaddress.IPv4Interface(row["ipv4"])
                if self.ipv4.network.overlaps(existing.network):
                    raise ValueError(
                        f"IPv4 subnet {self.ipv4.network} overlaps with "
                        f"interface '{row['name']}' ({existing.network})",
                    )
            if self.ipv6 and row["ipv6"]:
                existing = ipaddress.IPv6Interface(row["ipv6"])
                if self.ipv6.network.overlaps(existing.network):
                    raise ValueError(
                        f"IPv6 subnet {self.ipv6.network} overlaps with "
                        f"interface '{row['name']}' ({existing.network})",
                    )

    def save(self, conn: sqlite3.Connection) -> None:
        """Save the interface to the database"""
        self.check_address_space()
        self.check_ip_conflicts(conn)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO interfaces(
                name,
                created_at,
                ipv4,
                ipv6,
                address_shift,
                private_key,
                public_key,
                mtu,
                listen_port,
                endpoint,
                dns,
                allowed_ips,
                persistent_keepalive
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO UPDATE
            SET created_at = excluded.created_at,
                ipv4 = excluded.ipv4,
                ipv6 = excluded.ipv6,
                address_shift = excluded.address_shift,
                private_key = excluded.private_key,
                public_key = excluded.public_key,
                mtu = excluded.mtu,
                listen_port = excluded.listen_port,
                endpoint = excluded.endpoint,
                dns = excluded.dns,
                allowed_ips = excluded.allowed_ips,
                persistent_keepalive = excluded.persistent_keepalive
            """,
            (
                self.name,
                self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                str(self.ipv4) if self.ipv4 else None,
                str(self.ipv6) if self.ipv6 else None,
                self.address_shift,
                self.private_key,
                self.public_key,
                self.mtu,
                self.listen_port,
                self.endpoint,
                ",".join(map(str, self.dns)),
                ",".join(map(str, self.allowed_ips)),
                self.persistent_keepalive,
            ),
        )

    def generate_client_ipv4(self) -> ipaddress.IPv4Interface | None:
        if not self.ipv4:
            return None
        result = self.ipv4 + self.address_shift
        if result.ip not in self.ipv4.network:
            raise ValueError(
                f"IPv4 address pool exhausted for {self.ipv4.network}",
            )
        return result

    def generate_client_ipv6(self) -> ipaddress.IPv6Interface | None:
        if not self.ipv6:
            return None
        result = self.ipv6 + self.address_shift
        if result.ip not in self.ipv6.network:
            raise ValueError(
                f"IPv6 address pool exhausted for {self.ipv6.network}",
            )
        return result

    def create_client(
        self,
        conn: sqlite3.Connection,
        alias: str,
        preshared_key: bool = False,
    ) -> tuple["Client", str]:
        preshared_key = preshared_keygen() if preshared_key else None

        ipv4_iface = self.generate_client_ipv4()
        ipv6_iface = self.generate_client_ipv6()
        ipv4 = ipv4_iface.ip if ipv4_iface else None
        ipv6 = ipv6_iface.ip if ipv6_iface else None

        self.address_shift += 1
        self.save(conn)

        private, public = keygen()

        client = Client(
            interface=self.name,
            alias=alias,
            public_key=public,
            preshared_key=preshared_key,
            ipv4=ipv4,
            ipv6=ipv6,
        )
        client.save(conn)
        return client, private

    def clients(self, conn: sqlite3.Connection) -> Iterator["Client"]:
        cur = conn.cursor()
        cur.execute(
            "SELECT alias FROM clients WHERE interface = ? ORDER BY id", (self.name,)
        )
        for row in cur.fetchall():
            yield Client.load(conn, row["alias"], self.name)

    @classmethod
    def list(cls, conn: sqlite3.Connection) -> Iterator["Interface"]:
        cur = conn.cursor()
        cur.execute("SELECT name FROM interfaces ORDER BY name")
        for row in cur.fetchall():
            yield cls.load(conn, row["name"])

    def remove(self, conn: sqlite3.Connection) -> None:
        """Remove the interface from the database"""
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM clients WHERE interface = ?",
            (self.name,),
        )
        cur.execute(
            "DELETE FROM interfaces WHERE name = ?",
            (self.name,),
        )


@dataclass(frozen=False)
class Client:
    interface: str
    alias: str
    public_key: str
    preshared_key: str | None
    ipv4: ipaddress.IPv4Address
    ipv6: ipaddress.IPv6Address
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def load(cls, conn: sqlite3.Connection, alias: str, interface: str) -> "Client":
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM clients WHERE alias = ? AND interface = ?",
            (alias, interface),
        )
        result = cur.fetchone()
        if not result:
            raise LookupError("Client not found")

        return cls(
            interface=result["interface"],
            alias=result["alias"],
            public_key=result["public_key"],
            preshared_key=result["preshared_key"],
            created_at=datetime.strptime(result["created_at"], "%Y-%m-%d %H:%M:%S"),
            ipv4=ipaddress.IPv4Address(result["ipv4"]) if result["ipv4"] else None,
            ipv6=ipaddress.IPv6Address(result["ipv6"]) if result["ipv6"] else None,
        )

    def save(self, conn: sqlite3.Connection) -> None:
        """Save the client to the database"""
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO clients(
                interface,
                alias,
                public_key,
                preshared_key,
                ipv4,
                ipv6,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO UPDATE
            SET created_at = excluded.created_at,
                public_key = excluded.public_key,
                preshared_key = excluded.preshared_key,
                ipv4 = excluded.ipv4,
                ipv6 = excluded.ipv6
            """,
            (
                self.interface,
                self.alias,
                self.public_key,
                self.preshared_key,
                str(self.ipv4) if self.ipv4 else None,
                str(self.ipv6) if self.ipv6 else None,
                self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

    def remove(self, conn: sqlite3.Connection) -> None:
        """Remove the client from the database"""
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM clients WHERE interface = ? AND alias = ?",
            (self.interface, self.alias),
        )

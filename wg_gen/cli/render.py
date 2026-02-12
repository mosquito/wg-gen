import errno
import logging
import sqlite3
from io import StringIO
from pathlib import Path

from argclass import Argument

from ..db import Interface
from .base import BaseParser


class SystemdNetworkdParser(BaseParser):
    output: Path = Argument(
        "--output", "-o", default=Path("/etc/systemd/network"), help="Output directory"
    )

    def __call__(self, conn: sqlite3.Connection) -> int:
        output_path = self.output.resolve()
        logging.info("Generating systemd-networkd configuration to %s", output_path)

        for interface in Interface.list(conn):
            with StringIO() as f:
                f.write("[Match]\n")
                f.write(f"Name={interface.name}\n")
                f.write("\n")

                f.write("[Link]\n")
                f.write("ActivationPolicy=always-up\n")
                f.write("RequiredForOnline=no\n")
                f.write("\n")

                f.write("[Network]\n")
                for address in filter(None, [interface.ipv4, interface.ipv6]):
                    f.write(f"Address={address}\n")
                f.write("\n")
                network_content = f.getvalue()

            with StringIO() as f:
                f.write("[NetDev]\n")
                f.write("Kind=wireguard\n")
                f.write(f"Name={interface.name}\n")
                f.write(f"MTUBytes={interface.mtu}\n")
                f.write("\n")

                f.write("[WireGuard]\n")
                f.write(f"ListenPort={interface.listen_port}\n")
                f.write(f"PrivateKey={interface.private_key}\n")
                f.write("\n")

                for client in interface.clients(conn):
                    f.write(f"# Client: {client.alias}\n")
                    f.write("[WireGuardPeer]\n")
                    f.write(
                        "AllowedIPs={}\n".format(
                            ",".join(
                                map(str, filter(None, [client.ipv4, client.ipv6]))
                            ),
                        ),
                    )
                    f.write(f"PublicKey={client.public_key}\n")
                    if client.preshared_key:
                        f.write(f"PresharedKey={client.preshared_key}\n")
                    f.write(f"PersistentKeepalive={interface.persistent_keepalive}\n")
                    f.write("\n")

                netdev_content = f.getvalue()

            netdev_path = output_path / f"{interface.name}.netdev"
            network_path = output_path / f"{interface.name}.network"

            for path, content in [
                (netdev_path, netdev_content),
                (network_path, network_content),
            ]:
                path.parent.mkdir(parents=True, exist_ok=True)
                logging.info(
                    "Writing configuration for %s to: %s", interface.name, path
                )
                path.write_text(content)
                path.chmod(0o640)
        return 0


class WGQuickParser(BaseParser):
    output: Path = Argument(
        "--output", "-o", default=Path("/etc/wireguard"), help="Output directory"
    )

    def __call__(self, conn: sqlite3.Connection) -> int:
        output_path = self.output.resolve()
        logging.info("Generating wg-quick configuration to %s", output_path)

        for interface in Interface.list(conn):
            with StringIO() as f:
                f.write("[Interface]\n")
                f.write(f"ListenPort={interface.listen_port}\n")
                f.write(f"PrivateKey={interface.private_key}\n")
                f.write(f"MTU={interface.mtu}\n")
                f.write(
                    "Address={}\n".format(
                        ",".join(
                            map(str, filter(None, [interface.ipv4, interface.ipv6]))
                        ),
                    ),
                )
                f.write("\n")

                for client in interface.clients(conn):
                    f.write(f"# Client: {client.alias}\n")
                    f.write("[Peer]\n")
                    f.write(
                        "AllowedIPs={}\n".format(
                            ",".join(
                                map(str, filter(None, [client.ipv4, client.ipv6]))
                            ),
                        ),
                    )
                    f.write(f"PublicKey={client.public_key}\n")
                    f.write(f"PersistentKeepalive={interface.persistent_keepalive}\n")
                    if client.preshared_key:
                        f.write(f"PresharedKey={client.preshared_key}\n")

                    f.write("\n")

                config_content = f.getvalue()

            config_path = output_path / f"{interface.name}.conf"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            logging.info("Writing configuration to: %s", config_path)
            config_path.write_text(config_content)
            config_path.chmod(0o640)

        return 0


class RenderParser(BaseParser):
    systemd = SystemdNetworkdParser()
    wgquick = WGQuickParser()

    def __call__(self, conn: sqlite3.Connection) -> int:
        self.print_help()
        return errno.EINVAL

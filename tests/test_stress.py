import json

import pytest

NUM_INTERFACES = 128

pytestmark = pytest.mark.slow


@pytest.fixture
def populated_cli(cli):
    """Create many interfaces, each with one client."""
    for i in range(NUM_INTERFACES):
        a, b = divmod(i, 256)
        result = cli(
            "interface",
            "add",
            f"wg{i}",
            "--ipv4",
            f"10.{a}.{b}.1/24",
            "--ipv6",
            f"fd{a:02x}:{b:02x}::1/64",
            "--endpoint",
            f"vpn{i}.example.com:51820",
            "--listen-port",
            str(10000 + i),
        )
        assert result.code == 0, f"Failed to add interface wg{i}"

        result = cli("client", "add", f"wg{i}", f"peer{i}")
        assert result.code == 0, f"Failed to add client peer{i} to wg{i}"

    return cli


def test_stress_create_interfaces(populated_cli):
    result = populated_cli("-f", "json", "interface", "list")
    assert result.code == 0
    data = json.loads(result.stdout)
    assert len(data) == NUM_INTERFACES


def test_stress_list_clients(populated_cli):
    result = populated_cli("-f", "json", "client", "list")
    assert result.code == 0
    data = json.loads(result.stdout)
    assert len(data) == NUM_INTERFACES

    names = {d["client"] for d in data}
    assert len(names) == NUM_INTERFACES


def test_stress_render_wgquick(populated_cli, tmp_path):
    output_dir = tmp_path / "wgquick"
    output_dir.mkdir()
    result = populated_cli("render", "wgquick", "--output", str(output_dir))
    assert result.code == 0

    confs = list(output_dir.glob("*.conf"))
    assert len(confs) == NUM_INTERFACES

    # spot-check first, last, and middle
    for i in [0, NUM_INTERFACES // 2, NUM_INTERFACES - 1]:
        conf = (output_dir / f"wg{i}.conf").read_text()
        assert "[Interface]" in conf
        assert "[Peer]" in conf
        assert f"peer{i}" in conf


def test_stress_render_systemd(populated_cli, tmp_path):
    output_dir = tmp_path / "systemd"
    output_dir.mkdir()
    result = populated_cli("render", "systemd", "--output", str(output_dir))
    assert result.code == 0

    netdevs = list(output_dir.glob("*.netdev"))
    networks = list(output_dir.glob("*.network"))
    assert len(netdevs) == NUM_INTERFACES
    assert len(networks) == NUM_INTERFACES

    for i in [0, NUM_INTERFACES // 2, NUM_INTERFACES - 1]:
        netdev = (output_dir / f"wg{i}.netdev").read_text()
        network = (output_dir / f"wg{i}.network").read_text()
        assert "[WireGuardPeer]" in netdev
        assert f"peer{i}" in netdev
        assert "[Network]" in network

def test_render_help(cli):
    result = cli("render", "--help")
    assert result.code == 0


def test_render_no_args(cli):
    result = cli("render")
    assert result.code != 0


def test_render_wgquick(cli, add_interface, tmp_path):
    add_interface()
    cli("client", "add", "wg0", "alice")

    output_dir = tmp_path / "wgquick"
    output_dir.mkdir()
    result = cli("render", "wgquick", "--output", str(output_dir))
    assert result.code == 0

    conf = (output_dir / "wg0.conf").read_text()
    assert "[Interface]" in conf
    assert "[Peer]" in conf
    assert "alice" in conf


def test_render_systemd(cli, add_interface, tmp_path):
    add_interface()
    cli("client", "add", "wg0", "alice")

    output_dir = tmp_path / "systemd"
    output_dir.mkdir()
    result = cli("render", "systemd", "--output", str(output_dir))
    assert result.code == 0

    netdev = (output_dir / "wg0.netdev").read_text()
    network = (output_dir / "wg0.network").read_text()
    assert "[NetDev]" in netdev
    assert "[WireGuardPeer]" in netdev
    assert "alice" in netdev
    assert "[Network]" in network
    assert "10.0.0.1/24" in network


def test_render_wgquick_empty(cli, tmp_path):
    output_dir = tmp_path / "wgquick"
    output_dir.mkdir()
    result = cli("render", "wgquick", "--output", str(output_dir))
    assert result.code == 0


def test_render_systemd_empty(cli, tmp_path):
    output_dir = tmp_path / "systemd"
    output_dir.mkdir()
    result = cli("render", "systemd", "--output", str(output_dir))
    assert result.code == 0


def test_render_wgquick_multiple_clients(cli, add_interface, tmp_path):
    add_interface()
    cli("client", "add", "wg0", "alice")
    cli("client", "add", "wg0", "bob")

    output_dir = tmp_path / "wgquick"
    output_dir.mkdir()
    cli("render", "wgquick", "--output", str(output_dir))

    conf = (output_dir / "wg0.conf").read_text()
    assert conf.count("[Peer]") == 2
    assert "alice" in conf
    assert "bob" in conf


def test_render_systemd_multiple_clients(cli, add_interface, tmp_path):
    add_interface()
    cli("client", "add", "wg0", "alice")
    cli("client", "add", "wg0", "bob")

    output_dir = tmp_path / "systemd"
    output_dir.mkdir()
    cli("render", "systemd", "--output", str(output_dir))

    netdev = (output_dir / "wg0.netdev").read_text()
    assert netdev.count("[WireGuardPeer]") == 2
    assert "alice" in netdev
    assert "bob" in netdev


def test_render_wgquick_multiple_interfaces(cli, add_interface, tmp_path):
    add_interface(name="wg0", ipv4="10.0.0.1/24", ipv6="fd00::1/64")
    add_interface(name="wg1", ipv4="10.1.0.1/24", ipv6="fd01::1/64")

    output_dir = tmp_path / "wgquick"
    output_dir.mkdir()
    cli("render", "wgquick", "--output", str(output_dir))

    assert (output_dir / "wg0.conf").exists()
    assert (output_dir / "wg1.conf").exists()


def test_render_wgquick_content_details(cli, tmp_path):
    cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/24",
        "--ipv6",
        "fd00::1/64",
        "--endpoint",
        "vpn.example.com:51820",
        "--mtu",
        "1400",
        "--listen-port",
        "12345",
    )
    cli("client", "add", "wg0", "alice")

    output_dir = tmp_path / "wgquick"
    output_dir.mkdir()
    cli("render", "wgquick", "--output", str(output_dir))

    conf = (output_dir / "wg0.conf").read_text()
    assert "ListenPort=12345" in conf
    assert "MTU=1400" in conf
    assert "10.0.0.1/24" in conf
    assert "fd00::1/64" in conf


def test_render_systemd_file_permissions(cli, add_interface, tmp_path):
    add_interface()
    output_dir = tmp_path / "systemd"
    output_dir.mkdir()
    cli("render", "systemd", "--output", str(output_dir))

    netdev = output_dir / "wg0.netdev"
    network = output_dir / "wg0.network"
    assert netdev.stat().st_mode & 0o777 == 0o640
    assert network.stat().st_mode & 0o777 == 0o640


def test_render_wgquick_file_permissions(cli, add_interface, tmp_path):
    add_interface()
    output_dir = tmp_path / "wgquick"
    output_dir.mkdir()
    cli("render", "wgquick", "--output", str(output_dir))

    conf = output_dir / "wg0.conf"
    assert conf.stat().st_mode & 0o777 == 0o640


def test_render_wgquick_preshared_key(cli, add_interface, tmp_path):
    add_interface()
    cli("client", "add", "wg0", "alice", "--preshared-key")

    output_dir = tmp_path / "wgquick"
    output_dir.mkdir()
    cli("render", "wgquick", "--output", str(output_dir))

    conf = (output_dir / "wg0.conf").read_text()
    assert "PresharedKey=" in conf


def test_render_systemd_preshared_key(cli, add_interface, tmp_path):
    add_interface()
    cli("client", "add", "wg0", "alice", "--preshared-key")

    output_dir = tmp_path / "systemd"
    output_dir.mkdir()
    cli("render", "systemd", "--output", str(output_dir))

    netdev = (output_dir / "wg0.netdev").read_text()
    assert "PresharedKey=" in netdev

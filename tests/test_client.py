import json


def test_client_help(cli):
    result = cli("client", "--help")
    assert result.code == 0


def test_client_no_args(cli):
    result = cli("client")
    assert result.code != 0


def test_client_add(cli, add_interface):
    add_interface()
    result = cli("client", "add", "wg0", "alice")
    assert result.code == 0
    assert "[Interface]" in result.stdout
    assert "[Peer]" in result.stdout


def test_client_add_contains_keys(cli, add_interface):
    add_interface()
    result = cli("client", "add", "wg0", "alice")
    assert result.code == 0
    assert "PrivateKey" in result.stdout
    assert "PublicKey" in result.stdout
    assert "AllowedIPs" in result.stdout
    assert "Endpoint" in result.stdout
    assert "vpn.example.com:51820" in result.stdout


def test_client_add_nonexistent_interface(cli):
    result = cli("client", "add", "wg999", "alice")
    assert result.code == 1


def test_client_add_duplicate(cli, add_interface):
    add_interface()
    result = cli("client", "add", "wg0", "alice")
    assert result.code == 0
    result = cli("client", "add", "wg0", "alice")
    assert result.code == 1


def test_client_add_duplicate_force(cli, add_interface):
    add_interface()
    cli("client", "add", "wg0", "alice")
    result = cli("client", "add", "wg0", "alice", "--force")
    assert result.code == 0


def test_client_add_with_preshared_key(cli, add_interface):
    add_interface()
    result = cli("client", "add", "wg0", "alice", "--preshared-key")
    assert result.code == 0
    assert "PresharedKey" in result.stdout


def test_client_without_preshared_key_no_psk_in_config(cli, add_interface):
    add_interface()
    result = cli("client", "add", "wg0", "alice")
    assert result.code == 0
    assert "PresharedKey" not in result.stdout


def test_client_list_empty(cli):
    result = cli("client", "list")
    assert result.code == 0


def test_client_list(cli, add_interface):
    add_interface()
    cli("client", "add", "wg0", "alice")
    cli("client", "add", "wg0", "bob")

    result = cli("client", "list")
    assert result.code == 0
    assert "alice" in result.stdout
    assert "bob" in result.stdout


def test_client_list_json(cli, add_interface):
    add_interface()
    cli("client", "add", "wg0", "alice")
    cli("client", "add", "wg0", "bob")

    result = cli("-f", "json", "client", "list")
    assert result.code == 0
    data = json.loads(result.stdout)
    assert len(data) == 2
    aliases = {d["client"] for d in data}
    assert aliases == {"alice", "bob"}


def test_client_remove(cli, add_interface):
    add_interface()
    cli("client", "add", "wg0", "alice")

    result = cli("client", "remove", "wg0", "alice")
    assert result.code == 0

    result = cli("-f", "json", "client", "list")
    data = json.loads(result.stdout)
    assert len(data) == 0


def test_client_remove_multiple(cli, add_interface):
    add_interface()
    cli("client", "add", "wg0", "alice")
    cli("client", "add", "wg0", "bob")

    result = cli("client", "remove", "wg0", "alice", "bob")
    assert result.code == 0

    result = cli("-f", "json", "client", "list")
    data = json.loads(result.stdout)
    assert len(data) == 0


def test_client_remove_nonexistent(cli, add_interface):
    add_interface()
    result = cli("client", "remove", "wg0", "nobody")
    assert result.code == 0  # logs error but returns 0


def test_client_ip_increments(cli, add_interface):
    add_interface()
    cli("client", "add", "wg0", "alice")
    cli("client", "add", "wg0", "bob")

    result = cli("-f", "json", "client", "list")
    data = json.loads(result.stdout)
    ips = {d["client"]: d["ipv4"] for d in data}
    assert ips["alice"] == "10.0.0.2"
    assert ips["bob"] == "10.0.0.3"


def test_client_ipv6_increments(cli, add_interface):
    add_interface()
    cli("client", "add", "wg0", "alice")
    cli("client", "add", "wg0", "bob")

    result = cli("-f", "json", "client", "list")
    data = json.loads(result.stdout)
    ips = {d["client"]: d["ipv6"] for d in data}
    assert ips["alice"] == "fd00::2"
    assert ips["bob"] == "fd00::3"


def test_client_add_after_remove_ip_does_not_reuse(cli, add_interface):
    """address_shift keeps incrementing even after client removal"""
    add_interface()
    cli("client", "add", "wg0", "alice")  # 10.0.0.2
    cli("client", "remove", "wg0", "alice")
    cli("client", "add", "wg0", "bob")  # 10.0.0.3, not 10.0.0.2

    result = cli("-f", "json", "client", "list")
    data = json.loads(result.stdout)
    assert data[0]["ipv4"] == "10.0.0.3"


def test_same_alias_different_interfaces(cli, add_interface):
    add_interface(name="wg0", ipv4="10.0.0.1/24", ipv6="fd00::1/64")
    add_interface(name="wg1", ipv4="10.1.0.1/24", ipv6="fd01::1/64")

    r1 = cli("client", "add", "wg0", "alice")
    assert r1.code == 0
    r2 = cli("client", "add", "wg1", "alice")
    assert r2.code == 0

    result = cli("-f", "json", "client", "list")
    data = json.loads(result.stdout)
    assert len(data) == 2
    ifaces = {d["interface"] for d in data}
    assert ifaces == {"wg0", "wg1"}


def test_client_list_multiple_interfaces(cli, add_interface):
    add_interface(name="wg0", ipv4="10.0.0.1/24", ipv6="fd00::1/64")
    add_interface(name="wg1", ipv4="10.1.0.1/24", ipv6="fd01::1/64")

    cli("client", "add", "wg0", "alice")
    cli("client", "add", "wg1", "bob")

    result = cli("-f", "json", "client", "list")
    data = json.loads(result.stdout)
    assert len(data) == 2
    by_iface = {d["interface"]: d["client"] for d in data}
    assert by_iface == {"wg0": "alice", "wg1": "bob"}


def test_client_config_dns_and_mtu(cli):
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
        "1350",
        "--dns",
        "9.9.9.9",
    )
    result = cli("client", "add", "wg0", "alice")
    assert result.code == 0
    assert "MTU = 1350" in result.stdout
    assert "DNS = 9.9.9.9" in result.stdout


def test_client_config_addresses(cli, add_interface):
    add_interface()
    result = cli("client", "add", "wg0", "alice")
    assert result.code == 0
    assert "10.0.0.2" in result.stdout
    assert "fd00::2" in result.stdout


def test_client_qr_output(cli, add_interface):
    add_interface()
    result = cli("client", "add", "wg0", "alice", "--qr")
    assert result.code == 0
    assert "Client QR" in result.stdout


def test_client_add_ipv4_only_interface(cli, add_interface):
    add_interface(ipv4="10.0.0.1/24", ipv6=None)
    result = cli("client", "add", "wg0", "alice")
    assert result.code == 0
    assert "10.0.0.2" in result.stdout


def test_client_add_ipv6_only_interface(cli, add_interface):
    add_interface(ipv4=None, ipv6="fd00::1/64")
    result = cli("client", "add", "wg0", "alice")
    assert result.code == 0
    assert "fd00::2" in result.stdout


def test_client_add_no_ips_interface(cli, add_interface):
    add_interface(ipv4=None, ipv6=None)
    result = cli("client", "add", "wg0", "alice")
    assert result.code == 0


def test_client_ipv4_only_list(cli, add_interface):
    add_interface(ipv4="10.0.0.1/24", ipv6=None)
    cli("client", "add", "wg0", "alice")

    result = cli("-f", "json", "client", "list")
    data = json.loads(result.stdout)
    assert data[0]["ipv4"] == "10.0.0.2"
    assert data[0]["ipv6"] == ""


def test_client_ipv6_only_list(cli, add_interface):
    add_interface(ipv4=None, ipv6="fd00::1/64")
    cli("client", "add", "wg0", "alice")

    result = cli("-f", "json", "client", "list")
    data = json.loads(result.stdout)
    assert data[0]["ipv4"] == ""
    assert data[0]["ipv6"] == "fd00::2"


# --- Address pool exhaustion ---


def test_ipv4_pool_exhausted_slash30(cli):
    """A /30 has 4 addresses: .0 (network), .1 (server), .2, .3.
    With server at .1 and shift starting at 1, we get .2 and .3 as clients.
    Third client should fail."""
    cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/30",
        "--ipv6",
        "fd00::1/64",
        "--endpoint",
        "vpn.example.com:51820",
    )
    r1 = cli("client", "add", "wg0", "c1")
    assert r1.code == 0

    r2 = cli("client", "add", "wg0", "c2")
    assert r2.code == 0

    r3 = cli("client", "add", "wg0", "c3")
    assert r3.code == 1


def test_ipv4_pool_exhausted_slash30_correct_ips(cli):
    """Verify the two valid clients get .2 and .3"""
    cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/30",
        "--ipv6",
        "fd00::1/64",
        "--endpoint",
        "vpn.example.com:51820",
    )
    cli("client", "add", "wg0", "c1")
    cli("client", "add", "wg0", "c2")

    result = cli("-f", "json", "client", "list")
    data = json.loads(result.stdout)
    ips = {d["client"]: d["ipv4"] for d in data}
    assert ips["c1"] == "10.0.0.2"
    assert ips["c2"] == "10.0.0.3"


def test_ipv6_pool_exhausted_slash126(cli):
    """/126 gives 4 addresses, server at ::1, clients ::2 and ::3"""
    cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/24",
        "--ipv6",
        "fd00::1/126",
        "--endpoint",
        "vpn.example.com:51820",
    )
    r1 = cli("client", "add", "wg0", "c1")
    assert r1.code == 0

    r2 = cli("client", "add", "wg0", "c2")
    assert r2.code == 0

    r3 = cli("client", "add", "wg0", "c3")
    assert r3.code == 1


def test_ipv4_pool_exhausted_slash31(cli):
    """/31 point-to-point: only .0 and .1 — server is .1, no room for clients.
    Interface creation itself should be rejected."""
    r = cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/31",
        "--ipv6",
        "fd00::1/64",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert r.code == 1


def test_pool_exhausted_does_not_create_client(cli):
    """When pool is exhausted, no client should be saved to the database"""
    cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/30",
        "--ipv6",
        "fd00::1/64",
        "--endpoint",
        "vpn.example.com:51820",
    )
    cli("client", "add", "wg0", "c1")
    cli("client", "add", "wg0", "c2")
    cli("client", "add", "wg0", "c3")  # should fail

    result = cli("-f", "json", "client", "list")
    data = json.loads(result.stdout)
    assert len(data) == 2


def test_pool_exhausted_ipv4_only(cli):
    """/30 with no IPv6 — same exhaustion behavior"""
    cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/30",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert cli("client", "add", "wg0", "c1").code == 0
    assert cli("client", "add", "wg0", "c2").code == 0
    assert cli("client", "add", "wg0", "c3").code == 1


def test_pool_exhausted_ipv6_only(cli):
    """/126 with no IPv4"""
    cli(
        "interface",
        "add",
        "wg0",
        "--ipv6",
        "fd00::1/126",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert cli("client", "add", "wg0", "c1").code == 0
    assert cli("client", "add", "wg0", "c2").code == 0
    assert cli("client", "add", "wg0", "c3").code == 1


def test_pool_not_reclaimed_after_remove(cli):
    """Removing a client does NOT free its IP for reuse, so pool
    still exhausts at the same point."""
    cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/30",
        "--ipv6",
        "fd00::1/64",
        "--endpoint",
        "vpn.example.com:51820",
    )
    cli("client", "add", "wg0", "c1")
    cli("client", "add", "wg0", "c2")
    cli("client", "remove", "wg0", "c1")
    cli("client", "remove", "wg0", "c2")

    # shift is already at 3, next IP would be .4 — out of range
    r = cli("client", "add", "wg0", "c3")
    assert r.code == 1


def test_client_preshared_key_not_private_key(cli, add_interface):
    """PresharedKey value in config must differ from PrivateKey"""
    add_interface()
    result = cli("client", "add", "wg0", "alice", "--preshared-key")
    assert result.code == 0
    lines = result.stdout.splitlines()
    private_key = None
    preshared_key = None
    for line in lines:
        if line.strip().startswith("PrivateKey"):
            private_key = line.split("=", 1)[1].strip()
        if line.strip().startswith("PresharedKey"):
            preshared_key = line.split("=", 1)[1].strip()
    assert private_key is not None
    assert preshared_key is not None
    assert private_key != preshared_key


def test_client_preshared_key_in_peer_section(cli, add_interface):
    """PresharedKey must appear in [Peer] section, not [Interface]"""
    add_interface()
    result = cli("client", "add", "wg0", "alice", "--preshared-key")
    assert result.code == 0
    text = result.stdout
    peer_pos = text.index("[Peer]")
    psk_pos = text.index("PresharedKey")
    assert psk_pos > peer_pos


def test_client_list_csv_empty(cli):
    """CSV output with no clients should not crash"""
    result = cli("-f", "csv", "client", "list")
    assert result.code == 0


def test_client_list_tsv_empty(cli):
    """TSV output with no clients should not crash"""
    result = cli("-f", "tsv", "client", "list")
    assert result.code == 0


def test_client_force_readd_gets_new_ip(cli, add_interface):
    """--force re-add increments address_shift, giving a new IP"""
    add_interface()
    cli("client", "add", "wg0", "alice")

    result1 = cli("-f", "json", "client", "list")
    data1 = json.loads(result1.stdout)
    ip_before = data1[0]["ipv4"]

    cli("client", "add", "wg0", "alice", "--force")

    result2 = cli("-f", "json", "client", "list")
    data2 = json.loads(result2.stdout)
    ip_after = data2[0]["ipv4"]

    assert ip_before != ip_after


def test_client_config_no_ips_interface(cli, add_interface):
    """Config generated for interface with no IPv4/IPv6 should have empty Address"""
    add_interface(ipv4=None, ipv6=None)
    result = cli("client", "add", "wg0", "alice")
    assert result.code == 0
    assert "Address = " in result.stdout

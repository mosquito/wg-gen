import json


def test_interface_help(cli):
    result = cli("interface", "--help")
    assert result.code == 0


def test_interface_no_args(cli):
    result = cli("interface")
    assert result.code != 0


def test_interface_add(cli):
    result = cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/24",
        "--ipv6",
        "fd00::1/64",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert result.code == 0


def test_interface_add_missing_endpoint(cli):
    result = cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/24",
    )
    assert result.code != 0


def test_interface_list_empty(cli):
    result = cli("interface", "list")
    assert result.code == 0


def test_interface_add_and_list(cli, add_interface):
    add_interface()
    result = cli("-f", "json", "interface", "list")
    assert result.code == 0
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert data[0]["interface"] == "wg0"
    assert data[0]["endpoint"] == "vpn.example.com:51820"


def test_interface_add_and_list_json(cli, add_interface):
    add_interface()
    result = cli("-f", "json", "interface", "list")
    assert result.code == 0
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert data[0]["interface"] == "wg0"
    assert data[0]["endpoint"] == "vpn.example.com:51820"


def test_interface_add_and_list_csv(cli, add_interface):
    add_interface()
    result = cli("-f", "csv", "interface", "list")
    assert result.code == 0
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2  # header + 1 row
    assert "wg0" in lines[1]


def test_interface_add_and_list_tsv(cli, add_interface):
    add_interface()
    result = cli("-f", "tsv", "interface", "list")
    assert result.code == 0
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2
    assert "\t" in lines[0]


def test_interface_add_multiple(cli):
    for name, ipv4, ipv6 in [
        ("wg0", "10.0.0.1/24", "fd00::1/64"),
        ("wg1", "10.1.0.1/24", "fd01::1/64"),
    ]:
        result = cli(
            "interface",
            "add",
            name,
            "--ipv4",
            ipv4,
            "--ipv6",
            ipv6,
            "--endpoint",
            "vpn.example.com:51820",
        )
        assert result.code == 0

    result = cli("-f", "json", "interface", "list")
    data = json.loads(result.stdout)
    assert len(data) == 2
    names = {d["interface"] for d in data}
    assert names == {"wg0", "wg1"}


def test_interface_add_custom_options(cli):
    result = cli(
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
        "--persistent-keepalive",
        "25",
        "--dns",
        "9.9.9.9",
    )
    assert result.code == 0
    result = cli("-f", "json", "interface", "list")
    data = json.loads(result.stdout)
    assert data[0]["mtu"] == "1400"
    assert data[0]["listen_port"] == "12345"


def test_interface_remove(cli, add_interface):
    add_interface()
    result = cli("interface", "remove", "wg0")
    assert result.code == 0

    result = cli("-f", "json", "interface", "list")
    data = json.loads(result.stdout)
    assert len(data) == 0


def test_interface_remove_nonexistent(cli):
    result = cli("interface", "remove", "wg999")
    assert result.code == 1


def test_interface_remove_cascades_clients(cli, add_interface):
    add_interface()
    cli("client", "add", "wg0", "alice")
    cli("interface", "remove", "wg0")

    result = cli("-f", "json", "client", "list")
    data = json.loads(result.stdout)
    assert len(data) == 0


def test_interface_ipv4_only_list(cli, add_interface):
    add_interface(ipv4="10.0.0.1/24", ipv6=None)
    result = cli("-f", "json", "interface", "list")
    assert result.code == 0
    data = json.loads(result.stdout)
    assert data[0]["ipv4"] == "10.0.0.1/24"
    assert data[0]["ipv6"] == "None"


def test_interface_ipv6_only_list(cli, add_interface):
    add_interface(ipv4=None, ipv6="fd00::1/64")
    result = cli("-f", "json", "interface", "list")
    assert result.code == 0
    data = json.loads(result.stdout)
    assert data[0]["ipv6"] == "fd00::1/64"


def test_interface_add_no_ips(cli):
    result = cli(
        "interface",
        "add",
        "wg0",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert result.code == 0
    result = cli("-f", "json", "interface", "list")
    data = json.loads(result.stdout)
    assert len(data) == 1


def test_interface_upsert_same_name(cli, add_interface):
    add_interface()
    result = cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/24",
        "--ipv6",
        "fd00::1/64",
        "--endpoint",
        "new.endpoint.com:9999",
    )
    assert result.code == 0
    result = cli("-f", "json", "interface", "list")
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert data[0]["endpoint"] == "new.endpoint.com:9999"


def test_interface_duplicate_ips_different_name(cli, add_interface):
    """Adding wg1 with same IPs as wg0 should fail due to subnet overlap"""
    add_interface(name="wg0")
    result = cli(
        "interface",
        "add",
        "wg1",
        "--ipv4",
        "10.0.0.1/24",
        "--ipv6",
        "fd00::1/64",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert result.code == 1


def test_interface_overlapping_ipv4_subnet(cli, add_interface):
    """10.0.0.0/24 overlaps with 10.0.0.0/16"""
    add_interface(name="wg0", ipv4="10.0.0.1/24", ipv6="fd00::1/64")
    result = cli(
        "interface",
        "add",
        "wg1",
        "--ipv4",
        "10.0.0.1/16",
        "--ipv6",
        "fd01::1/64",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert result.code == 1


def test_interface_overlapping_ipv6_subnet(cli, add_interface):
    """fd00::/64 overlaps with fd00::/48"""
    add_interface(name="wg0", ipv4="10.0.0.1/24", ipv6="fd00::1/64")
    result = cli(
        "interface",
        "add",
        "wg1",
        "--ipv4",
        "10.1.0.1/24",
        "--ipv6",
        "fd00::1/48",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert result.code == 1


def test_interface_non_overlapping_subnets(cli, add_interface):
    """Different subnets should be fine"""
    add_interface(name="wg0", ipv4="10.0.0.1/24", ipv6="fd00::1/64")
    result = cli(
        "interface",
        "add",
        "wg1",
        "--ipv4",
        "10.1.0.1/24",
        "--ipv6",
        "fd01::1/64",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert result.code == 0


def test_interface_one_has_ipv4_other_has_ipv6_only(cli, add_interface):
    """No overlap possible when IP families don't intersect"""
    add_interface(name="wg0", ipv4="10.0.0.1/24", ipv6=None)
    result = cli(
        "interface",
        "add",
        "wg1",
        "--ipv6",
        "fd00::1/64",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert result.code == 0


def test_interface_re_add_after_remove(cli, add_interface):
    add_interface()
    cli("interface", "remove", "wg0")
    add_interface()

    result = cli("-f", "json", "interface", "list")
    data = json.loads(result.stdout)
    assert len(data) == 1


def test_multiple_dns_servers(cli):
    result = cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/24",
        "--ipv6",
        "fd00::1/64",
        "--endpoint",
        "vpn.example.com:51820",
        "--dns",
        "1.1.1.1",
        "8.8.8.8",
        "9.9.9.9",
    )
    assert result.code == 0
    result = cli("-f", "json", "interface", "list")
    data = json.loads(result.stdout)
    dns = data[0]["dns"]
    assert isinstance(dns, list)
    assert "1.1.1.1" in dns
    assert "8.8.8.8" in dns
    assert "9.9.9.9" in dns


def test_allowed_ips_non_local(cli):
    result = cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/24",
        "--ipv6",
        "fd00::1/64",
        "--endpoint",
        "vpn.example.com:51820",
        "--allowed-ips",
        "non-local",
    )
    assert result.code == 0
    result = cli("-f", "json", "interface", "list")
    data = json.loads(result.stdout)
    allowed = data[0]["allowed_ips"]
    assert isinstance(allowed, list)
    assert len(allowed) > 2


def test_allowed_ips_custom(cli):
    result = cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/24",
        "--ipv6",
        "fd00::1/64",
        "--endpoint",
        "vpn.example.com:51820",
        "--allowed-ips",
        "192.168.0.0/16",
        "10.0.0.0/8",
    )
    assert result.code == 0
    result = cli("-f", "json", "interface", "list")
    data = json.loads(result.stdout)
    allowed = data[0]["allowed_ips"]
    assert isinstance(allowed, list)
    assert "192.168.0.0/16" in allowed
    assert "10.0.0.0/8" in allowed


# --- Address space validation at interface creation ---


def test_interface_reject_ipv4_slash32(cli):
    """/32 is a single host — no room for any client"""
    result = cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/32",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert result.code == 1


def test_interface_reject_ipv4_slash31(cli):
    """/31 has only 2 addresses (.0 and .1), server at .1 — no room for clients"""
    result = cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/31",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert result.code == 1


def test_interface_reject_ipv6_slash128(cli):
    """/128 is a single host"""
    result = cli(
        "interface",
        "add",
        "wg0",
        "--ipv6",
        "fd00::1/128",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert result.code == 1


def test_interface_reject_ipv6_slash127(cli):
    """/127 has only 2 addresses, server at ::1 — no room"""
    result = cli(
        "interface",
        "add",
        "wg0",
        "--ipv6",
        "fd00::1/127",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert result.code == 1


def test_interface_accept_ipv4_slash30(cli):
    """/30 has 4 addresses — server at .1, room for .2 and .3"""
    result = cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/30",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert result.code == 0


def test_interface_accept_ipv6_slash126(cli):
    """/126 has 4 addresses — room for clients"""
    result = cli(
        "interface",
        "add",
        "wg0",
        "--ipv6",
        "fd00::1/126",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert result.code == 0


def test_interface_reject_ipv4_at_end_of_subnet(cli):
    """Server at .3 in a /30 (last addr) — .4 is out of range"""
    result = cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.3/30",
        "--endpoint",
        "vpn.example.com:51820",
    )
    assert result.code == 1


def test_interface_reject_not_saved_on_bad_network(cli):
    """Rejected interface should not be in the database"""
    cli(
        "interface",
        "add",
        "wg0",
        "--ipv4",
        "10.0.0.1/32",
        "--endpoint",
        "vpn.example.com:51820",
    )
    result = cli("-f", "json", "interface", "list")
    data = json.loads(result.stdout)
    assert len(data) == 0


def test_interface_list_csv_empty(cli):
    """CSV output with no interfaces should not crash"""
    result = cli("-f", "csv", "interface", "list")
    assert result.code == 0


def test_interface_list_tsv_empty(cli):
    """TSV output with no interfaces should not crash"""
    result = cli("-f", "tsv", "interface", "list")
    assert result.code == 0

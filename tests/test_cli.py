def test_cli_help(cli):
    result = cli("--help")
    assert result.code == 0


def test_cli_no_args(cli):
    result = cli()
    assert result.code != 0

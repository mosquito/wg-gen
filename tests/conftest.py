from dataclasses import dataclass
from typing import Callable

import pytest

from wg_gen.__main__ import main


@dataclass(frozen=True, slots=True)
class CallResult:
    code: int
    stdout: str
    stderr: str


@pytest.fixture
def cli(tmp_path, capsys) -> Callable[[*[str, ...]], CallResult]:
    db_path = tmp_path / "db.sqlite"

    def run(*args):
        try:
            main("--db-path", str(db_path), *args)
            exit_code = 0
        except SystemExit as e:
            exit_code = e.code

        captured = capsys.readouterr()
        return CallResult(code=exit_code, stdout=captured.out, stderr=captured.err)

    return run


@pytest.fixture
def add_interface(cli):
    def _add(name="wg0", ipv4="10.0.0.1/24", ipv6="fd00::1/64"):
        args = ["interface", "add", name, "--endpoint", "vpn.example.com:51820"]
        if ipv4:
            args += ["--ipv4", ipv4]
        if ipv6:
            args += ["--ipv6", ipv6]
        result = cli(*args)
        assert result.code == 0

    return _add

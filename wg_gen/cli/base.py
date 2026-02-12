import errno
import sqlite3

import argclass


class BaseParser(argclass.Parser):
    def __call__(self, conn: sqlite3.Connection) -> int:  # type: ignore[override]
        if self.current_subparser is not None:
            return self.current_subparser(conn)  # type: ignore[call-arg]
        self.print_help()
        exit(errno.EINVAL)

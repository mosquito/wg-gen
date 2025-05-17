import errno
import sqlite3

import argclass


class BaseParser(argclass.Parser):
    # noinspection PyMethodOverriding
    def __call__(self, conn: sqlite3.Connection) -> int:
        if self.current_subparser is not None:
            return self.current_subparser(conn)
        self.print_help()
        exit(errno.EINVAL)

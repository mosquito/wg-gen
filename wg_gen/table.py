import csv
import json
import sys

import rich
from rich.table import Table


COLORS = [
    "cyan",
    "magenta",
    "yellow",
    "bright_blue",
    "red",
    "green",
    "bright_magenta",
    "dodger_blue2",
    "bright_red",
]


class SimpleTable(Table):
    def __init__(self, *headers, title: str, **kwargs):
        super().__init__(title=title, box=None, **kwargs)

        for idx, header in enumerate(headers):
            self.add_column(header, style=COLORS[idx % len(COLORS)])

    def print_table(self):
        rich.print(self)

    def get_rows(self) -> list[dict[str, str | list[str]]]:
        data: dict[str, list[str | list[str]]] = {}
        cells_len = 0
        for col in self.columns:
            hdr = str(col.header).lower().replace(" ", "_")
            data[hdr] = [
                str(c) if "\n" not in str(c) else str(c).splitlines() for c in col.cells
            ]
            cells_len = len(data[hdr])
        result: list[dict[str, str | list[str]]] = []
        for i in range(cells_len):
            entry: dict[str, str | list[str]] = {}
            for hdr in data:
                entry[hdr] = data[hdr][i]
            result.append(entry)
        return result

    def print_json(self):
        print(json.dumps(self.get_rows(), indent=1))

    def print_csv(self, delimiter: str = ","):
        writer = csv.writer(
            sys.stdout, delimiter=delimiter, quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
        data = self.get_rows()
        if not data:
            return

        writer.writerow(data[0].keys())
        for row in data:
            writer.writerow(
                v if not isinstance(v, list) else ",".join(v) for v in row.values()
            )

    def print(self, format: str = "table"):
        if format == "json":
            self.print_json()
        elif format == "csv":
            self.print_csv()
        elif format == "tsv":
            self.print_csv(delimiter="\t")
        else:
            self.print_table()

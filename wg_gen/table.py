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

def table_maker(title: str, *headers: str) -> Table:
    table = Table(title=title, box=None)

    for idx, header in enumerate(headers):
        table.add_column(header, style=COLORS[idx % len(COLORS)])

    return table


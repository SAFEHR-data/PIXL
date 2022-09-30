import argparse

from pathlib import Path
from datetime import datetime
from typing import Optional, Sequence
from core import QueryableDatabase, SQLQuery


class ArgumentParser(argparse.ArgumentParser):

    def __init__(self):
        super().__init__()
        self.add_argument(
            "template_filepath",    # Required positional argument
            type=str,
            help="Name of the .sql template file to use"
        )

    def parse_args(self,
                   args: Optional[Sequence[str]] = None
                   ) -> argparse.Namespace:
        """
        Parse a set of arguments in the format::

            --known_arg a_value --first_key first_value

        where the first_key argument is unknown to the parser. These latter
        unknown arguments are added to the namespace.
        """

        args, other = self.parse_known_args(args)
        for i, key in enumerate(other[::2]):

            if i + 1 == len(other):
                raise RuntimeError("Found trailing key. Please provide a value")

            value = other[2 * i + 1]

            if key.startswith("window_"):  # we have a timestamp
                value = datetime.fromisoformat(value)

            setattr(args, key.lstrip("--"), value)  # --a b -> args.a = b

        return args


if __name__ == '__main__':

    args = ArgumentParser().parse_args()
    query = SQLQuery(filepath=Path(args.template_filepath),
                     context=vars(args))

    db = QueryableDatabase()
    result = db.execute(query)

    if result is None:
        exit("No data to be found!")

    print(','.join([str(item) for item in result]))

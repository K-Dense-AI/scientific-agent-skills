"""Check table headers before pandas can silently rename duplicate columns."""

import csv
from itertools import chain


def validate_header(path, delimiter=",", comment=None):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        first = next((line for line in handle if line.strip()
                      and not (comment and line.startswith(comment))), "")
        if not first:
            return  # The main reader reports an empty file.
        try:
            if delimiter is None:
                delimiter = csv.Sniffer().sniff(first, delimiters=",\t").delimiter
            header = next(csv.reader(chain([first], handle), delimiter=delimiter))
        except csv.Error as exc:
            raise ValueError(f"Invalid table header: {exc}") from exc
    normalized = [label.strip() for label in header]
    if len(normalized) != len(set(normalized)):
        raise ValueError("Duplicate column labels in input header; refusing automatic renaming")

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


def read_table(path, **kwargs):
    """Keep pandas' CSV semantics without implicit indices or lost data."""
    import warnings

    import pandas as pd

    # index_col=False prevents automatic index inference. Pandas warns when
    # that would discard data, so never return the resulting truncated table.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", pd.errors.ParserWarning)
            return pd.read_csv(path, index_col=False, **kwargs)
    except pd.errors.ParserWarning as exc:
        raise ValueError(f"Table fields do not match the header: {exc}") from exc

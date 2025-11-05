import itertools
import copy

from typing import List, Mapping


def print_grid(servers: list[str], results: Mapping[str, bool], verbose=False) -> str:
    """
    Input:
        servers: List of server names
        results: Mapping of the pairwise server name and result compare
    Output:
        -
    """
    labels = copy.deepcopy(servers)
    first_column_width: int = max(map(len, labels))
    labels = [label.ljust(first_column_width) for label in labels]

    printed = set()
    # Vertical labels
    result: str = (
        "".join(
            f'{"".ljust(first_column_width - 1)}{" ".join(row)}\n'
            for row in itertools.zip_longest(
                *(s.strip().rjust(len(s)) for s in [" " * len(labels[0]), *labels]),
            )
        )
        + f"{''.ljust(first_column_width)}+{'-' * (len(labels) * 2 - 1)}\n"
    )
    
    #for label, row in zip(labels, grid):
    for label in labels:
        result += label.ljust(first_column_width) + "|"
        for rlabel in labels:
            symbol: str
            if label == rlabel:
                symbol = "\x1b[0;32m-\x1b[0m"
            else:
                pair = str(sorted([label.strip(), rlabel.strip()]))
                if pair in printed:
                    symbol = ' '
                else:
                    if results[pair]:
                        symbol = "\x1b[0;32m✓\x1b[0m"
                    elif results[pair] is None:
                        symbol = "\x1b[0;33m∅\x1b[0m"
                    else:
                        symbol = "\x1b[0;31m✖\x1b[0m"
                    printed.add(pair)
            result += symbol + " "
        
        result += "\n"

    if verbose:
        print(result)
    return result

from pathlib import Path
from collections.abc import Iterator
from itertools import islice

import ijson


def read_json_in_batches(
    file_path: str | Path,
    batch_size: int = 1000
) -> Iterator[list[dict]]:

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"JSON file not found: {file_path}"
        )

    if batch_size <= 0:
        raise ValueError("Batch size must be greater than zero.")

    try:
        with open(file_path, "rb") as file:

            records = ijson.items(file, "item")

            while True:
                batch = list(islice(records, batch_size))

                if not batch:
                    break

                yield batch

    except ijson.JSONError as exc:
        raise ValueError(
            f"Invalid JSON file: {exc}"
        ) from exc
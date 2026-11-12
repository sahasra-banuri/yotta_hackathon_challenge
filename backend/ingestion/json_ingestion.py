from pathlib import Path
from collections.abc import Iterator
from itertools import islice

import ijson


def read_json_in_batches(
    file_path: str | Path,
    batch_size: int = 1000
) -> Iterator[list[dict]]:

    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(
            f"JSON file not found: {file_path}"
        )

    if file_path.stat().st_size == 0:
        raise ValueError("Orders JSON file is physically empty.")

    if batch_size <= 0:
        raise ValueError("Batch size must be greater than zero.")

    try:
        with open(file_path, "rb") as file:

            parser = ijson.parse(file)

            try:
                _, event, _ = next(parser)
            except StopIteration:
                raise ValueError("JSON file contains no data.")

            if event != "start_array":
                raise ValueError(
                    "Orders JSON must contain a top-level array."
                )

            file.seek(0)
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
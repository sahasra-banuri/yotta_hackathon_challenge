import csv

from pathlib import Path
from collections.abc import Iterator
from itertools import islice


def read_csv_in_chunks(
    file_path: str | Path,
    chunk_size: int = 50000
) -> Iterator[list[dict]]:

    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(
            f"CSV file not found: {file_path}"
        )

    if chunk_size <= 0:
        raise ValueError(
            "Chunk size must be greater than zero."
        )

    if file_path.stat().st_size == 0:
        raise ValueError(
            "CSV file has no header."
        )

    try:
        with open(
            file_path,
            "r",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            reader = csv.DictReader(file, strict=True)

            if not reader.fieldnames:
                raise ValueError(
                    "CSV file has no header."
                )

            required_columns = {
                "product_id",
                "product_name",
                "category",
                "price",
                "stock_quantity",
                "status"
            }

            missing_columns = (
                required_columns - set(reader.fieldnames)
            )

            if missing_columns:
                raise ValueError(
                    f"Missing CSV columns: {missing_columns}"
                )

            records_found = False

            while True:
                batch = list(islice(reader, chunk_size))

                if not batch:
                    break

                records_found = True

                yield batch

            if not records_found:
                raise ValueError(
                    "Products CSV contains a header but no data records."
                )

    except csv.Error as exc:
        raise ValueError(
            f"Unable to parse CSV: {exc}"
        ) from exc
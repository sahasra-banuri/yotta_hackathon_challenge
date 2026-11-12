from pathlib import Path

from backend.ingestion.csv_ingestion import read_csv_in_chunks
from backend.ingestion.json_ingestion import read_json_in_batches

from backend.config import SAMPLE_DATA_DIR


def test_csv_ingestion():

    file_path = SAMPLE_DATA_DIR / "products.csv"

    total_records = 0
    total_batches = 0

    for batch in read_csv_in_chunks(file_path, chunk_size=200):

        total_records += len(batch)
        total_batches += 1

    print("\nCSV INGESTION")
    print("Total records:", total_records)
    print("Total batches:", total_batches)


def test_json_ingestion():

    file_path = SAMPLE_DATA_DIR / "orders.json"

    total_records = 0
    total_batches = 0

    for batch in read_json_in_batches(file_path, batch_size=200):

        total_records += len(batch)
        total_batches += 1

    print("\nJSON INGESTION")
    print("Total records:", total_records)
    print("Total batches:", total_batches)


if __name__ == "__main__":
    test_csv_ingestion()
    test_json_ingestion()
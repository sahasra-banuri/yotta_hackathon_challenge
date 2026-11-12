import json
import pytest

from backend.ingestion.json_ingestion import read_json_in_batches


def create_json(tmp_path, records, filename="orders.json"):
    file_path = tmp_path / filename

    file_path.write_text(
        json.dumps(records),
        encoding="utf-8"
    )

    return file_path


def create_order(order_id):
    return {
        "order_id": order_id,
        "order_date": "2026-11-12",
        "order_status": "PENDING",
        "items": [
            {
                "product_id": "P001",
                "quantity": 2,
                "unit_price": 100
            }
        ]
    }


def test_read_valid_json(tmp_path):
    records = [
        create_order("ORD001"),
        create_order("ORD002")
    ]

    file_path = create_json(tmp_path, records)

    batches = list(read_json_in_batches(file_path))

    assert len(batches) == 1
    assert len(batches[0]) == 2
    assert batches[0][0]["order_id"] == "ORD001"
    assert batches[0][1]["order_id"] == "ORD002"


def test_json_batching(tmp_path):
    records = [
        create_order(f"ORD{i:03d}")
        for i in range(1, 6)
    ]

    file_path = create_json(tmp_path, records)

    batches = list(
        read_json_in_batches(file_path, batch_size=2)
    )

    assert len(batches) == 3
    assert [len(batch) for batch in batches] == [2, 2, 1]


def test_empty_json_array(tmp_path):
    file_path = create_json(tmp_path, [])

    batches = list(read_json_in_batches(file_path))

    assert batches == []


def test_json_file_not_found(tmp_path):
    file_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError, match="JSON file not found"):
        list(read_json_in_batches(file_path))


@pytest.mark.parametrize("batch_size", [0, -1, -100])
def test_invalid_batch_size(tmp_path, batch_size):
    file_path = create_json(tmp_path, [])

    with pytest.raises(
        ValueError,
        match="Batch size must be greater than zero"
    ):
        list(read_json_in_batches(file_path, batch_size))


def test_malformed_json(tmp_path):
    file_path = tmp_path / "malformed.json"

    file_path.write_text(
        '[{"order_id": "ORD001"},',
        encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Invalid JSON file"):
        list(read_json_in_batches(file_path))


def test_json_records_are_dictionaries(tmp_path):
    records = [create_order("ORD001")]
    file_path = create_json(tmp_path, records)

    batches = list(read_json_in_batches(file_path))

    assert isinstance(batches[0][0], dict)
    assert batches[0][0]["order_id"] == "ORD001"


def test_json_exact_batch_boundary(tmp_path):
    records = [
        create_order(f"ORD{i:03d}")
        for i in range(1, 5)
    ]

    file_path = create_json(tmp_path, records)

    batches = list(
        read_json_in_batches(file_path, batch_size=2)
    )

    assert len(batches) == 2
    assert [len(batch) for batch in batches] == [2, 2]
import pytest

from backend.ingestion.csv_ingestion import read_csv_in_chunks


CSV_HEADER = (
    "product_id,product_name,category,price,stock_quantity,status\n"
)


def create_csv(tmp_path, content, filename="products.csv"):
    file_path = tmp_path / filename
    file_path.write_text(content, encoding="utf-8")
    return file_path


def create_product(product_id):
    return (
        f"{product_id},Product {product_id},Electronics,"
        f"100,10,ACTIVE\n"
    )


def test_read_valid_csv(tmp_path):
    content = (
        CSV_HEADER
        + create_product("P001")
        + create_product("P002")
    )

    file_path = create_csv(tmp_path, content)

    batches = list(
        read_csv_in_chunks(file_path, chunk_size=10)
    )

    assert len(batches) == 1
    assert len(batches[0]) == 2
    assert batches[0][0]["product_id"] == "P001"
    assert batches[0][1]["product_id"] == "P002"


def test_csv_chunking(tmp_path):
    content = CSV_HEADER

    for i in range(1, 6):
        content += create_product(f"P{i:03d}")

    file_path = create_csv(tmp_path, content)

    batches = list(
        read_csv_in_chunks(file_path, chunk_size=2)
    )

    assert len(batches) == 3
    assert [len(batch) for batch in batches] == [2, 2, 1]


def test_empty_csv_with_header(tmp_path):
    file_path = create_csv(tmp_path, CSV_HEADER)

    with pytest.raises(
        ValueError,
        match="header but no data records"
    ):
        list(read_csv_in_chunks(file_path))


def test_csv_without_header(tmp_path):
    file_path = create_csv(tmp_path, "")

    with pytest.raises(
        ValueError,
        match="CSV file has no header"
    ):
        list(read_csv_in_chunks(file_path))


def test_csv_missing_required_columns(tmp_path):
    content = (
        "product_id,product_name,price\n"
        "P001,Laptop,100\n"
    )

    file_path = create_csv(tmp_path, content)

    with pytest.raises(
        ValueError,
        match="Missing CSV columns"
    ):
        list(read_csv_in_chunks(file_path))


def test_csv_file_not_found(tmp_path):
    file_path = tmp_path / "missing.csv"

    with pytest.raises(
        FileNotFoundError,
        match="CSV file not found"
    ):
        list(read_csv_in_chunks(file_path))


@pytest.mark.parametrize("chunk_size", [0, -1, -100])
def test_invalid_chunk_size(tmp_path, chunk_size):
    file_path = create_csv(tmp_path, CSV_HEADER)

    with pytest.raises(
        ValueError,
        match="Chunk size must be greater than zero"
    ):
        list(read_csv_in_chunks(file_path, chunk_size))


def test_csv_malformed_quoting(tmp_path):
    content = (
        CSV_HEADER
        + '"P001,"Laptop,Electronics,100,10,ACTIVE\n'
    )

    file_path = create_csv(tmp_path, content)

    with pytest.raises(
        ValueError,
        match="Unable to parse CSV"
    ):
        list(read_csv_in_chunks(file_path))


def test_csv_records_are_dictionaries(tmp_path):
    content = CSV_HEADER + create_product("P001")

    file_path = create_csv(tmp_path, content)

    batches = list(read_csv_in_chunks(file_path))

    assert isinstance(batches[0][0], dict)

    assert set(batches[0][0].keys()) == {
        "product_id",
        "product_name",
        "category",
        "price",
        "stock_quantity",
        "status"
    }


def test_csv_exact_chunk_boundary(tmp_path):
    content = CSV_HEADER

    for i in range(1, 5):
        content += create_product(f"P{i:03d}")

    file_path = create_csv(tmp_path, content)

    batches = list(
        read_csv_in_chunks(file_path, chunk_size=2)
    )

    assert len(batches) == 2
    assert [len(batch) for batch in batches] == [2, 2]
import pytest
from decimal import Decimal

from backend.processing.product_validator import validate_product


@pytest.fixture
def valid_product():
    return {
        "product_id": "P001",
        "product_name": "Laptop",
        "category": "Electronics",
        "price": "75000.50",
        "stock_quantity": "10",
        "status": "ACTIVE"
    }


def test_valid_product(valid_product):
    seen_ids = set()

    result, errors = validate_product(valid_product, seen_ids)

    assert errors == []
    assert result is not None

    assert result["product_id"] == "P001"
    assert result["product_name"] == "Laptop"
    assert result["category"] == "Electronics"
    assert result["price"] == Decimal("75000.50")
    assert result["stock_quantity"] == 10
    assert result["status"] == "ACTIVE"

    assert "P001" in seen_ids


def test_product_fields_are_trimmed_and_normalized(valid_product):
    valid_product.update({
        "product_name": " Laptop ",
        "category": " Electronics ",
        "status": " active "
    })

    result, errors = validate_product(valid_product, set())

    assert errors == []
    assert result["product_name"] == "Laptop"
    assert result["category"] == "Electronics"
    assert result["status"] == "ACTIVE"


@pytest.mark.parametrize(
    "field,value,expected_error",
    [
        ("product_id", "", "Product ID is missing."),
        ("product_name", "", "Product name is missing."),
        ("category", "", "Product category is missing."),
        ("price", "invalid", "Price must be a valid number."),
        ("price", "-100", "Price must be greater than zero."),
        ("price", "0", "Price must be greater than zero."),
        ("price", "NaN", "Price must be a finite number."),
        ("price", "Infinity", "Price must be a finite number."),
        ("stock_quantity", "-5", "Stock quantity cannot be negative."),
        ("stock_quantity", "2.5", "Stock quantity must be an integer."),
    ]
)
def test_invalid_product_fields(
    valid_product,
    field,
    value,
    expected_error
):
    valid_product[field] = value

    result, errors = validate_product(valid_product, set())

    assert result is None
    assert expected_error in errors


def test_invalid_product_status(valid_product):
    valid_product["status"] = "UNKNOWN"

    result, errors = validate_product(valid_product, set())

    assert result is None
    assert any(
        "Invalid product status" in error
        for error in errors
    )


def test_duplicate_product_id(valid_product):
    seen_ids = {"P001"}

    result, errors = validate_product(valid_product, seen_ids)

    assert result is None
    assert "Duplicate product ID: P001" in errors


def test_multiple_validation_errors(valid_product):
    valid_product.update({
        "product_name": "",
        "category": "",
        "price": "-100",
        "stock_quantity": "-5"
    })

    result, errors = validate_product(valid_product, set())

    assert result is None
    assert len(errors) >= 4


def test_invalid_record_does_not_reserve_product_id(valid_product):
    seen_ids = set()

    invalid_product = valid_product.copy()
    invalid_product["price"] = "-100"

    result, errors = validate_product(invalid_product, seen_ids)

    assert result is None
    assert "P001" not in seen_ids

    # The same ID should be accepted when a valid record arrives.
    result, errors = validate_product(valid_product, seen_ids)

    assert errors == []
    assert result is not None
    assert result["product_id"] == "P001"
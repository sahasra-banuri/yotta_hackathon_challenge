from pathlib import Path

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = BASE_DIR / "data"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
GENERATED_DATA_DIR = DATA_DIR / "generated"

# Database configuration
DATABASE_PATH = DATA_DIR / "ecommerce.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Processing configuration
DEFAULT_CHUNK_SIZE = 50000
DEFAULT_JSON_BATCH_SIZE = 1000

# Allowed values
VALID_PRODUCT_STATUSES = {"ACTIVE", "INACTIVE"}

VALID_ORDER_STATUSES = {
    "PENDING",
    "CONFIRMED",
    "SHIPPED",
    "COMPLETED",
    "CANCELLED"
}

# Monitoring configuration
MEMORY_LIMIT_MB = 512
STALE_RUN_TIMEOUT_MINUTES = 60
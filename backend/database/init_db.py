from backend.database.connection import Base, engine

# Import models so SQLAlchemy registers all tables
from backend.database.models import (
    Product,
    Order,
    OrderItem,
    RejectedRecord,
    PipelineRun
)


def initialize_database():

    Base.metadata.create_all(bind=engine)

    print("Database initialized successfully.")

    print("Created tables:")

    for table_name in Base.metadata.tables:
        print(f"- {table_name}")


if __name__ == "__main__":
    initialize_database()
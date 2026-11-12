from sqlalchemy import inspect

from backend.database.connection import engine


def verify_database():

    inspector = inspect(engine)

    tables = inspector.get_table_names()

    print("\nDATABASE VERIFICATION")
    print("=====================")

    for table in tables:

        print(f"\nTable: {table}")

        columns = inspector.get_columns(table)

        for column in columns:

            print(
                f"  {column['name']} "
                f"| {column['type']} "
                f"| Nullable: {column['nullable']}"
            )
import sqlite3

from backend.config import DATABASE_PATH

connection = sqlite3.connect(DATABASE_PATH)
cursor = connection.cursor()

tables = [
    "products",
    "orders",
    "order_items",
    "rejected_records",
    "pipeline_runs"
]

print("\nDATABASE RECORD COUNTS")
print("======================")

for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"{table}: {count:,} records")



print("\nPIPELINE EXECUTION HISTORY")
print("==========================")

cursor.execute("""
    SELECT
        run_id,
        status,
        total_records,
        valid_records,
        rejected_records,
        processing_time,
        peak_memory_mb,
        started_at
    FROM pipeline_runs
    ORDER BY started_at DESC
""")

for row in cursor.fetchall():
    print("\nRun ID:", row[0])
    print("Status:", row[1])
    print("Total records:", row[2])
    print("Valid records:", row[3])
    print("Rejected records:", row[4])
    print("Processing time:", row[5])
    print("Peak memory (MB):", row[6])
    print("Started at:", row[7])

print("\nNEGATIVE TEST RUN VERIFICATION")
print("==============================")

test_run_id = "051b107c-47ea-4921-b8c3-425bcdb54e00"

cursor.execute("""
    SELECT source_file, record_id, rejection_reason
    FROM rejected_records
    WHERE run_id = ?
""", (test_run_id,))

rejections = cursor.fetchall()

print(f"\nRejected records: {len(rejections)}")

for source_file, record_id, reason in rejections:
    print(f"\nFile: {source_file}")
    print(f"Record ID: {record_id}")
    print(f"Reason: {reason}")


print("\nPUBLISHED TEST PRODUCTS")
print("=======================")

cursor.execute("""
    SELECT product_id, product_name, price
    FROM products
    WHERE product_id LIKE 'TP%'
""")

for row in cursor.fetchall():
    print(row)


print("\nPUBLISHED TEST ORDERS")
print("=====================")

cursor.execute("""
    SELECT order_id, total_amount
    FROM orders
    WHERE order_id LIKE 'ORDTEST%'
""")

for row in cursor.fetchall():
    print(row)
    
connection.close()

if __name__ == "__main__":
    verify_database()
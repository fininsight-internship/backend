import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Connecting to: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

print("\n--- Tables in public schema ---")
tables = inspector.get_table_names(schema="public")
for t in tables:
    print(f"- {t}")

import os
from urllib.parse import urlparse

import pandas as pd
from sqlalchemy import create_engine, text


def get_database_url():
    # Prefer env var, fallback to local docker-compose mapping
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:change_me@localhost:5432/ticketing_db",
    )


def list_user_tables(engine):
    sql = text(
        """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_type='BASE TABLE'
          AND table_schema NOT IN ('pg_catalog','information_schema')
        ORDER BY table_schema, table_name
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).fetchall()
    return [f"{r[0]}.{r[1]}" for r in rows]


def export_to_xlsx(engine, tables, out_path):
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        for full_name in tables:
            schema, table = full_name.split(".")
            query = f'SELECT * FROM "{schema}"."{table}"'
            try:
                df = pd.read_sql_query(query, engine)
            except Exception as e:
                print(f"Skipping {full_name}: read error: {e}")
                continue
            sheet_name = table[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=False)


def main():
    db_url = get_database_url()
    print("Using DATABASE_URL:", db_url)
    engine = create_engine(db_url)
    tables = list_user_tables(engine)
    if not tables:
        print("No user tables found.")
        return
    out_path = os.path.abspath(os.path.join(os.getcwd(), "tables_export.xlsx"))
    print(f"Exporting {len(tables)} tables to {out_path}")
    export_to_xlsx(engine, tables, out_path)
    print("Export complete.")


if __name__ == "__main__":
    main()
